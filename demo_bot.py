from utils import get_config, send_alert_message
from loguru import logger

import time
import json
import os


def get_sleep_hours():
    return float(get_config()['demo_bot']['sleep_hours'])


def main():
    last_msg_filename = 'temp/last_msg.json'
    if not os.path.exists('temp/'):
        os.mkdir('temp')
    if not os.path.exists(last_msg_filename):
        with open(last_msg_filename, 'w') as f:
            json.dump({'time': int(time.time())}, f)
    sleep_hours = get_sleep_hours()
    while True:
        try:
            with open(last_msg_filename) as f:
                msg = json.load(f)
            while True:
                try:
                    with open(last_msg_filename) as file:
                        new_msg = json.load(file)
                    if msg['time'] != new_msg['time']:
                        with open('temp/graph.png', 'rb') as f:
                            image = f.read()
                        send_alert_message(get_config(), new_msg['msg'], image)
                        break
                    time.sleep(1)
                except json.decoder.JSONDecodeError:
                    pass
            while True:
                try:
                    sleep_hours = get_sleep_hours()
                    break
                except Exception as exc:
                    logger.error(exc)
            time.sleep(60*60*sleep_hours)
        except Exception as e:
            logger.error(e)


if __name__ == '__main__':
    main()