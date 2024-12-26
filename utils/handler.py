from aiogram import F
from aiogram.filters import Filter
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime

from os import path
from config import get_env, get_config
import asyncio

import utils.kb as kb
from states import UserState
from database.model import DB


# Отправка фото
@dp.message(F.photo)
async def time_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    group = msg.media_group_id
    await msg.answer(str(group))


# Установка времени
@dp.message(UserState.time)
async def time_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    try:
        time = datetime.strptime(msg.text, "%H:%M")
    except ValueError:
        await sender.message(user_id, "wrong_time")
        return


# Установка телефона
@dp.message(UserState.phone, F.contact)
async def phone_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    phone = msg.contact.phone_number


# Проверка на отсутствие состояний
class NoStates(Filter):
    async def __call__(self, msg: Message, state: FSMContext):
        stat = await state.get_state()
        return stat is None


# Сообщение без состояний
@dp.message(NoStates())
async def no_states_handler(msg: Message, state: FSMContext):
    pass


# Установка базы данных
@dp.message(F.document)
async def set_databse(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    role = DB.get('select role from users where telegram_id = ?', [user_id], True)
    if not role:
        return
    if role[0] != "admin":
        return
    
    doc = msg.document
    if doc.file_name.split(".")[-1] != "sqlite3":
        return
    
    file = await bot.get_file(doc.file_id)
    await bot.download_file(file.file_path, path.join("database", "db.sqlite3"))
