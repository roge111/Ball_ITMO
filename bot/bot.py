# -*- coding: utf-8 -*-
from dotenv import load_dotenv
from pathlib import Path
from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.session.aiohttp import AiohttpSession
import os
import sys
import logging
import asyncio

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from managers.dataBase import DataBaseManager
from managers.ReadInfo import ReadInfo
from managers.ManagerGPT import ManagerYandexGPT

import shutil
from datetime import datetime

# Создаем папку для изображений
IMAGES_DIR = ROOT / 'images'
IMAGES_DIR.mkdir(exist_ok=True)


async def save_photo(photo: types.PhotoSize, user_id: int) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"user_{user_id}_{timestamp}.jpg"
    file_path = IMAGES_DIR / filename
    await bot.download(photo, destination=file_path)
    return str(file_path)


load_dotenv()

TG_TOKEN = os.getenv('TG_API_BOT')
admins_str = os.getenv('ADMINS_ID')
ADMINS_LIST = [int(id.strip()) for id in admins_str.split(',')]
MAIN_ADMIN_ID = int(os.getenv('MAIN_ADMIN_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

# === Прокси для Vependo ===
PROXY_URL = os.getenv('PROXY_URL', 'socks5://127.0.0.1:10801')

session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=TG_TOKEN, session=session)
dp = Dispatcher()
db = DataBaseManager()
readInfo = ReadInfo()
yaGPT = ManagerYandexGPT()


class WaitingMessage(StatesGroup):
    waiting_gender = State()
    finally_register = State()
    waiting_message_support = State()
    waiting_request_gpt = State()
    waiting_request_gpt_history = State()
    waiting_request_gpt_music = State()
    waiting_request_gpt_talk = State()
    waiting_id_question = State()
    waiting_ask = State()


# ---------- утилиты ----------
def check_tg_id(tg_id):
    result = db.query_database(f'select 1 from users where tg_id = {tg_id}')
    if len(result) and result[0][0]:
        return True
    return False


def check_question_id(id):
    result = db.query_database(f"select 1 from questions where id = {id};")
    if len(result) and result[0][0]:
        return True
    return False


def get_unanswered_questions():
    query = """
    SELECT id, user_id, question 
    FROM questions 
    WHERE is_ask = 'no' 
    ORDER BY id
    """
    try:
        return db.query_database(query)
    except Exception as e:
        print(f"Ошибка при получении вопросов: {e}")
        return []


def get_summary(tg_id: int, topic: str) -> str:
    """Возвращает сохранённый resume по (tg_id, topic) или пустую строку."""
    try:
        row = db.query_database(
            "SELECT cs.summary FROM chat_sessions cs "
            "JOIN users u ON u.user_id = cs.user_id "
            "WHERE u.tg_id = %s AND cs.topic = %s",
            (tg_id, topic)
        )
        if row and row[0][0]:
            return row[0][0]
    except Exception as e:
        print(f"[get_summary] {e}")
    return ""


# ---------- клавиатуры ----------
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🤖 Задать вопрос в бот по дресс-коду", callback_data="ask_gpt"),
        InlineKeyboardButton(text="🎵 Задать вопрос в бот по музыке бала", callback_data="ask_gpt_music"),
        InlineKeyboardButton(text="🏛️ Задать вопрос в бот по истории бала", callback_data="ask_gpt_history"),
        InlineKeyboardButton(text="🤖 Задать вопрос в бот по разговорному этикету", callback_data="ask_gpt_talk"),
        InlineKeyboardButton(text="🖊️ Написать в поддержку", callback_data="support"),
    )
    builder.adjust(1)
    return builder.as_markup()


def main_menu_admin():
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🤖 Задать вопрос в бот по дресс-коду", callback_data="ask_gpt"),
        InlineKeyboardButton(text="🎵 Задать вопрос в бот по музыке бала", callback_data="ask_gpt_music"),
        InlineKeyboardButton(text="🏛️ Задать вопрос в бот по истории бала", callback_data="ask_gpt_history"),
        InlineKeyboardButton(text="🤖 Задать вопрос в бот по разговорному этикету", callback_data="ask_gpt_talk"),
        InlineKeyboardButton(text="🖊️ Написать в поддержку", callback_data="support"),
        InlineKeyboardButton(text="Ответить на вопрос", callback_data="ask_question"),
        InlineKeyboardButton(text="Получить список вопросов", callback_data="list_questions")
    )
    builder.adjust(1)
    return builder.as_markup()


