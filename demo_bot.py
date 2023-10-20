from utils import get_config
from loguru import logger
import time
import json
import requests


def send_message_to_telegram(config, msg):
    bot_token = config['demo_bot']['demo_bot_token']
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    chat_id = config['demo_bot']['demo_chat_id']
    k = 0
    r = {'ok': False}
    while not r['ok'] and k < 5:
        try:
            r = requests.post(
                url, data={
                    'chat_id': chat_id, 'caption': msg, 'parse_mode': 'HTML'
                }, files={'photo': open('graph.png', 'rb')}
            ).json()
            if not r['ok']:
                logger.error(f'Error sending msg to {chat_id}\n{r["description"]}')
        except Exception as e:
            logger.error(e)
        k += 1


def main():
    sleep_hours = float(get_config()['demo_bot']['sleep_hours'])
    while True:
        try:
            with open('last_msg.json') as f:
                msg = json.load(f)
            while True:
                try:
                    with open('last_msg.json') as file:
                        new_msg = json.load(file)
                    if msg['time'] != new_msg['time']:
                        send_message_to_telegram(get_config(), new_msg['msg'])
                        break
                    time.sleep(1)
                except json.decoder.JSONDecodeError:
                    pass
            while True:
                try:
                    sleep_hours = float(get_config()['demo_bot']['sleep_hours'])
                    break
                except Exception as exc:
                    logger.error(exc)
            time.sleep(60*60*sleep_hours)
        except Exception as e:
            logger.error(e)


if __name__ == '__main__':
    main()