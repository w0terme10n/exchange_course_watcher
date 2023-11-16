from utils import send_alert_message, send_service_message, get_config, draw_graph
from configparser import RawConfigParser
from ccxt.base.exchange import Exchange
from threading import Thread
from decimal import Decimal
from loguru import logger

import schedule
import time
import json
import ccxt
import os


def get_tickers_prices(exchange: Exchange, exchange_name: str, nums_precision: int) -> dict:
    prices = {}
    try:
        if exchange_name in ('binance', 'bybit'):
            response = exchange.fetch_tickers()
            tickers = [tckr for tckr in response if 'USDT' in tckr and response[tckr]['last'] is not None]
            prices.update({ticker: response[ticker]['last'] for ticker in tickers if response[ticker]['last'] > 1/10**nums_precision})
        elif exchange_name == 'kucoin':
            response = exchange.fetch_markets()
            tickers = [tckr for tckr in response if tckr['info']['quoteCurrency'] == 'USDT']
            prices.update({ticker['symbol']: ticker['info']['lastTradePrice'] for ticker in tickers if ticker['info']['lastTradePrice'] > 1/10**nums_precision})
    except Exception as e:
        logger.error(f'Error {exchange_name} | {e}')
        return {}   
    return prices


def get_tickers_data(exchange_name: str) -> dict:
    while True:
        try:
            with open(f'temp/{exchange_name}_tickers.json') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(e)
            return {}


def update_tickers_info(exchange_name: str, tickers_info: dict) -> None:
    while True:
        try:
            with open(f'temp/{exchange_name}_tickers.json', 'w') as f:
                json.dump(tickers_info, f, indent=4)
            break
        except Exception as e:
            logger.error(e)


def watcher(exchange, exchange_name: str, nums_precision: int) -> None:
    tickers_prices = get_tickers_prices(exchange, exchange_name, nums_precision)
    k = 0
    while tickers_prices == {}:
        tickers_prices = get_tickers_prices(exchange, exchange_name, nums_precision)
        k += 1
        if k > 10:
            logger.error(f'{exchange_name} | Too many errors while getting tickers. Exit.')
            return
    data_filename = f'temp/{exchange_name}_tickers.json'
    if os.path.exists(data_filename):
        try:
            data = get_tickers_data(exchange_name)
            for ticker in tickers_prices:
                if ticker not in data:
                    data[ticker] = [tickers_prices[ticker]]
                else:
                    data[ticker].insert(0, tickers_prices[ticker])
                    if len(data[ticker]) > 10:
                        del data[ticker][-1]
            update_tickers_info(exchange_name, data)
        except Exception as e:
            logger.error(e)
    else:
        data = {}
        for ticker in tickers_prices:
            data[ticker] = [tickers_prices[ticker]]
        update_tickers_info(exchange_name, data)


def course_watcher(exchange, exchange_name: str, nums_precision: int) -> None:
    watcher(exchange, exchange_name, nums_precision)
    schedule.every(1).minutes.do(lambda: watcher(exchange, exchange_name, nums_precision))
    while True:
        schedule.run_pending()
        time.sleep(0.1)


def sender(config: RawConfigParser, exchange_name: str) -> None:
    exchange_classes = {
        'binance': ccxt.binance,
        'bybit': ccxt.bybit,
        'kucoin': ccxt.kucoinfutures
    }
    if exchange_name not in exchange_classes:
        raise BaseException('Exchange isn\'t supported')
    percent_difference = float(config[exchange_name]['percent_difference'])
    nums_precision = int(config['telegram']['nums_precision'])
    exchange: Exchange = exchange_classes[exchange_name]()
    Thread(target=course_watcher, args=(exchange,exchange_name,nums_precision)).start()
    send_service_message(get_config(), f'{exchange_name.capitalize()} watcher started', exchange_name)
    while True:
        changed = False
        tickers_prices = get_tickers_data(exchange_name)
        for ticker in tickers_prices:
            minutes_prices_list = tickers_prices[ticker]
            if not minutes_prices_list:
                continue
            new_price = minutes_prices_list[0]
            for index, old_price in enumerate(minutes_prices_list):
                if old_price * (1 + percent_difference / 100) <= new_price:
                    now_time = exchange.fetch_time()
                    yesterday_timestamp = now_time - 24*60*60*10**3
                    yesterday_price = exchange.fetch_ohlcv(ticker, '1m', yesterday_timestamp, 1)[0][4]
                    yesterday_change = round(Decimal((new_price/yesterday_price-1)*100), nums_precision)

                    half_hour_timestamp = now_time - 30*60*10**3
                    half_hour_price = exchange.fetch_ohlcv(ticker, '1m', half_hour_timestamp, 1)[0][4]
                    half_hour_change = round(Decimal((new_price/half_hour_price-1)*100), nums_precision)
                    with open('message.txt') as f:
                        msg = f.read()
                    msg = msg.format(
                        ticker=ticker, new_price=round(Decimal(new_price), nums_precision),
                        old_price=round(Decimal(old_price), nums_precision),
                        diff=round(Decimal(new_price-old_price), nums_precision),
                        percent_diff=round(Decimal((new_price/old_price-1)*100), nums_precision),
                        minutes=index+1,yesterday_change=yesterday_change,half_hour_change=half_hour_change
                    )
                    send_alert_message(get_config(), msg, draw_graph(exchange, ticker, exchange_name, new_price))
                    tickers_prices[ticker].clear()
                    changed = True
                    break
        if changed:
            update_tickers_info(exchange_name, tickers_prices)
        time.sleep(20)


def worker(exchange_name: str):
    if not os.path.exists('temp'):
        os.mkdir('temp')
    update_tickers_info(exchange_name, {})
    config = get_config()
    sender(config, exchange_name)

