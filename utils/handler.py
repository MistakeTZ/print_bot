from aiogram import F
from aiogram.filters import Filter
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from loader import dp, bot, sender
from datetime import datetime
import math
from pdf2image import convert_from_path
import pypandoc

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

    data = await state.get_data()
    if data["edit"] == "count":
        if not "x" in data:
            try:
                number = int(msg.text)
            except:
                return
            data["x"] = number
            await state.set_data(data)
            await sender.message(user_id, "edit_count_y")
            return

    database = DB.get("select media_group_id, count_x, fields, color, \
                      two_side, quality, count_y from prints where id = ?", [data["id"]], True)
    values = list(database)
    directory = path.join("temp", str(values[0]))
    files = next(walk(directory), (None, None, []))[2]

    if data["edit"] != "size":
        try:
            number = int(msg.text)
        except:
            return
    if data["edit"] == "count":
        count_y = number
        count_x = data["x"]
    else:
        count_x, count_y = values[1], values[6]
    grid = (count_x, count_y)

    if data["edit"] != "size":
        if data["edit"] == "fields":
            fields = number
        else:
            fields = values[2]

        returnable = combine_images_to_pdf(directory, files, "photo.pdf",
                grid_size=grid,
                grayscale=values[3], border=fields)

        sizes = returnable["sizes"]

        if data["edit"] == "fields":
            DB.commit("update prints set fields = ?, width = ?, height = ? where id = ?",
                      [number, *sizes, data["id"]])
        else:
            DB.commit("update prints set count_x = ?, count_y = ?, width = ?, height = ? where id = ?",
                      [count_x, count_y, *sizes, data["id"]])
    else:
        try:
            splitter = "x" if "x" in msg.text else "х"
            sizes = [float(num) * 10 for num in msg.text.split(splitter)]
        except:
            return

        returnable = combine_images_to_pdf(directory, files, "photo.pdf",
                grid_size=grid,
                grayscale=values[3], border=values[2], size=sizes)
        sizes = returnable["sizes"]
        fields = min(returnable["borders"])

        DB.commit("update prints set fields = ?, width = ?, height = ? where id = ?".format(
            data["edit"]), [fields, *sizes, data["id"]])
    files = returnable["pathes"]

    if values[4] == 'short':
        duplex = "по короткому краю"
    elif values[4] == 'none':
        duplex = "отключена"
    elif values[4] == 'long':
        duplex = "по длинному краю"

    if values[5] == 'draft':
        quality = "низкое"
    elif values[5] == 'medium':
        quality = "среднее"
    elif values[5] == 'high':
        quality = "высокое"

    text = sender.text("paint_settings")

    reply = kb.edit_buttons(data["id"], 0, len(files), grid, sizes, ["отключено", "включено"][values[3]], fields, duplex, quality)

    file = FSInputFile(path=files[0], filename="photo.jpg")
    await bot.send_photo(user_id, file, caption=text, reply_markup=reply)


# Установка базы данных
@dp.message(F.document)
async def set_databse(msg: Message, state: FSMContext):
    user_id = msg.from_user.id

    doc = msg.document
    extension = doc.file_name.split(".")[-1]
    if extension == "sqlite3":
        role = DB.get('select role from users where telegram_id = ?', [user_id], True)
        if not role:
            return
        if role[0] != "admin":
            return
    
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, path.join("database", "db.sqlite3"))

    elif extension == "pdf" or extension == "docx":
        group = int(str(user_id) + str(msg.message_id))

        folder_path = path.join("temp", str(group))
        mkdir(folder_path)
        DB.commit("insert into prints (telegram_id, media_group_id, registered) \
                values (?, ?, ?)", [user_id, group, datetime.now()])
        database_id = DB.get("select id from prints where media_group_id = ?", [group], True)[0]

        if extension == "docx":
            docx_path = path.join(folder_path, str(msg.message_id) + ".docx")
            await bot.download(msg.document.file_id, docx_path)
            file_path = path.join(folder_path, str(msg.message_id) + ".pdf")
            pypandoc.convert_file(docx_path, 'pdf', outputfile=file_path)
        else:
            file_path = path.join(folder_path, str(msg.message_id) + ".pdf")
            await bot.download(msg.document.file_id, file_path)

        pages = convert_from_path(file_path, 500)
        for count, page in enumerate(pages):
            page.save(path.join(folder_path, f'out{count}.jpg'), 'JPEG')

        await sender.message(user_id, "doc_sended", kb.buttons(True, "gen", f"generate_{database_id}", "print", f"print_{database_id}"))
