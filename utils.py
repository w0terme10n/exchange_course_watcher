from configparser import RawConfigParser
import plotly.graph_objects as go
from datetime import datetime
from loguru import logger

import json
import requests
import time



def draw_graph(exchange, ticker, exchange_name):
    graph_start_time = exchange.fetch_time() - 30*60*10**3
    candlesticks = exchange.fetch_ohlcv(ticker, since=graph_start_time)
    now_price = exchange.fetch_ticker(ticker)['last']
    dates_data = [datetime.fromtimestamp(i[0]/10**3) for i in candlesticks]
    open_data = [i[1] for i in candlesticks]
    high_data = [i[2] for i in candlesticks]
    low_data = [i[3] for i in candlesticks]
    close_data = [i[4] for i in candlesticks]
    # volume_data = [i[5] for i in candlesticks]

    candlestick_chart = go.Candlestick(
        x=dates_data,
        open=open_data,
        high=high_data,
        low=low_data,
        close=close_data
    )
    fig = go.Figure(data=[candlestick_chart])
    fig.update_layout(title=f'{exchange_name}: {ticker}')
    fig.add_hline(y=now_price, line_color='yellow', label={'text': 'Signal price', 'textposition': 'start', 'font': {'color': 'yellow', 'size': 14, 'family': 'Arial'}})
    fig.update_layout(template='plotly_dark')
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_xaxes(visible=False)
    fig.update_layout(yaxis={'side': 'right'})
    return fig.to_image(format='png')


def get_config():
    config = RawConfigParser()
    config.read('config.cfg')
    return config


def send_message_to_telegram(config, msg, image=None, exchange_name=None):
    if image is None and exchange_name is None:
        raise BaseException('Both image and exchange_name arguments are None')
    bot_token = config['telegram']['token']
    chat_ids = [config['telegram'][chat_id] for chat_id in config['telegram'] if chat_id.startswith('chat_id')]
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    if 'started' not in msg:
        while True:
            try:
                with open('last_msg.json', 'w') as f:
                    t = {'msg': msg, 'time': int(time.time())}
                    json.dump(t, f)
                break
            except:
                pass
    if image:
        while True:
            try:
                with open('graph.png', 'wb') as f:
                    f.write(image)
                    break
            except:
                pass
    else:
        image = open(f'{exchange_name}_img.png', 'rb')
    for chat_id in chat_ids:
        k = 0
        r = {'ok': False}
        while not r['ok'] and k < 5:
            try:
                r = requests.post(
                    url, data={
                        'chat_id': chat_id, 'caption': msg, 'parse_mode': 'HTML'
                    }, files={'photo': image}
                ).json()
                if not r['ok']:
                    logger.error(f'Error sending msg to {chat_id}\n{r["description"]}')
            except Exception as e:
                logger.error(e)
            k += 1