def error():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='🖊️ Написать в поддержку', callback_data="support"))
    return builder.as_markup()


def questions():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Ответить на вопрос", callback_data="ask_question"))
    return builder.as_markup()


# ---------- /start и регистрация ----------
@dp.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    if check_tg_id(tg_id):
        await message.answer("Привет👋 \nТы уже зарегистрирован!")
        if message.from_user.id in ADMINS_LIST:
            await message.answer("Главное меню", reply_markup=main_menu_admin())
        else:
            await message.answer("Главное меню", reply_markup=main_menu())
    else:
        await message.answer("Давай пройдем регистрацию. Введи свой пол: М или Ж")
        await state.set_state(WaitingMessage.waiting_gender)


@dp.message(WaitingMessage.waiting_gender)
async def add_gender(message: types.Message, state: FSMContext):
    message_user = message.text.upper()
    if message_user != 'М' and message_user != 'Ж':
        await message.answer("❌ Неправильный формат ввода. Попробуй еще раз. Введи свой пол: М или Ж.")
        await state.set_state(WaitingMessage.waiting_gender)
    else:
        try:
            db.query_database(
                f"insert into users (tg_id, gender) values ({message.from_user.id}, '{message_user}');",
                reg=True
            )
            await message.answer("Ты успешно зарегистрирован! 🎊")
            await state.clear()
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"При регистрации произошла ошибка: {e}")
            await message.answer(f"Ручки моего разработчика уже все чинят!")
        if message.from_user.id in ADMINS_LIST:
            await message.answer("Главное меню", reply_markup=main_menu_admin())
        else:
            await message.answer("Главное меню", reply_markup=main_menu())


# ---------- поддержка ----------
@dp.callback_query(F.data == 'support')
async def support(callback: types.CallbackQuery, state: FSMContext):
    if check_tg_id(callback.from_user.id):
        await bot.send_message(chat_id=callback.from_user.id, text='Напиши свою обращение или напиши `cancel`.')
        await state.set_state(WaitingMessage.waiting_message_support)
    else:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="Ты не зарегестрирован(-а). Давай пройдем регистрацию. Выбери свой пол: М или Ж"
        )
        await state.set_state(WaitingMessage.waiting_gender)


@dp.message(WaitingMessage.waiting_message_support)
async def process_support(message: types.Message, state: FSMContext):
    try:
        if message.text and message.text.lower() == 'cancel':
            await handle_cancel(message, state)
            return

        user_id = db.query_database(
            f"select user_id from users where tg_id = {message.from_user.id};"
        )[0][0]

        photo_path = None
        text_content = ""

        if message.photo:
            photo = message.photo[-1]
            photo_path = await save_photo(photo, message.from_user.id)

        if message.caption:
            text_content = message.caption
        elif message.text and not message.photo:
            text_content = message.text

        if photo_path and text_content:
            db_content = f"📷 Фото: {photo_path}\n📝 Текст: {text_content}"
        elif photo_path:
            db_content = f"📷 Фото: {photo_path}"
        elif text_content:
            db_content = text_content
        else:
            await message.answer("❌ Сообщение не содержит текста или фото.")
            return

        db.query_database(
            f"insert into questions (user_id, is_ask, question) values ({user_id}, 'no', '{db_content}');",
            reg=True
        )
        id_question = db.query_database(
            f"select id from questions where question = '{db_content}';"
        )[0][0]

        for id_admin in ADMINS_LIST:
            if photo_path and text_content:
                await bot.send_photo(
                    chat_id=id_admin,
                    photo=types.FSInputFile(photo_path),
                    caption=f"📝 Новое обращение:\n{text_content}\n\nОт пользователя: {message.from_user.full_name}\nID пользователя: {message.from_user.id}\nID вопроса: {id_question}",
                    reply_markup=questions()
                )
            elif photo_path:
                await bot.send_photo(
                    chat_id=id_admin,
                    photo=types.FSInputFile(photo_path),
                    caption=f"📷 Обращение с фото\n\nОт пользователя: {message.from_user.full_name}\nID пользователя: {message.from_user.id}\nID вопроса: {id_question}",
                    reply_markup=questions()
                )
            else:
                await bot.send_message(
                    chat_id=id_admin,
                    text=f"📝 Новое обращение:\n{text_content}\n\nОт пользователя: {message.from_user.full_name}\nID пользователя: {message.from_user.id}\nID вопроса: {id_question}",
                    reply_markup=questions()
                )

        await message.answer("✅ Обращение отправлено.")

    except Exception as e:
        await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"При отправке обращения произошла ошибка: {e}")
        await message.answer("Произошла ошибка. Ручки разработчика уже работают) Обратитесь позже.")

    await handle_menu_return(message, state)


