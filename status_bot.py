from aiogram import Bot, Dispatcher, executor, types
from configparser import RawConfigParser

import subprocess
import logging


config = RawConfigParser()
config.read('config.cfg')
API_TOKEN = config['telegram']['token']
BYBIT_WATCHER_SERVICE_NAME = config['bybit']['service_name']
KUCOIN_WATCHER_SERVICE_NAME = config['kucoin']['service_name']
BINANCE_WATCHER_SERVICE_NAME = config['binance']['service_name']
DEMO_BOT_SERVICE_NAME = config['demo_bot']['service_name']

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'status'])
async def status(message: types.Message):
    bybit_watcher_status = subprocess.run(
        f'systemctl is-active {BYBIT_WATCHER_SERVICE_NAME}', shell=True,
        stdout=subprocess.PIPE, universal_newlines=True
    ).stdout
    kucoin_watcher_status = subprocess.run(
        f'systemctl is-active {KUCOIN_WATCHER_SERVICE_NAME}', shell=True,
        stdout=subprocess.PIPE, universal_newlines=True
    ).stdout
    binance_watcher_status = subprocess.run(
        f'systemctl is-active {BINANCE_WATCHER_SERVICE_NAME}', shell=True,
        stdout=subprocess.PIPE, universal_newlines=True
    ).stdout
    demo_bot_status = subprocess.run(
        f'systemctl is-active {DEMO_BOT_SERVICE_NAME}', shell=True,
        stdout=subprocess.PIPE, universal_newlines=True
    ).stdout
    await message.answer(
        f'Hello! I\'m status bot!\nBinance watcher status: {binance_watcher_status}Bybit watcher status: {bybit_watcher_status}Kucoin watcher status: {kucoin_watcher_status}DEMO bot status: {demo_bot_status}'
    )


@dp.message_handler(commands=['start_watchers'])
async def start_watchers(message: types.Message):
    await message.answer('Watchers are starting')
    subprocess.run(f'sudo systemctl start {BINANCE_WATCHER_SERVICE_NAME}', shell=True)
    subprocess.run(f'sudo systemctl start {BYBIT_WATCHER_SERVICE_NAME}', shell=True)
    subprocess.run(f'sudo systemctl start {KUCOIN_WATCHER_SERVICE_NAME}', shell=True)


@dp.message_handler(commands=['stop_watchers'])
async def stop_watchers(message: types.Message):
    subprocess.run(f'sudo systemctl stop {BINANCE_WATCHER_SERVICE_NAME}', shell=True)
    subprocess.run(f'sudo systemctl stop {BYBIT_WATCHER_SERVICE_NAME}', shell=True)
    subprocess.run(f'sudo systemctl stop {KUCOIN_WATCHER_SERVICE_NAME}', shell=True)
    await message.answer('All watchers are stopped')


@dp.message_handler(commands=['start_demo_bot'])
async def start_demo_bot(message: types.Message):
    await message.answer('Demo bot is starting')
    subprocess.run(f'sudo systemctl start {DEMO_BOT_SERVICE_NAME}', shell=True)


@dp.message_handler(commands=['stop_demo_bot'])
async def stop_demo_bot(message: types.Message):
    subprocess.run(f'sudo systemctl stop {DEMO_BOT_SERVICE_NAME}', shell=True)
    await message.answer('Demo bot was stopped')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)