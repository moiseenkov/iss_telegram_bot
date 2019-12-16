import logging
import time

import requests
import telebot
from environs import Env
from telebot import apihelper
from telebot.types import Message


URL_ISS_LOCATION = 'http://api.open-notify.org/iss-now.json'

logging.basicConfig(filename='iss_bot.log',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

env = Env()
env.read_env()
TOKEN = env('TOKEN')
PROXY = env('PROXY')


if PROXY:
    apihelper.proxy = dict(https=PROXY)

bot = telebot.TeleBot(TOKEN, threaded=False)


@bot.message_handler(commands=['where'])
def send_iss_position(message: Message):
    msg = f'/where command from user {message.from_user}'
    try:
        response = requests.get(URL_ISS_LOCATION)
        if response.status_code == 200:
            pos = response.json()['iss_position']
            bot.send_location(message.chat.id, **pos)
            bot.send_message(message.chat.id, text=f'Current ISS position is: {pos["latitude"]}°, {pos["longitude"]}°')
            logging.info(msg + ' OK')
        else:
            raise ConnectionError
    except ConnectionError as conn:
        msg += f' FAILED due to response status code {response.status_code} from {URL_ISS_LOCATION};' \
               f' response data: {response.json()}'
        logging.error(msg)
    except Exception as exception:
        logging.exception(msg + f' FAILED with exception {exception}')


while True:
    try:
        bot.polling(timeout=123, none_stop=True)
    except requests.exceptions.ConnectionError as ex:
        logging.exception(f'Exception: {ex}')
        time.sleep(5)
