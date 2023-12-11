from random import randint

import telebot
from telebot import types

import messages as m

from config import TOKEN, BARISTAS

bot = telebot.TeleBot(TOKEN)
choices = []
places = []


def choose_coffee(message):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for idx, coffee_type in enumerate(m.COFFEE_BUTTONS):
        if coffee_type in choices:
            coffee_type = 'Ещё {}'.format(coffee_type.lower())
        buttons.append(types.InlineKeyboardButton(text=coffee_type, callback_data='coffee_button_pressed:{}'.format(idx)))
    keyboard.add(*buttons)
    question = m.COFFEE_QUESTION_MORE if choices else m.COFFEE_QUESTION
    bot.send_message(message.chat.id, question, reply_markup=keyboard)


def choose_place(message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = []
    for idx, coffee_type in enumerate(m.PLACES_BUTTONS):
        buttons.append(types.InlineKeyboardButton(text=coffee_type, callback_data='place_button_pressed:{}'.format(idx)))
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, 'А вы где?', reply_markup=keyboard)


def get_order(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    place_message = 'Сменить место' if places else 'Выбрать место'
    keyboard.add(
        types.InlineKeyboardButton(text=m.THATSALL, callback_data='coffee_time'),
        types.InlineKeyboardButton(text=m.CLEAR, callback_data='clear_order'),
        types.InlineKeyboardButton(text=place_message, callback_data='choose_place'),
    )
    bot.send_message(message.chat.id, m.OR, reply_markup=keyboard)


def order_format(items):
    order_items = set(items)
    place = '➡️ {}'.format(places[0]) if places else '👀 Мы не знаем, где вы('

    return '\n'.join(
        sorted([m.ORDER_FORMAT.format(item.capitalize(), items.count(item))
                for item in order_items])) + '\n{}'.format(place)


@bot.message_handler(commands=['start'])
def start_message(message):
    client = message.chat.first_name
    bot.send_message(message.chat.id, m.START.format(client))
    choose_coffee(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if 'coffee_button_pressed' in call.data:
        choice = m.COFFEE_BUTTONS[int(call.data.split(':')[-1])]
        choices.append(choice)
        bot.send_message(call.message.chat.id, order_format(choices))
        choose_coffee(call.message)
        get_order(call.message)
    elif 'place_button_pressed' in call.data:
        choice = m.PLACES_BUTTONS[int(call.data.split(':')[-1])]
        if places:
            places[0] = choice
        else:
            places.append(choice)
        bot.send_message(call.message.chat.id, order_format(choices))
        choose_coffee(call.message)
        get_order(call.message)
    elif call.data == 'clear_order':
        choices.clear()
        bot.send_message(call.message.chat.id, m.OK)
        choose_coffee(call.message)
    elif call.data == 'choose_place':
        choose_place(call.message)
    elif call.data == 'coffee_time':
        if choices:
            if places:
                order_no = randint(1000, 9999)
                bot.send_message(call.message.chat.id, m.COOKING.format(order_no))
                for barista in BARISTAS:
                    client = '{} {} @{}'.format(
                        call.message.chat.first_name,
                        call.message.chat.last_name,
                        call.message.chat.username
                    )
                    order_no = 'Заказ № {}'.format(order_no)
                    order = order_no, client, order_format(choices)
                    bot.send_message(barista, '\n'.join(order))
                choices.clear()
                bot.send_message(call.message.chat.id, m.RETRY)
            else:
                choose_place(call.message)
        else:
            bot.send_message(call.message.chat.id, m.EMPTY_ORDER)
            choose_coffee(call.message)


@bot.message_handler(commands=["id"])
def chat_id(message):
    my_chat_id = int(message.chat.id)
    bot.send_message(message.chat.id, my_chat_id)


bot.infinity_polling()
