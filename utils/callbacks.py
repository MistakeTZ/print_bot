from aiogram import F
from aiogram.types.callback_query import CallbackQuery
from aiogram.types import FSInputFile
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
from .print import execute_print, create_print_job, upload_file
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
    _, photo_pathes = combine_images_to_pdf(directory, files, "photo.pdf", grid_size=(2, 2))

    file = FSInputFile(path=photo_pathes[0], filename="photo.jpg")
    await bot.send_photo(user_id, file,
                         caption=sender.text("paint_settings", 1, "отключено", 5, "переплет по длинному краю"),
                         reply_markup=kb.edit_buttons(print_id, 0, len(photo_pathes)))


# Изменение настроек
@dp.callback_query(F.data.startswith("edit_"))
async def start_handler(clbck: CallbackQuery, state: FSMContext) -> None:
    user_id = clbck.from_user.id
    data = clbck.data.split("_")
    print_id = int(data[1])
    to_edit = data[2]
    page = int(data[3])

    database = DB.get("select media_group_id, count, fields, color, two_side from prints where id = ?", [print_id], True)

    if not database:
        return
    values = list(database)

    photo_path = path.join("temp", str(values[0]))
    files = next(walk(path.join(photo_path, "pages")), (None, None, []))[2]

    if to_edit == "page":
        file = path.join(path.join(photo_path, "pages"), files[page])

    else:
        if to_edit == "count" or to_edit == "fields":
            await state.set_data({"id": print_id, "edit": to_edit})
            await state.set_state(UserState.edit)
            await sender.message(user_id, "edit_" + to_edit, kb.buttons(True, "back", f"edit_{print_id}_page_{page}"))
            return
        elif to_edit == "2side":
            if values[4] == 'long':
                text = "отключена"
                values[4] = 'off'
            elif values[4] == 'short':
                text = "переплет по длинному краю"
                values[4] = 'long'
            else:
                values[4] = 'short'
                
            DB.commit("update prints set two_side = ? where id = ?", [values[4], print_id])
        elif to_edit == "gray":
            files = next(walk(photo_path), (None, None, []))[2]
            values[3] = not values[3]
            DB.commit("update prints set color = ? where id = ?", [values[3], print_id])
            _, photo_pathes = combine_images_to_pdf(photo_path, files, "photo.pdf",
                                                    grid_size=(int(math.sqrt(values[1])), int(math.sqrt(values[1]))),
                                                    grayscale=values[3], border=values[2])

    if values[4] == 'short':
        text = "переплет по короткому краю"
    elif values[4] == 'off':
        text = "отключена"
    elif values[4] == 'long':
        text = "переплет по длинному краю"

    # file = FSInputFile(path=photo_pathes[0], filename="photo.jpg")
    await clbck.message.edit_caption(caption=sender.text("paint_settings",
            values[1], ["отключено", "включено"][values[3]], values[2], text),
            reply_markup=kb.edit_buttons(print_id, page, len(files)))



@dp.callback_query(F.data.startswith("print_"))
async def print(clbck: CallbackQuery, state: FSMContext):
    user_id = clbck.from_user.id
    print_id = int(clbck.data.split("_")[-1])
    media_group = DB.get("select media_group_id from prints where id = ?", [print_id], True)

    if not media_group:
        await sender.message(user_id, "failed")
        return

    file_path = path.join("temp", str(media_group[0]), "photo.pdf")
    if not path.exists(file_path):
        directory = path.join("temp", str(media_group[0]))
        files = next(walk(directory), (None, None, []))[2]
        if not files:
            await sender.message(user_id, "failed")
            return
    
        await sender.message(user_id, "creating_doc")
        file_path, _ = combine_images_to_pdf(directory, files, "photo.pdf")

    await sender.message(user_id, "creating_job")
    job_id = create_print_job(print_id)
    if not job_id:
        await sender.message(user_id, "failed")
        return
    
    await sender.message(user_id, "uploading_photo")

    upload_file(file_path)

    await sender.message(user_id, "executing_print")
    if not execute_print(job_id):
        await sender.message(user_id, "failed")