async def handle_cancel(message: types.Message, state: FSMContext):
    await message.answer("❌ Обращение отменено.")
    await handle_menu_return(message, state)


async def handle_menu_return(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


# ---------- кнопки тем ----------
@dp.callback_query(F.data == 'ask_gpt')
async def ask_gpt(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Напиши вопрос по балу, который тебя интересует или отмени запрос словом `cancel`."
    )
    await state.set_state(WaitingMessage.waiting_request_gpt)


@dp.callback_query(F.data == 'ask_gpt_history')
async def ask_gpt_history(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Напиши вопрос по балу, который тебя интересует или отмени запрос словом `cancel`."
    )
    await state.set_state(WaitingMessage.waiting_request_gpt_history)


@dp.callback_query(F.data == 'ask_gpt_music')
async def ask_gpt_music(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Напиши вопрос по балу, который тебя интересует или отмени запрос словом `cancel`."
    )
    await state.set_state(WaitingMessage.waiting_request_gpt_music)


@dp.callback_query(F.data == 'ask_gpt_talk')
async def ask_gpt_talk(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Напиши вопрос по балу, который тебя интересует или отмени запрос словом `cancel`."
    )
    await state.set_state(WaitingMessage.waiting_request_gpt_talk)


# ---------- обработчики тем ----------
@dp.message(WaitingMessage.waiting_request_gpt)
async def process_gpt(message: types.Message, state: FSMContext):
    message_user = message.text
    if message_user != 'cancel':
        if check_tg_id(message.from_user.id):
            gender = db.query_database(f'select gender from users where tg_id = {message.from_user.id};')
            if len(gender):
                gender = gender[0][0]
                if gender == 'М':
                    system_message = readInfo.read_pdf_info('info/Дресс-код_для_кавалеров.pdf')
                else:
                    system_message = readInfo.read_pdf_info('info/Дресс-код_для_дам.pdf')

                summary = get_summary(message.from_user.id, 'dresscode')
                request_text = message_user
                if summary:
                    request_text = f"[Контекст прошлого диалога]\n{summary}\n\n[Текущий вопрос]\n{message_user}"

                yaGPT.set_context(message.from_user.id, 'dresscode')

                res = yaGPT.ask_yandex_gpt(
                    request=request_text,
                    system_message=f"На все вопросы отвечай по информации про бал: {system_message}\nЕсли не достаточно, то бери ответ из интернета с пометкой: взято из интернета"
                )
                result, err = res[0], res[1]
                if not len(result) or err:
                    await message.reply("❌Произошла ошибка. Ручки разработчика уже потеют)")
                    await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"На вопрос '{message_user}' пришел пустой ответ.")
                else:
                    response = yaGPT.parser_response_gpt(result)
                    await message.reply(response)
            else:
                await message.answer("❌ У вас отсутсвует информация о поле. Введите свой пол: М или Ж.")
                await state.set_data(WaitingMessage.waiting_gender)
        else:
            await message.answer("К сожалению, без регистрации в боте ты не можешь задать вопрос. Давай зарегестрируемся. Введи свой пол: М или Ж.")
            await state.set_state(WaitingMessage.waiting_gender)
    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


