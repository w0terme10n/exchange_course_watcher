from utils import send_message_to_telegram, get_config, draw_graph
from decimal import Decimal
from loguru import logger
from time import sleep

import ccxt
            

def main():
    config = get_config()
    api_key = config['binance']['apiKey']
    api_secret = config['binance']['secret']
    percent_difference = float(config['binance']['percent_difference'])
    nums_precision = int(config['telegram']['nums_precision'])

    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret
    })

    send_message_to_telegram(get_config(), 'Binance watcher started', exchange_name='binance')

    tickers_prices = {}
    tickers = exchange.fetch_tickers()
    for ticker in tickers:
        if 'USDT' in ticker and tickers[ticker]['last'] != 0 and tickers[ticker]['last'] is not None:
            tickers_prices.update({ticker: [tickers[ticker]['last']]})

    sleep(60)

    while True:
        try:
            tickers = exchange.fetch_tickers()
        except Exception as e:
            logger.error(f'Binance | Error while getting tickers\n{e}')
            continue
        
        for ticker in tickers:
            if ticker in tickers_prices and tickers[ticker]['last'] != 0 and tickers[ticker]['last'] is not None:
                try:
                    new_price = tickers[ticker]['last']
                    minutes_prices_list = tickers_prices[ticker]
                    for index, old_price in enumerate(minutes_prices_list):
                        if old_price * (1 + percent_difference / 100) <= new_price:
                            msg = open('message.txt').read().format(
                                ticker=ticker, new_price=round(Decimal(new_price), nums_precision),
                                old_price=round(Decimal(old_price), nums_precision),
                                diff=round(Decimal(new_price-old_price), nums_precision),
                                percent_diff=round(Decimal((new_price/old_price-1)*100), nums_precision),
                                minutes=index+1
                            )
                            send_message_to_telegram(get_config(), msg, image=draw_graph(exchange, ticker, 'Binance'))
                            tickers_prices[ticker].clear()
                            break

                    tickers_prices[ticker].insert(0, new_price)
                    if len(tickers_prices[ticker]) > 10:
                        del tickers_prices[ticker][-1]
                except Exception as e:
                    logger.error(e)

        sleep(60)


if __name__ == '__main__':
    try:
        main()
    except ccxt.errors.AuthenticationError:
        send_message_to_telegram(get_config(), 'API token expired', exchange_name='binance')
