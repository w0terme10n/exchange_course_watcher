from configparser import RawConfigParser
from ccxt.base.exchange import Exchange
import plotly.graph_objects as go
from datetime import datetime
from loguru import logger

import requests
import json
import time


def draw_graph(exchange: Exchange, ticker: str, exchange_label: str, now_price: float) -> bytes:
    graph_start_time = exchange.fetch_time() - 500*60*10**3
    candlesticks = exchange.fetch_ohlcv(ticker, timeframe='5m', since=graph_start_time)
    dates_data = [datetime.fromtimestamp(i[0]/10**3) for i in candlesticks]
    open_data = [i[1] for i in candlesticks]
    high_data = [i[2] for i in candlesticks]
    low_data = [i[3] for i in candlesticks]
    close_data = [i[4] for i in candlesticks]
    # volume_data = [i[5] for i in candlesticks]

    layout = go.Layout(
        autosize=False,
        width=1000,
        height=600,
        title=f'{ticker}',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        yaxis=dict(side='right'),
        xaxis=dict(showticklabels=False, title=dict(text=f'{exchange_label.capitalize()}', font=dict(size=20, color='#FFFFFF')))
    )
    candlestick_chart = go.Candlestick(
        x=dates_data,
        open=open_data,
        high=high_data,
        low=low_data,
        close=close_data
    )
    fig = go.Figure(data=[candlestick_chart], layout=layout)
    # sudo apt install fonts-noto-color-emoji
    fig.add_hline(y=now_price, line_color='yellow', label=dict(text='<b>🚨Signal price🚨</b>', textposition='start', font=dict(color='yellow', size=14, family='Noto Color Emoji;sans-serif')))    
    return fig.to_image(format='png')
    

def get_config() -> RawConfigParser:
    config = RawConfigParser()
    config.read('config.cfg')
    return config


def send_photo_to_telegram(bot_token: str, chat_id: str, msg: str, image: bytes) -> None:
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    r = {'ok': False}
    k = 0
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


def send_service_message(config: RawConfigParser, msg: str, exchange_name: str) -> None:
    bot_token = config['telegram']['token']
    chat_ids = [config['telegram'][chat_id] for chat_id in config['telegram'] if chat_id.startswith('chat_id')]
    image = open(f'img/{exchange_name}_img.png', 'rb')
    for chat_id in chat_ids:
        send_photo_to_telegram(bot_token, chat_id, msg, image)


def send_alert_message(config: RawConfigParser, msg: str, graph_img: bytes) -> None:
    bot_token = config['telegram']['token']
    chat_ids = [config['telegram'][chat_id] for chat_id in config['telegram'] if chat_id.startswith('chat_id')]
    while True:
        try:
            with open('temp/last_msg.json', 'w') as f:
                t = {'msg': msg, 'time': int(time.time())}
                json.dump(t, f)
            break
        except Exception as e:
            logger.error(e)
    while True:
        try:
            with open('temp/graph.png', 'wb') as f:
                f.write(graph_img)
            break
        except Exception as e:
            logger.error(e)
    for chat_id in chat_ids:
        send_photo_to_telegram(bot_token, chat_id, msg, graph_img)
