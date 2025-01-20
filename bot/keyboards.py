from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def create_dynamic_menu() -> ReplyKeyboardMarkup:
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Задания")],
            [KeyboardButton(text="Начать чат с помощником")],
        ],
        resize_keyboard=True
    )
