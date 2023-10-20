from utils import send_message_to_telegram, get_config, draw_graph
from decimal import Decimal
from loguru import logger
from time import sleep

import ccxt


def main():
    config = get_config()
    api_key = config['kucoin']['apiKey']
    api_secret = config['kucoin']['secret']
    percent_difference = float(config['kucoin']['percent_difference'])
    nums_precision = int(config['telegram']['nums_precision'])

    exchange = ccxt.kucoinfutures({
        'apiKey': api_key,
        'secret': api_secret
    })

    send_message_to_telegram(get_config(), 'Kucoin watcher started', exchange_name='kucoin')

    tickers_prices = {}
    tickers = exchange.fetch_markets()
    for ticker in tickers:
        if ticker['info']['quoteCurrency'] == 'USDT':
            tickers_prices.update({ticker['symbol']: [ticker['info']['lastTradePrice']]})

    sleep(60)

    while True:
        try:
            tickers = exchange.fetch_markets()

        except Exception as e:
            logger.error(f'Kucoin | Error while getting tickers\n{e}')
            continue

        for ticker in tickers:
            if ticker['symbol'] in tickers_prices:
                try:
                    new_price = ticker['info']['lastTradePrice']
                    minutes_prices_list = tickers_prices[ticker['symbol']]
                    for index, old_price in enumerate(minutes_prices_list):
                        if old_price * (1 + percent_difference / 100) <= new_price:
                            msg = open('message.txt').read().format(
                                ticker=ticker['symbol'], new_price=round(Decimal(new_price), nums_precision),
                                old_price=round(Decimal(old_price), nums_precision),
                                diff=round(Decimal(new_price-old_price), nums_precision),
                                percent_diff=round(Decimal((new_price/old_price-1)*100), nums_precision),
                                minutes=index+1
                            )
                            send_message_to_telegram(get_config(), msg, image=draw_graph(exchange, ticker, 'Kucoin futures'))
                            tickers_prices[ticker['symbol']].clear()
                            break

                    tickers_prices[ticker['symbol']].insert(0, new_price)
                    if len(tickers_prices[ticker['symbol']]) > 10:
                        del tickers_prices[ticker['symbol']][-1]

                except Exception as e:
                    logger.error(e)

        sleep(60)


if __name__ == '__main__':
    main()
