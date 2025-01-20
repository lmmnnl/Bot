from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

router = Router()

async def create_task_status_buttons(task_id: int):
    buttons = [
        InlineKeyboardButton(text="Not Started", callback_data=f"status_{task_id}_not_started"),
        InlineKeyboardButton(text="Processing", callback_data=f"status_{task_id}_processing"),
        InlineKeyboardButton(text="Finished", callback_data=f"status_{task_id}_finished"),
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return keyboard

