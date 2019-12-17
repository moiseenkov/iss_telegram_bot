"""
Bot provides some information about current state of International Space Station
"""
import logging
import time
from collections import defaultdict
from datetime import datetime

import requests
import telebot
from environs import Env
from telebot import apihelper, types
from telebot.types import Message


URL_ISS_LOCATION = 'http://api.open-notify.org/iss-now.json'
URL_ISS_CREW = 'http://api.open-notify.org/astros.json'
URL_ISS_PASS_TIMES = 'http://api.open-notify.org/iss-pass.json'

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


def keyboard():
    """
    Function generates keyboard
    Returns: InlineKeyboardMarkup instance
    """
    _keyboard = types.ReplyKeyboardMarkup(row_width=1)
    button_position = types.KeyboardButton(text='Position')
    button_crew = types.KeyboardButton(text='Crew')
    button_pass_times = types.KeyboardButton(text='Pass times', request_location=True)
    _keyboard.add(button_position)
    _keyboard.add(button_crew)
    _keyboard.add(button_pass_times)
    return _keyboard


def get_iss_position(message: Message):
    """
    Shows current geo position of ISS
    Args:
        message: telebot.types.Message instance
    """
    response = requests.get(URL_ISS_LOCATION)
    if response.status_code == 200:
        _position = response.json()['iss_position']
        bot.send_location(message.chat.id, **_position)
        bot.send_message(chat_id=message.chat.id,
                         text=f'*Current ISS position is: '
                              f'{_position["latitude"]}°, {_position["longitude"]}°*',
                         parse_mode='Markdown',
                         reply_markup=keyboard())
    return response


def get_iss_crew(message: Message):
    """
    Shows current crew of ISS
    Args:
        message: telebot.types.Message instance
    """
    response = requests.get(URL_ISS_CREW)
    if response.status_code == 200:
        data = response.json()
        names = [human['name'] for human in data['people']]
        text = f'*Current crew is {data["number"]} humans:*\n' + ',\n'.join(names)
        bot.send_message(chat_id=message.chat.id, text=text, parse_mode='Markdown',
                         reply_markup=keyboard())
    return response


def get_iss_pass_times(message: Message):
    """
    Shows times when ISS will have the same position as user
    Args:
        message: telebot.types.Message instance
    """
    parameters = {
        'lat': message.location.latitude,
        'lon': message.location.longitude,
    }
    response = requests.get(url=URL_ISS_PASS_TIMES, params=parameters)
    if response.status_code == 200:
        pass_times = (item['risetime'] for item in response.json()['response'])
        pass_times = (datetime.fromtimestamp(item) for item in pass_times)
        pass_times = [item.strftime('%d.%m.%Y %H:%M:%S') for item in pass_times]
        bot.send_message(chat_id=message.chat.id,
                         text='\n'.join(pass_times),
                         reply_markup=keyboard())
    return response


HANDLERS = defaultdict(str, **{
    'Position': get_iss_position,
    'Crew': get_iss_crew,
    'Location': get_iss_pass_times,
})


@bot.message_handler(content_types=['text', 'location'])
def text_messages(message: Message):
    """
    Buttons handler
    """
    try:
        if message.content_type == 'text':
            handler = HANDLERS[message.text]
        elif message.content_type == 'location':
            handler = HANDLERS['Location']
        else:
            handler = None
        if not handler:
            bot.send_message(chat_id=message.chat.id, text='Push one of buttons',
                             reply_markup=keyboard())
        response = handler(message)
        if response.status_code == 200:
            logging.info('Position request from user {%s} OK', message.from_user)
        else:
            bot.send_message(chat_id=message.chat.id,
                             text='Sorry, I lost connection. Try again later please',
                             reply_markup=keyboard())
            logging.error('Position request from user % FAILED due to response code %d from %s. '
                          'Response data: %s', message.from_user, response.status_code,
                          URL_ISS_LOCATION,
                          response.json())

    except Exception as exception:
        logging.error('Position request from user %s FAILED with exception %s',
                      message.from_user, exception)
        bot.send_message(chat_id=message.chat.id,
                         text='Sorry, I don\'t feel good now. Try again later please',
                         reply_markup=keyboard())


if __name__ == '__main__':
    while True:
        try:
            bot.polling(timeout=60, none_stop=True)
        except requests.exceptions.ConnectionError as ex:
            logging.exception('Exception: %s', ex)
            time.sleep(5)
