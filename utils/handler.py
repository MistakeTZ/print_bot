from aiogram import F
from aiogram.filters import Filter
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime
import math

from os import path, mkdir, walk
from .photo_editor import combine_images_to_pdf

import utils.kb as kb
from states import UserState
from database.model import DB


# Отправка фото
@dp.message(F.photo)
async def time_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    group = msg.media_group_id
    
    if not group:
        group = int(str(user_id) + str(msg.message_id))

    folder_path = path.join("temp", str(group))
    if not path.exists(folder_path):
        mkdir(folder_path)
        DB.commit("insert into prints (telegram_id, media_group_id, registered) \
                  values (?, ?, ?)", [user_id, group, datetime.now()])
        first = True
        database_id = DB.get("select id from prints where media_group_id = ?", [group], True)[0]
    else:
        first = False

    file_path = path.join("temp", str(group), str(msg.message_id) + ".jpg")
    await bot.download(msg.photo[-1].file_id, file_path)

    if first:
        await sender.message(user_id, "photo_sended", kb.buttons(True, "gen", f"generate_{database_id}", "print", f"print_{database_id}"))


# Изменение
@dp.message(UserState.edit, F.text)
async def time_check(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    try:
        number = int(msg.text)
    except:
        return

    data = await state.get_data()
    DB.commit("update prints set {} = ? where id = ?".format(data["edit"]), [number, data["id"]])

    database = DB.get("select media_group_id, count, fields, color, two_side, quality from prints where id = ?", [data["id"]], True)
    values = list(database)
    directory = path.join("temp", str(values[0]))
    files = next(walk(directory), (None, None, []))[2]

    _, files = combine_images_to_pdf(directory, files, "photo.pdf",
            grid_size=(int(math.sqrt(values[1])), int(math.sqrt(values[1]))),
            grayscale=values[3], border=values[2])

    if values[4] == 'short':
        duplex = "по короткому краю"
    elif values[4] == 'off':
        duplex = "отключена"
    elif values[4] == 'long':
        duplex = "по длинному краю"

    if values[4] == 'low':
        quality = "низкое"
    elif values[4] == 'medium':
        quality = "среднее"
    elif values[4] == 'high':
        quality = "высокое"

    text = sender.text("paint_settings")

    reply = kb.edit_buttons(data["id"], 0, len(files),  values[1], ["отключено", "включено"][values[3]], values[2], duplex, quality)

    file = FSInputFile(path=files[0], filename="photo.jpg")
    await bot.send_photo(user_id, file, caption=text, reply_markup=reply)


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
