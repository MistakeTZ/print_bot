from aiogram import F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
from os import path
from datetime import datetime

from config import get_env, get_config
import utils.kb as kb
from states import UserState
from database.model import DB
from .print import create_print_job, execute_print, upload_file


# Команда старта бота
@dp.message(CommandStart())
async def command_start_handler(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    if not DB.get("select id from users where telegram_id = ?", [user_id]):
        print("New user:", user_id)
        DB.commit("insert into users (telegram_id, name, username, registered) values (?, ?, ?, ?)", 
                  [user_id, msg.from_user.full_name, msg.from_user.username, datetime.now()])

    await sender.message(user_id, "start")
    await state.set_state(UserState.default)

    # job_id = create_print_job()
    # upload_file(path.join("temp", "SampleDoc.pdf"))
    # execute_print(job_id)


# Команда получения БД
@dp.message(Command("get"))
async def command_settings(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    role = DB.get('select role from users where telegram_id = ?', [user_id], True)
    if not role:
        return
    if role[0] != "admin":
        await sender.message(user_id, "not_allowed")
        return
    await sender.send_media(user_id, "file", "db.sqlite3", path="database", name="db")
