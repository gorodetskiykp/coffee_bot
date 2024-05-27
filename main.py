import logging
import smtplib
import time

from collections import defaultdict
from random import randint

import telebot
from telebot import types

import messages as m

from config import ADMIN_TELEGRAM_ID, BARISTAS, TOKEN

bot = telebot.TeleBot(TOKEN)
choices = defaultdict(list)  # для каждого пользователя список выбранных напитков
places_choice = defaultdict(list)  # для каждого пользователя список доступных мест
places = defaultdict(list)  # для каждого пользователя текущее место заказа
messages = defaultdict(list)   # для каждого пользователя список сообщений

logger = telebot.logger
logger.setLevel(logging.DEBUG)


def send_mail():
    HOST = 'smtp.gmail.com'
    SUBJECT = 'Hello'
    TO = ''
    FROM = ''
    text = 'HELLO'

    BODY = "\r\n".join((
        "From: %s" % FROM,
        "To: %s" % TO,
        "Subject: %s" % SUBJECT,
        "",
        text
    ))

    client = smtplib.SMTP(HOST, port=587)
    client.starttls()
    client.login('', '')
    client.sendmail(FROM, [TO], BODY)
    client.quit()


def choose_coffee(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, coffee_type in enumerate(m.COFFEE_BUTTONS):
        if coffee_type in choices[message.chat.id]:
            coffee_type = 'Ещё {}'.format(coffee_type.lower())
        buttons.append(
            types.InlineKeyboardButton(
                text=coffee_type,
                callback_data='coffee_button_pressed:{}'.format(idx)
            )
        )
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, m.COFFEE_QUESTION, reply_markup=keyboard)


def choose_place(message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = []
    places = places_choice[message.chat.id] if places_choice[message.chat.id] else m.PLACES_BUTTONS
    for idx, place in enumerate(places):
        buttons.append(
            types.InlineKeyboardButton(
                text=place,
                callback_data='place_button_pressed:{}'.format(idx)
            )
        )
    buttons.append(
        types.InlineKeyboardButton(
            text='Другое',
            callback_data='place_button_pressed:{}'.format('other')
        )
    )
    keyboard.add(*buttons)
    bot.send_message(message.chat.id, 'Куда принести заказ?', reply_markup=keyboard)


def choose_other_place(message):
    if places[message.chat.id]:
        places[message.chat.id][0] = message.text
    else:
        places[message.chat.id].append(message.text)
    if places_choice[message.chat.id]:
        places_choice[message.chat.id].append(message.text)
    else:
        places_choice[message.chat.id] = m.PLACES_BUTTONS + [message.text]
    bot.send_message(
        message.chat.id,
        order_format(choices[message.chat.id], message)
    )
    # get_order(message)
    coffee_time(message)

def get_order(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    place_message = ('Сменить место'
                     if places[message.chat.id] else 'Выбрать место')
    keyboard.add(
        types.InlineKeyboardButton(text=place_message,
                                   callback_data='choose_place'),
        types.InlineKeyboardButton(text=m.CLEAR, callback_data='clear_order'),
        types.InlineKeyboardButton(text=m.THATSALL,
                                   callback_data='coffee_time'),
    )
    bot.send_message(message.chat.id, m.OR, reply_markup=keyboard)


def order_format(items, message):
    order_items = set(items)
    place = ('➡️ {}'.format(places[message.chat.id][0])
             if places[message.chat.id] else '👀 Пока не выбрано место доставки...')

    return '\n'.join(
        sorted([m.ORDER_FORMAT.format(item.capitalize(), items.count(item))
                for item in order_items])) + '\n{}'.format(place)


def yes_or_no(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="Да", callback_data='yes_no_pressed:yes'),
        types.InlineKeyboardButton(text="Нет", callback_data='yes_no_pressed:no'),
    )
    bot.send_message(message.chat.id, m.COFFEE_QUESTION_MORE, reply_markup=keyboard)


def coffee_time(message):
    if choices[message.chat.id]:
        if places[message.chat.id]:
            order_no = randint(1000, 9999)
            order_no_full = 'Заказ № {}'.format(order_no)
            bot.send_message(message.chat.id, m.COOKING.format(order_no))
            for barista in BARISTAS:
                client = '{} {} @{}'.format(
                    message.chat.first_name,
                    message.chat.last_name,
                    message.chat.username
                )
                order = (
                    order_no_full,
                    client,
                    order_format(choices[message.chat.id], message)
                )
                try:
                    bot.send_message(barista, '\n'.join(order))
                    pass
                except Exception:
                    bot.send_message(ADMIN_TELEGRAM_ID, "Не могу отправить сообщение в чат {}".format(barista))
                # send_mail()
            choices[message.chat.id].clear()
            bot.send_message(message.chat.id, m.RETRY)
            places_choice[message.chat.id].clear()
            places[message.chat.id].clear()
            for msg_id in range(message.id, messages[message.chat.id][0] - 1, -1):
                try:
                    bot.delete_message(message.chat.id, msg_id)
                except:
                    pass

            time.sleep(1)

            for msg_id in range(message.id + 3, message.id - 1, -1):
                try:
                    bot.delete_message(message.chat.id, msg_id)
                except:
                    pass

        else:
            choose_place(message)
    else:
        bot.send_message(message.chat.id, m.EMPTY_ORDER)
        choose_coffee(message)

@bot.message_handler(commands=['start'])
def start_message(message):
    client = message.chat.first_name
    bot.send_message(message.chat.id, m.START.format(client))
    messages[message.chat.id].append(message.message_id)
    choose_coffee(message)


@bot.message_handler(commands=['vks'])
def start_message(message):
    with open('vks.pdf', 'rb') as file:
        bot.send_document(message.chat.id, file.read(), visible_file_name="ВКС.pdf")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if 'coffee_button_pressed' in call.data:
        choice = m.COFFEE_BUTTONS[int(call.data.split(':')[-1])]
        choices[call.message.chat.id].append(choice)
        bot.send_message(
            call.message.chat.id,
            order_format(choices[call.message.chat.id], call.message)
        )
        # choose_coffee(call.message)
        yes_or_no(call.message)
        # get_order(call.message)
    elif 'yes_no_pressed' in call.data:
        if call.data.split(':')[-1] == 'yes':
            choose_coffee(call.message)
        else:
            coffee_time(call.message)
    elif 'place_button_pressed' in call.data:
        place_index = call.data.split(':')[-1]
        if place_index == 'other':
            bot.send_message(call.message.chat.id, 'Куда принести?')
            bot.register_next_step_handler(call.message, choose_other_place)
        else:
            places_list = places_choice[call.message.chat.id] if places_choice[call.message.chat.id] else m.PLACES_BUTTONS
            choice = places_list[int(place_index)]
            if places[call.message.chat.id]:
                places[call.message.chat.id][0] = choice
            else:
                places[call.message.chat.id].append(choice)
            bot.send_message(
                call.message.chat.id,
                order_format(choices[call.message.chat.id], call.message)
            )
            # choose_coffee(call.message)
            # get_order(call.message)
            coffee_time(call.message)
    elif call.data == 'clear_order':
        choices[call.message.chat.id].clear()
        bot.send_message(call.message.chat.id, m.OK)
        choose_coffee(call.message)
    elif call.data == 'choose_place':
        choose_place(call.message)
    elif call.data == 'coffee_time':
        coffee_time(call.message)


@bot.message_handler(commands=["id"])
def chat_id(message):
    my_chat_id = int(message.chat.id)
    bot.send_message(message.chat.id, my_chat_id)


bot.infinity_polling()
