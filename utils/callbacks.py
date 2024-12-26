from aiogram import F
from aiogram.types.callback_query import CallbackQuery
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
import asyncio
from os import path

from config import get_env, get_config

import utils.kb as kb
from states import UserState
from database.model import DB


# Возвращение в меню
@dp.callback_query(F.data == "back")
async def menu_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    await sender.edit_message(clbck.message, "menu")
    await state.set_state(UserState.default)


# Начинается с
@dp.callback_query(F.data.startswith("start_"))
async def start_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    answer = clbck.data.split("_")[-1]


async def check_sub(user_id):
    channel = int(get_env("channel"))
    try:
        status = await bot.get_chat_member(channel, user_id)
        return (status.status != ChatMemberStatus.KICKED) and (
            status.status != ChatMemberStatus.LEFT)
    except:
        return False
