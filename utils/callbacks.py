from aiogram import F
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import FSInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
from loader import dp, bot, sender
import asyncio
from os import path, walk
import math

from config import get_env, get_config

import utils.kb as kb
from states import UserState
from database.model import DB
from .printing import execute_print, create_print_job, upload_file
from .photo_editor import combine_images_to_pdf


# Возвращение в меню
@dp.callback_query(F.data == "back")
async def menu_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    await sender.edit_message(clbck.message, "menu")
    await state.set_state(UserState.default)


# Отправление задания на печать
@dp.callback_query(F.data.startswith("generate_"))
async def start_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    print_id = int(clbck.data.split("_")[-1])
    media_group = DB.get("select media_group_id from prints where id = ?", [print_id], True)

    if not media_group:
        await sender.message(user_id, "failed")
        return

    directory = path.join("temp", str(media_group[0]))
    files = next(walk(directory), (None, None, []))[2]
    if not files:
        await sender.message(user_id, "failed")
        return

    await sender.message(user_id, "creating_doc")
    _, photo_pathes = combine_images_to_pdf(directory, files, "photo.pdf")

    file = FSInputFile(path=photo_pathes[0], filename="photo.jpg")
    await bot.send_photo(user_id, file,
                         caption=sender.text("paint_settings", 1, "отключено", 5, "переплет по длинному краю", "среднее"),
                         reply_markup=kb.edit_buttons(print_id, 0, len(photo_pathes)))


# Изменение настроек
@dp.callback_query(F.data.startswith("edit_"))
async def start_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    data = clbck.data.split("_")
    print_id = int(data[1])
    to_edit = data[2]
    page = int(data[3])

    database = DB.get("select media_group_id, count, fields, color, two_side, quality from prints where id = ?", [print_id], True)

    if not database:
        return
    values = list(database)

    photo_path = path.join("temp", str(values[0]))
    files = next(walk(path.join(photo_path, "pages")), (None, None, []))[2]
    photo_changed = False

    if to_edit == "page":
        file = path.join(path.join(photo_path, "pages"), files[page])
        photo_changed = True

    else:
        if to_edit == "count" or to_edit == "fields":
            await state.set_data({"id": print_id, "edit": to_edit})
            await state.set_state(UserState.edit)
            await sender.message(user_id, "edit_" + to_edit, kb.buttons(True, "back", f"edit_{print_id}_page_{page}"))
            return
        elif to_edit == "2side":
            if values[4] == 'long':
                values[4] = 'off'
            elif values[4] == 'short':
                values[4] = 'long'
            else:
                values[4] = 'short'
                
            DB.commit("update prints set two_side = ? where id = ?", [values[4], print_id])

        elif to_edit == "quality":
            if values[5] == 'low':
                values[5] = 'medium'
            elif values[5] == 'medium':
                values[5] = 'high'
            else:
                values[5] = 'low'
                
            DB.commit("update prints set two_side = ? where id = ?", [values[4], print_id])

        elif to_edit == "gray":
            files = next(walk(photo_path), (None, None, []))[2]
            values[3] = not values[3]
            DB.commit("update prints set color = ? where id = ?", [values[3], print_id])
            _, files = combine_images_to_pdf(photo_path, files, "photo.pdf",
                                                    grid_size=(int(math.sqrt(values[1])), int(math.sqrt(values[1]))),
                                                    grayscale=values[3], border=values[2])
            file = files[page]
            photo_changed = True

    if values[4] == 'short':
        duplex = "переплет по короткому краю"
    elif values[4] == 'off':
        duplex = "отключена"
    elif values[4] == 'long':
        duplex = "переплет по длинному краю"

    if values[5] == 'low':
        quality = "низкое"
    elif values[5] == 'medium':
        quality = "среднее"
    elif values[5] == 'high':
        quality = "высокое"

    text = sender.text("paint_settings",
        values[1], ["отключено", "включено"][values[3]], values[2], duplex, quality)
    reply = kb.edit_buttons(print_id, page, len(files))

    if photo_changed:
        file = FSInputFile(path=file, filename="photo.jpg")
        photo = InputMediaPhoto(media=file, caption=text)
        try:
            await clbck.message.edit_media(media=photo, reply_markup=reply)
        except Exception as e:
            print(e)
    else:
        try:
            await clbck.message.edit_caption(caption=text, reply_markup=reply)
        except Exception as e:
            print(e)


@dp.callback_query(F.data.startswith("print_"))
async def print_(clbck: CallbackQuery, state: FSMContext):
    user_id = clbck.from_user.id
    print_id = int(clbck.data.split("_")[-1])
    data = DB.get("select media_group_id, 2side, quality from prints where id = ?", [print_id], True)

    if not data:
        await sender.message(user_id, "failed")
        return

    file_path = path.join("temp", str(data[0]), "photo.pdf")
    if not path.exists(file_path):
        directory = path.join("temp", str(data[0]))
        files = next(walk(directory), (None, None, []))[2]
        if not files:
            await sender.message(user_id, "failed")
            return
    
        await sender.message(user_id, "creating_doc")
        file_path, _ = combine_images_to_pdf(directory, files, "photo.pdf")

    await sender.message(user_id, "creating_job")
    job_id = create_print_job(print_id, data[2], data[1]!='off')
    if not job_id:
        await sender.message(user_id, "failed")
        return
    
    await sender.message(user_id, "uploading_photo")

    upload_file(file_path)

    await sender.message(user_id, "executing_print")
    if not execute_print(job_id):
        await sender.message(user_id, "failed")