@dp.message(WaitingMessage.waiting_request_gpt_history)
async def process_gpt_history(message: types.Message, state: FSMContext):
    message_user = message.text
    if message_user != 'cancel':
        if check_tg_id(message.from_user.id):
            gender = db.query_database(f'select gender from users where tg_id = {message.from_user.id};')
            if len(gender):
                gender = gender[0][0]
                system_message = readInfo.read_pdf_info('info/МАБ_История_Балов_ШСЭ.pdf') + '\n'

                summary = get_summary(message.from_user.id, 'history')
                request_text = message_user
                if summary:
                    request_text = f"[Контекст прошлого диалога]\n{summary}\n\n[Текущий вопрос]\n{message_user}"

                yaGPT.set_context(message.from_user.id, 'history')

                res = yaGPT.ask_yandex_gpt(
                    request=request_text,
                    system_message=f"На все вопросы отвечай по информации про бал: {system_message}\nЕсли не достаточно, то бери ответ из интернета с пометкой: взято из интернета"
                )
                result, err = res[0], res[1]
                if not len(result) or err:
                    await message.reply("❌Произошла ошибка. Ручки разработчика уже потеют)")
                    await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"На вопрос '{message_user}' пришел пустой ответ.")
                else:
                    response = yaGPT.parser_response_gpt(result)
                    await message.reply(response)
            else:
                await message.answer("❌ У вас отсутсвует информация о поле. Введите свой пол: М или Ж.")
                await state.set_data(WaitingMessage.waiting_gender)
        else:
            await message.answer("К сожалению, без регистрации в боте ты не можешь задать вопрос. Давай зарегестрируемся. Введи свой пол: М или Ж.")
            await state.set_state(WaitingMessage.waiting_gender)
    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


@dp.message(WaitingMessage.waiting_request_gpt_music)
async def process_gpt_music(message: types.Message, state: FSMContext):
    message_user = message.text
    if message_user != 'cancel':
        if check_tg_id(message.from_user.id):
            gender = db.query_database(f'select gender from users where tg_id = {message.from_user.id};')
            if len(gender):
                gender = gender[0][0]
                system_message = readInfo.read_pdf_info('info/МАБ_Классическая_музыкальная_традиция_ШСЭ.pdf') + '\n'

                summary = get_summary(message.from_user.id, 'music')
                request_text = message_user
                if summary:
                    request_text = f"[Контекст прошлого диалога]\n{summary}\n\n[Текущий вопрос]\n{message_user}"

                yaGPT.set_context(message.from_user.id, 'music')

                res = yaGPT.ask_yandex_gpt(
                    request=request_text,
                    system_message=f"На все вопросы отвечай по информации про бал: {system_message}\nЕсли не достаточно, то бери ответ из интернета с пометкой: взято из интернета"
                )
                result, err = res[0], res[1]
                if not len(result) or err:
                    await message.reply("❌Произошла ошибка. Ручки разработчика уже потеют)")
                    await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"На вопрос '{message_user}' пришел пустой ответ.")
                else:
                    response = yaGPT.parser_response_gpt(result)
                    await message.reply(response)
            else:
                await message.answer("❌ У вас отсутсвует информация о поле. Введите свой пол: М или Ж.")
                await state.set_data(WaitingMessage.waiting_gender)
        else:
            await message.answer("К сожалению, без регистрации в боте ты не можешь задать вопрос. Давай зарегестрируемся. Введи свой пол: М или Ж.")
            await state.set_state(WaitingMessage.waiting_gender)
    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


