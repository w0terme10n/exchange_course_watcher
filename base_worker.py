from utils import *
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
    """
    The function `get_tickers_prices` retrieves ticker prices from different exchanges based on the
    exchange name and precision of the numbers.
    
    :param exchange: The `exchange` parameter is an instance of the `Exchange` class, which is used to
    interact with the API of a specific cryptocurrency exchange
    :type exchange: Exchange
    :param exchange_name: The `exchange_name` parameter is a string that specifies the name of the
    exchange. It can be one of the following values: 'binance', 'bybit', or 'kucoin'
    :type exchange_name: str
    :param nums_precision: The `nums_precision` parameter is an integer that represents the number of
    decimal places to consider when filtering tickers based on their last trade price. For example, if
    `nums_precision` is set to 2, tickers with a last trade price less than 0.01 will be excluded from
    :type nums_precision: int
    :return: a dictionary containing ticker symbols as keys and their corresponding prices as values.
    """
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
    """
    The function `get_tickers_data` retrieves ticker data from a JSON file based on the exchange name
    and returns it as a dictionary.
    
    :param exchange_name: The exchange_name parameter is a string that represents the name of the
    exchange. It is used to construct the file path for the tickers data file
    :type exchange_name: str
    :return: a dictionary.
    """
    while True:
        try:
            with open(f'temp/{exchange_name}_tickers.json') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.error(e)
            return {}


def update_tickers_info(exchange_name: str, tickers_info: dict) -> None:
    """
    The function `update_tickers_info` writes the `tickers_info` dictionary to a JSON file with the name
    `exchange_name_tickers.json` in the `temp` directory.
    
    :param exchange_name: The exchange_name parameter is a string that represents the name of the
    exchange. It is used to create a unique filename for the JSON file that will store the tickers
    information
    :type exchange_name: str
    :param tickers_info: The `tickers_info` parameter is a dictionary that contains information about
    tickers. It is used to store and update ticker information for a specific exchange
    :type tickers_info: dict
    """
    while True:
        try:
            with open(f'temp/{exchange_name}_tickers.json', 'w') as f:
                json.dump(tickers_info, f, indent=4)
            break
        except Exception as e:
            logger.error(e)


def watcher(exchange, exchange_name: str, nums_precision: int) -> None:
    """
    The `watcher` function retrieves ticker prices from an exchange, stores them in a JSON file, and
    updates the ticker information if the file already exists.
    
    :param exchange: The "exchange" parameter is an object or instance of a class that represents a
    cryptocurrency exchange. It is used to interact with the exchange's API and retrieve ticker prices
    :param exchange_name: The `exchange_name` parameter is a string that represents the name of the
    exchange. It is used as a unique identifier for the exchange in various parts of the code
    :type exchange_name: str
    :param nums_precision: The `nums_precision` parameter is an integer that represents the number of
    decimal places to round the ticker prices to
    :type nums_precision: int
    :return: The function `watcher` does not return anything. It performs some operations and updates
    tickers information, but it does not have a return statement.
    """
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
    """
    The function `course_watcher` sets up a schedule to periodically call the `watcher` function with
    the specified parameters.
    
    :param exchange: The "exchange" parameter is the object or instance of the exchange that you want to
    watch. It could be an API client or a connection to a trading platform
    :param exchange_name: The `exchange_name` parameter is a string that represents the name of the
    exchange. It is used as a parameter in the `watcher` function
    :type exchange_name: str
    :param nums_precision: The `nums_precision` parameter is an integer that represents the number of
    decimal places to round the numbers to. It is used in the `watcher` function to format the numbers
    before displaying them
    :type nums_precision: int
    """
    watcher(exchange, exchange_name, nums_precision)
    schedule.every(1).minutes.do(lambda: watcher(exchange, exchange_name, nums_precision))
    while True:
        schedule.run_pending()
        time.sleep(0.1)


def sender(config: RawConfigParser, exchange_name: str) -> None:
    """
    The `sender` function is a function that sends alerts based on price changes in
    cryptocurrency tickers.
    
    :param config: The `config` parameter is an instance of the `RawConfigParser` class, which is used
    to read configuration files. It contains various settings and values that are used by the `sender`
    function
    :type config: RawConfigParser
    :param exchange_name: The `exchange_name` parameter is a string that represents the name of the
    cryptocurrency exchange. It is used to determine which exchange class to use for fetching data and
    performing operations. The supported exchange names are 'binance', 'bybit', and 'kucoin'
    :type exchange_name: str
    """
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
                    try:
                        yesterday_price = exchange.fetch_ohlcv(ticker, '1m', yesterday_timestamp, 1)[0][4]
                        yesterday_change = round(Decimal((new_price/yesterday_price-1)*100), nums_precision)
                    except Exception as e:
                        logger.error(e)
                        break

                    half_hour_timestamp = now_time - 30*60*10**3
                    half_hour_price = exchange.fetch_ohlcv(ticker, '1m', half_hour_timestamp, 1)[0][4]
                    half_hour_change = round(Decimal((new_price/half_hour_price-1)*100), nums_precision)
                    with open('message.txt') as f:
                        msg = f.read()
                    if is_have_recent_news(config, ticker.split('/')[0]):
                        news = '🚩Coin news for the last 24 hours🚩'
                    else:
                        news = '📢No coin news in the last 24 hours'
                    msg = msg.format(
                        ticker=ticker, new_price=round(Decimal(new_price), nums_precision),
                        old_price=round(Decimal(old_price), nums_precision), news=news,
                        diff=round(Decimal(new_price-old_price), nums_precision),
                        percent_diff=round(Decimal((new_price/old_price-1)*100), nums_precision),
                        minutes=index+1, yesterday_change=yesterday_change, half_hour_change=half_hour_change
                    )
                    send_alert_message(get_config(), msg, draw_graph(exchange, ticker, exchange_name, new_price))
                    tickers_prices[ticker].clear()
                    changed = True
                    break
        if changed:
            update_tickers_info(exchange_name, tickers_prices)
        time.sleep(20)


def worker(exchange_name: str):
    """
    The function `worker` creates a temporary directory if it doesn't exist, updates tickers information
    for a given exchange, retrieves a configuration, and sends the configuration and exchange name to a
    sender function.
    
    :param exchange_name: The exchange name is a string that represents the name of the cryptocurrency
    exchange. It is used as a parameter in the `worker` function to perform certain operations specific
    to that exchange
    :type exchange_name: str
    """
    if not os.path.exists('temp'):
        os.mkdir('temp')
    update_tickers_info(exchange_name, {})
    config = get_config()
    sender(config, exchange_name)
