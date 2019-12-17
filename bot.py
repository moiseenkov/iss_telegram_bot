"""
Bot provides some information about current state of International Space Station
"""
import logging
import time
from collections import defaultdict

import requests
import telebot
from environs import Env
from telebot import apihelper, types
from telebot.types import Message


URL_ISS_LOCATION = 'http://api.open-notify.org/iss-now.json'
URL_ISS_CREW = 'http://api.open-notify.org/astros.json'

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
    _keyboard = types.InlineKeyboardMarkup(row_width=1)
    button_position = types.InlineKeyboardButton(text='Position', callback_data='position', )
    button_crew = types.InlineKeyboardButton(text='Crew', callback_data='crew', )
    _keyboard.add(button_position)
    _keyboard.add(button_crew)
    return _keyboard


@bot.message_handler(content_types=['text'])
def any_message(message: Message):
    """
    Processing any user message and provide keyboard
    Args:
        message: telebot.types.Message instance
    """
    bot.send_message(chat_id=message.chat.id,
                     text='Hello! How can I help you?',
                     reply_markup=keyboard())


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
                         text=f'Current ISS position is: '
                              f'{_position["latitude"]}°, {_position["longitude"]}°')
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
        bot.send_message(chat_id=message.chat.id, text=text, parse_mode='Markdown')
    return response


HANDLERS = defaultdict(None, **{
    'position': get_iss_position,
    'crew': get_iss_crew,
})


@bot.callback_query_handler(func=lambda call: True)
def buttons_handler(call):
    """
    Buttons handler
    """
    try:
        handler = HANDLERS[call.data]
        if handler is None:
            return

        response = handler(call.message)
        if response.status_code == 200:
            logging.info('Position request from user {%s} OK', call.message.from_user)
        else:
            bot.send_message(chat_id=call.message.chat.id,
                             text='Sorry, I lost connection. Try again later please')
            logging.error('Position request from user % FAILED due to response code %d from %s. '
                          'Response data: %s', call.message.from_user, response.status_code,
                          URL_ISS_LOCATION,
                          response.json())
    except Exception as exception:
        logging.error('Position request from user %s FAILED with exception %s',
                      call.message.from_user, exception)
        bot.send_message(chat_id=call.message.chat.id,
                         text='Sorry, I don\'t feel good now. Try again later please')
    finally:
        bot.send_message(chat_id=call.message.chat.id, text='Menu:', reply_markup=keyboard())


if __name__ == '__main__':
    while True:
        try:
            bot.polling(timeout=123, none_stop=True)
        except requests.exceptions.ConnectionError as ex:
            logging.exception('Exception: %s', ex)
            time.sleep(5)