@dp.message(WaitingMessage.waiting_request_gpt_talk)
async def process_gpt_talk(message: types.Message, state: FSMContext):
    message_user = message.text
    if message_user != 'cancel':
        if check_tg_id(message.from_user.id):
            gender = db.query_database(f'select gender from users where tg_id = {message.from_user.id};')
            if len(gender):
                gender = gender[0][0]
                system_message = readInfo.read_pdf_info('info/МАБ_Речевой_общ_цифровой_ШСЭ.pdf') + '\n'

                summary = get_summary(message.from_user.id, 'talk')
                request_text = message_user
                if summary:
                    request_text = f"[Контекст прошлого диалога]\n{summary}\n\n[Текущий вопрос]\n{message_user}"

                yaGPT.set_context(message.from_user.id, 'talk')

                res = yaGPT.ask_yandex_gpt(
                    request=request_text,
                    system_message=f"На все вопросы отвечай по информации про бал: {system_message}\nЕсли не достаточно, то бери ответ из интернета с пометкой: взято из интернета"
                )
                result, err = res[0], res[1]
                if not len(result) or err:
                    await message.reply("❌Произошла ошибка. Ручки разработчика уже потеют)")
                    await bot.send_message(chat_id=MAIN_ADMIN_ID, text=f"На вопрос '{message_user}' пришел пустой ответ.")
                else:
                    response = yaGPT.parser_response_gpt(result)
                    await message.reply(response)
            else:
                await message.answer("❌ У вас отсутсвует информация о поле. Введите свой пол: М или Ж.")
                await state.set_data(WaitingMessage.waiting_gender)
        else:
            await message.answer("К сожалению, без регистрации в боте ты не можешь задать вопрос. Давай зарегестрируемся. Введи свой пол: М или Ж.")
            await state.set_state(WaitingMessage.waiting_gender)
    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


