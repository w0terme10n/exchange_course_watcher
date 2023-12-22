from configparser import RawConfigParser
from ccxt.base.exchange import Exchange
import plotly.graph_objects as go
from datetime import datetime
from loguru import logger

import requests
import json
import time


def draw_graph(exchange: Exchange, ticker: str, exchange_label: str, now_price: float) -> bytes:
    """
    The function `draw_graph` takes in exchange information, ticker symbol, exchange label, and current
    price, and returns a graph image of candlestick data with a horizontal line indicating the current
    price.
    
    :param exchange: The `exchange` parameter is an object representing a cryptocurrency exchange.
    :type exchange: Exchange
    :param ticker: The `ticker` parameter is a string that represents the trading pair
    :type ticker: str
    :param exchange_label: The `exchange_label` parameter is a string that represents the label or name
    of the exchange. It is used to provide a title for the graph and as the x-axis title
    :type exchange_label: str
    :param now_price: The `now_price` parameter represents the current price of the ticker on the
    exchange
    :type now_price: float
    :return: a bytes object, which represents an image in PNG format.
    """
    graph_start_time = exchange.fetch_time() - 800*60*10**3
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
    fig.add_hline(
        y=now_price, line_color='yellow',
        label=dict(
            text='<b>🚨Signal price🚨</b>',
            textposition='start',
            font=dict(color='yellow',size=14,family='Noto Color Emoji;sans-serif')
        )
    )    
    return fig.to_image(format='png')
    

def get_config() -> RawConfigParser:
    """
    The function `get_config()` reads and returns a `RawConfigParser` object from a configuration file
    named 'config.cfg'.
    :return: an instance of the `RawConfigParser` class.
    """
    config = RawConfigParser()
    config.read('config.cfg')
    return config


def send_photo_to_telegram(bot_token: str, chat_id: str, msg: str, image: bytes) -> None:
    """
    The function `send_photo_to_telegram` sends a photo to a Telegram chat using the provided bot token,
    chat ID, message, and image data.
    
    :param bot_token: The `bot_token` parameter is a string that represents the token of your Telegram
    bot. You can obtain this token by creating a new bot on Telegram and following the instructions
    provided by the BotFather
    :type bot_token: str
    :param chat_id: The `chat_id` parameter is the unique identifier for the chat or conversation where
    you want to send the photo. It can be a user's private chat ID or a group chat ID
    :type chat_id: str
    :param msg: The `msg` parameter is a string that represents the caption or message that you want to
    send along with the photo. It can be used to provide additional context or information about the
    photo
    :type msg: str
    :param image: The `image` parameter is of type `bytes` and represents the image file that you want
    to send to Telegram. It should be the binary representation of the image file
    :type image: bytes
    """
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
    """
    The function sends a service message with an image to multiple Telegram chat IDs using a bot token
    and a configuration file.
    
    :param config: The `config` parameter is an instance of the `RawConfigParser` class, which is used
    to read configuration files. It contains the configuration settings for the Telegram bot, including
    the bot token and chat IDs
    :type config: RawConfigParser
    :param msg: The `msg` parameter is a string that represents the message you want to send as a
    service message. It could be any text or information that you want to communicate to the recipients
    :type msg: str
    :param exchange_name: The `exchange_name` parameter is a string that represents the name of the
    exchange. It is used to construct the filename of the image that will be sent in the message
    :type exchange_name: str
    """
    bot_token = config['telegram']['token']
    chat_ids = [config['telegram'][chat_id] for chat_id in config['telegram'] if chat_id.startswith('chat_id')]
    image = open(f'img/{exchange_name}_img.png', 'rb')
    for chat_id in chat_ids:
        send_photo_to_telegram(bot_token, chat_id, msg, image)


def send_alert_message(config: RawConfigParser, msg: str, graph_img: bytes) -> None:
    """
    The function `send_alert_message` sends an alert message with a graph image to multiple Telegram
    chat IDs using a Telegram bot token.
    
    :param config: The `config` parameter is an instance of the `RawConfigParser` class, which is used
    to read configuration files. It contains information such as the Telegram bot token and chat IDs
    :type config: RawConfigParser
    :param msg: The `msg` parameter is a string that represents the message you want to send as an
    alert. It could be any text message that you want to notify the users about
    :type msg: str
    :param graph_img: The `graph_img` parameter is of type `bytes` and represents the image data of a
    graph. It is expected to be in the form of bytes, which can be written to a file or sent as an
    attachment in a message
    :type graph_img: bytes
    """
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


def is_have_recent_news(config: RawConfigParser, coin: str) -> bool:
    """
    The function `is_have_recent_news` checks if there is recent news about a specific cryptocurrency by
    making a request to the CryptoPanic API and comparing the publication date of the latest news post
    with the current date.
    
    :param config: The `config` parameter is an instance of the `RawConfigParser` class, which is used
    to read configuration files. It is used to retrieve the API token for the Cryptopanic API
    :type config: RawConfigParser
    :param coin: The `coin` parameter is a string that represents the cryptocurrency for which you want
    to check if there are recent news articles
    :type coin: str
    :return: a boolean value. It returns True if there is recent news available for the specified coin,
    and False otherwise.
    """
    api_token = config['news']['cryptopanic_token']
    url = f'https://cryptopanic.com/api/v1/posts/?auth_token={api_token}&kind=news&currencies={coin}'
    try:
        r = requests.get(url)
        if r.status_code == 200:
            response = r.json()['results']
            if response:
                latest_post = response[0]
                post_date = datetime.strptime(latest_post['published_at'], '%Y-%m-%dT%H:%M:%SZ')
                now_date = datetime.now()
                if (now_date - post_date).days == 0:
                    return True
    except Exception as e:
        logger.error(e)
    return False
