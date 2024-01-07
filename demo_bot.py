from utils import get_config, send_photo_to_telegram
from loguru import logger

import time
import json
import os


def main():
    last_msg_filename = 'temp/last_msg.json'
    if not os.path.exists('temp/'):
        os.mkdir('temp')
    if not os.path.exists(last_msg_filename):
        with open(last_msg_filename, 'w') as f:
            json.dump({'time': int(time.time())}, f)
    config = get_config()
    sleep_hours = float(config['demo_bot']['sleep_hours'])
    demo_chat_id = get_config()['demo_bot']['demo_chat_id']
    demo_bot_token = get_config()['demo_bot']['demo_bot_token']
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
                        send_photo_to_telegram(demo_bot_token, demo_chat_id, new_msg['msg'], image)
                        break
                    time.sleep(1)
                except json.decoder.JSONDecodeError:
                    pass
            time.sleep(60*60*sleep_hours)
        except Exception as e:
            logger.error(e)


if __name__ == '__main__':
    main()