# ---------- сброс контекста ----------
@dp.message(Command('reset'))
async def reset_context(message: types.Message):
    if not check_tg_id(message.from_user.id):
        await message.answer("Ты ещё не зарегистрирован.")
        return
    try:
        db.query_database(
            "UPDATE chat_sessions SET summary='', updated_at=NOW() "
            "WHERE user_id = (SELECT user_id FROM users WHERE tg_id=%s)",
            (message.from_user.id,), reg=True
        )
        await message.answer("🧹 Контекст всех диалогов очищен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ---------- админ-часть: ответы на вопросы ----------
@dp.callback_query(F.data == 'ask_question')
async def ask_question(callback: types.CallbackQuery, state: FSMContext):
    await bot.send_message(chat_id=callback.from_user.id, text="Напишите id вопроса.")
    await state.set_state(WaitingMessage.waiting_id_question)


@dp.message(Command('getid'))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = message.chat.title or "Без названия"

    print(chat_id)
    await message.answer(
        f"🆔 ID: `{chat_id}`\n📝 Тип: {chat_type}\n👥 Название: {chat_title}",
        parse_mode="Markdown"
    )


@dp.message(WaitingMessage.waiting_id_question)
async def process_ask_question(message: types.Message, state: FSMContext):
    id_question = message.text
    current_user_id = message.from_user.id

    if check_question_id(id_question):
        res = db.query_database(
            f"select q.is_ask, users.tg_id, q.operator from questions as q join users on q.user_id = users.user_id where q.id = {id_question};"
        )
        print(res)
        if len(res):
            is_ask, tg_id, operator = res[0][0], res[0][1], res[0][2]

            operator_is_empty = operator is None
            operator_is_current_user = operator == current_user_id

            if operator_is_empty or operator_is_current_user:
                if operator_is_empty:
                    db.query_database(
                        f"update questions set operator = {current_user_id} where id = {id_question};",
                        reg=True
                    )

                if is_ask == 'no':
                    for id_admin in ADMINS_LIST:
                        if id_admin != current_user_id:
                            await bot.send_message(chat_id=id_admin, text=f"По вопросу с id = {id_question} взялся оператор.")
                    await bot.send_message(chat_id=tg_id, text=f"По вопросу с id = {id_question} взялся оператор.")
                    question_result = db.query_database(f"select question from questions where id = {id_question};")
                    question_content = question_result[0][0] if question_result else "Вопрос не найден"

                    if "📷 Фото:" in question_content:
                        photo_path = question_content.split("📷 Фото: ")[1].split("\n")[0]
                        text_part = question_content.split("📝 Текст: ")[1] if "📝 Текст:" in question_content else "Фото обращение"

                        try:
                            await bot.send_photo(
                                chat_id=message.from_user.id,
                                photo=types.FSInputFile(photo_path),
                                caption=f"📷 Вопрос с фото:\n{text_part}\n\nНапишите ответ на этот вопрос или введите 'отмена'"
                            )
                        except Exception as e:
                            await message.answer(f"❌ Не удалось загрузить фото: {e}")
                            await message.answer(f"Напишите ответ на вопрос: '{text_part}', или введите 'отмена' и ответите позже.")

                        await state.update_data(question=question_content)
                        await state.update_data(id_question=id_question)
                        await state.update_data(user_tg=tg_id)
                        await state.update_data(is_photo_question=True)
                        await state.update_data(photo_path=photo_path)
                        await state.update_data(original_text=text_part)

                    else:
                        await message.answer(f"Напишите ответ на вопрос: '{question_content}', или введите 'отмена' и ответите позже.")

                        await state.update_data(question=question_content)
                        await state.update_data(id_question=id_question)
                        await state.update_data(user_tg=tg_id)
                        await state.update_data(is_photo_question=False)

                    await state.set_state(WaitingMessage.waiting_ask)
                else:
                    await message.answer("На вопрос уже ответили.")
                    await state.clear()
            else:
                await message.answer("Этот вопрос уже взят другим оператором.")
                await state.clear()
        else:
            await message.answer('Нет данных по вопросу. Видимо уже ответили')
    else:
        await message.answer("Такого вопроса нет.")
        await state.clear()


@dp.message(WaitingMessage.waiting_ask)
async def process_ask_question_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    question_content = data['question']
    id_question = data['id_question']
    user_tg_id = data['user_tg']
    is_photo_question = data.get('is_photo_question', False)
    photo_path = data.get('photo_path')
    original_text = data.get('original_text', question_content)

    if message.text != 'отмена':
        if is_photo_question:
            if message.photo:
                photo = message.photo[-1]
                operator_photo_path = await save_photo(photo, message.from_user.id)

                await bot.send_photo(
                    chat_id=user_tg_id,
                    photo=types.FSInputFile(photo_path),
                    caption=f"📷 Ваше обращение: {original_text}"
                )
                await bot.send_photo(
                    chat_id=user_tg_id,
                    photo=types.FSInputFile(operator_photo_path),
                    caption=f"📷 Ответ оператора"
                )

                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=types.FSInputFile(operator_photo_path),
                    caption=f"📝 Ответ на фото-обращение\n\n💬 Текст обращения: {original_text}"
                )
            else:
                await bot.send_photo(
                    chat_id=user_tg_id,
                    photo=types.FSInputFile(photo_path),
                    caption=f"📷 Ваше обращение: {original_text}\n\n💬 Ответ оператора: {message.text}"
                )

                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=types.FSInputFile(photo_path),
                    caption=f"📝 Ответ на фото-обращение\n\n💬 Текст обращения: {original_text}\n\n💬 Ответ оператора: {message.text}"
                )
        else:
            await bot.send_message(
                chat_id=user_tg_id,
                text=f"💬 Ваш вопрос: '{question_content}'\n\n💬 Ответ оператора: {message.text}"
            )

            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"📝 Ответ на вопрос\n\n💬 Вопрос: {question_content}\n\n💬 Ответ: {message.text}"
            )

        db.query_database(f"update questions set is_ask = 'yes' where id = {id_question};", reg=True)
        await message.answer("✅ Ответ отправлен.")

    if message.from_user.id in ADMINS_LIST:
        await message.answer("Главное меню", reply_markup=main_menu_admin())
    else:
        await message.answer("Главное меню", reply_markup=main_menu())
    await state.clear()


@dp.callback_query(F.data == 'list_questions')
async def show_unanswered_questions(callback: types.CallbackQuery):
    questions_list = get_unanswered_questions()

    if not questions_list:
        await callback.message.answer("📭 Нет неотвеченных вопросов")
        return

    response = "📋 Список неотвеченных вопросов:\n\n"

    for i, (q_id, user_id, question_text) in enumerate(questions_list, 1):
        short_question = question_text[:100] + "..." if len(question_text) > 100 else question_text
        response += f"{i}. ID: {q_id}\n"
        response += f"   👤 User: {user_id}\n"
        response += f"   ❓ Вопрос: {short_question}\n"

    await callback.message.answer(response)
    await callback.message.answer("Главное меню", reply_markup=main_menu_admin())


# ---------- запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())