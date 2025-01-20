import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.handlers import router
from bot.commands import set_commands
from bot.database import init_db, add_user, add_task_to_db, update_task_status
from bot.config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    session = AiohttpSession()
    
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    dp.include_router(router)

    await set_commands(bot)
    await init_db()

    # # Список пользователей для добавления
    # users_to_add = [
    #     {"user_id": 12345, "username": "user1", "group_id": 232, "role": "student"},
    #     {"user_id": 11223, "username": "user2", "group_id": 232, "role": "student"},
    #     {"user_id": 11224, "username": "user4", "group_id": 234, "role": "student"},
    #     {"user_id": 11225, "username": "user5", "group_id": 234, "role": "student"},
    #     {"user_id": 67890, "username": "teacher1", "group_id": None, "role": "teacher"},
    # ]

    # for user in users_to_add:
    #     await add_user(user["user_id"], user["username"], user["group_id"], user["role"])

    # tasks_to_add = [
    #     {
    #         "teacher_id": 67890,
    #         "title": "Задание 1: Анализ данных",
    #         "description": "Проанализировать данные за прошедший месяц и представить отчёт.",
    #         "deadline": "2025-02-01",
    #         "checkpoints": "1. Собрать данные\n2. Проанализировать данные\n3. Подготовить отчет",
    #         "group_number": 232
    #     },
    #     {
    #         "teacher_id": 67890,
    #         "title": "Задание 2: Исследование",
    #         "description": "Провести исследование и подготовить научную работу.",
    #         "deadline": "2025-02-15",
    #         "checkpoints": "1. Выбрать тему\n2. Провести исследование\n3. Написать работу",
    #         "group_number": 234
    #     }
    # ]

    # for task in tasks_to_add:
    #     await add_task_to_db(task["teacher_id"], task["title"], task["description"], task["deadline"], task["checkpoints"], task["group_number"])

    # await update_task_status(student_id=123, task_id=1, status="Completed")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
