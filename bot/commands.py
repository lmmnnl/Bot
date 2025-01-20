from aiogram import Bot
from aiogram.types import BotCommand

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/info", description="Информация"),
        BotCommand(command="/change_name", description="Сменить имя"),
        BotCommand(command="/groups", description="Списки групп (teacher)"),
        BotCommand(command="/add_task", description="Добавить задание (teacher)"),
        BotCommand(command="/del_task", description="Удалить задание (teacher)"),
        BotCommand(command="/task_statuses", description="Статус выполнения заданий (teacher)"),
    ]
    await bot.set_my_commands(commands)