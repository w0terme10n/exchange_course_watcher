from utils import send_message_to_telegram, get_config, draw_graph
from decimal import Decimal
from loguru import logger
from time import sleep

import ccxt


def main():
    config = get_config()
    api_key = config['bybit']['apiKey']
    api_secret = config['bybit']['secret']
    percent_difference = float(config['bybit']['percent_difference'])
    nums_precision = int(config['telegram']['nums_precision'])

    exchange = ccxt.bybit({
        'apiKey': api_key,
        'secret': api_secret
    })

    send_message_to_telegram(get_config(), 'Bybit watcher started', exchange_name='bybit')

    tickers_prices = {}
    derivatives_tickers = exchange.fetch_tickers()
    for ticker in [tckr for tckr in derivatives_tickers if 'USDT' in tckr]:
        tickers_prices.update({ticker: [derivatives_tickers[ticker]['last']]})

    sleep(60)

    while True:
        try:
            derivatives_tickers = exchange.fetch_tickers()
        except Exception as e:
            logger.error(f'Bybit | Error while getting derivatives tickers\n{e}')
            continue

        for ticker in [tckr for tckr in derivatives_tickers if 'USDT' in tckr and tckr in tickers_prices]:
            try:
                new_price = derivatives_tickers[ticker]['last']
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
                        send_message_to_telegram(get_config(), msg, image=draw_graph(exchange, ticker, 'Bybit'))
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
        send_message_to_telegram(get_config(), 'API token expired', exchange_name='bybit')
