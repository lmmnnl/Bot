from aiogram import Router, F
from aiogram import Bot
from aiogram import types
import aiosqlite
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger
from bot.database import DATABASE
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bot.database import get_user, add_user, update_username, update_group_number, update_user_role, get_sorted_groups, get_student_tasks, delete_task, get_task_statuses
from bot.keyboards import create_dynamic_menu
from bot.inline_handlers import create_task_status_buttons
from bot.fsm import TaskForm, UserState
from aiogram.filters import StateFilter
from bot.llm import get_response
import logging
logging.basicConfig(level=logging.INFO)

router = Router()

scheduler = AsyncIOScheduler()

async def send_deadline_notification(user_id: int, task_name: str, deadline: str, bot: Bot):
    await bot.send_message(user_id, f"Напоминаем, что дедлайн для задания '{task_name}' истекает {deadline}.")


async def schedule_deadline_notification(task_id: int, user_id: int, deadline: str, bot: Bot):
    deadline_datetime = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
    notification_time = deadline_datetime - timedelta(days=1)

    scheduler.add_job(
        send_deadline_notification, 
        trigger=CronTrigger(year=notification_time.year, month=notification_time.month, 
                            day=notification_time.day, hour=notification_time.hour, 
                            minute=notification_time.minute),
        args=[user_id, task_id, deadline, bot],
        max_instances=1
    )

async def send_notification(user_id: int, bot: Bot):
    await bot.send_message(user_id, "СООБЩЕНИЕ ЧЕРЕЗ 48 ЧАСОВ ПОСЛЕ СТАРТА")

async def create_role_keyboard():
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Студент", callback_data="role_student")],
        [InlineKeyboardButton(text="Преподаватель", callback_data="role_teacher")]
    ])
    return inline_keyboard

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user:
        username, group_id, role = user[1], user[2], user[3]
        await message.answer(
            f"Мы вас помним, {username}! Вы в группе {group_id} с ролью {role}.",
            reply_markup=create_dynamic_menu()
        )
    else:
        username = message.from_user.username or "Неизвестно"
        await add_user(user_id, username=username, role='student')
        await message.answer(
            "Добро пожаловать! Пожалуйста, выберите вашу роль:",
            reply_markup=await create_role_keyboard()  
        )
        await state.set_state(UserState.waiting_role) 

    bot = message.bot
    scheduler.add_job(
        send_notification,
        trigger=IntervalTrigger(hours=48),
        args=[user_id, bot],
        max_instances=6
    )
    scheduler.start()

@router.callback_query(lambda call: call.data in ["role_student", "role_teacher"])
async def handle_role_selection(call: CallbackQuery, state: FSMContext):
    role = "student" if call.data == "role_student" else "teacher"
    await state.update_data(role=role)

    user_id = call.from_user.id
    await update_user_role(user_id, role)

    await call.message.answer(f"Вы выбрали роль: {role}. Теперь введите своё имя.") 
    await state.set_state(UserState.waiting_name)
    await call.answer() 

@router.message(UserState.waiting_name)
async def handle_name_input(message: Message, state: FSMContext):
    user_name = message.text.strip()
    user_id = message.from_user.id

    if user_name:
        await update_username(user_id, user_name)
        await state.update_data(user_name=user_name)

        user_data = await state.get_data()
        role = user_data.get("role")

        if role == "teacher":
            await message.answer(
                f"Имя обновлено!\nНовое имя: {user_name}\nРоль: {role}",
                reply_markup=create_dynamic_menu()
            )
            await state.clear()
        else:
            await message.answer("Спасибо! Теперь укажите номер своей группы.")
            await state.set_state(UserState.waiting_group)
    else:
        await message.answer("Имя не может быть пустым. Попробуйте снова.")

@router.message(UserState.waiting_group)
async def handle_group_input(message: Message, state: FSMContext):
    group_number = message.text.strip()
    user_id = message.from_user.id
    user_data = await state.get_data()

    role = user_data.get("role")

    if role == "teacher":
        await message.answer(
            f"Регистрация завершена!\nИмя: {user_data.get('user_name')}\nРоль: {role}",
            reply_markup=create_dynamic_menu()
        )
        await state.clear()
    elif group_number:
        await update_group_number(user_id, group_number)

        async with aiosqlite.connect(DATABASE) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT task_id FROM tasks WHERE group_number = ?
            """, (group_number,))
            tasks = await cursor.fetchall()

            for task in tasks:
                task_id = task[0]
                await cursor.execute("""
                    INSERT INTO task_status (task_id, user_id, status)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, "Not started"))
            await conn.commit()

        await message.answer(
            f"Регистрация завершена!\nИмя: {user_data.get('user_name')}\nГруппа: {group_number}",
            reply_markup=create_dynamic_menu()
        )
        await state.clear()
    else:
        await message.answer("Номер группы не может быть пустым. Попробуйте снова.")

@router.message(Command("info"))
async def info_handler(message: Message):
    info = (
        "<b>Команды:</b>\n\n"
        "/start — Запустить бота\n"
        "/info — Инструкции\n"
        "/change_name — Сменить имя\n\n"
        "<b>Доступны только преподавателю:\n</b>"
        "/groups — Списки групп\n"
        "/add_task - Добавить заданию\n"
        "/del_task - Удалить задание\n"
        "/task_statuses - Статус выполнения заданий\n\n"
        "<b>Кнопки:</b>\n"
        "'Задания'- Все задания\n"
        "'Начать чат с помощником'- Включения чата с ассистентом по учебе\n"
    )
    await message.answer(info, parse_mode="HTML")

@router.message(Command("change_name"))
async def change_name_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user:
        await message.answer("Пожалуйста, введите новое имя.")
        await state.set_state(UserState.waiting_name)
    else:
        await message.answer("Вы не зарегистрированы. Пожалуйста, начните с команды /start.")

@router.message(Command("groups"))
async def groups_handler(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user and user[3] == "teacher":
        groups = await get_sorted_groups()
        if groups:
            group_list = "\n".join([f"Группа {group_id}:\n " + "\n".join(students) + "\n" for group_id, students in groups.items()])
            await message.answer(f"Список всех групп:\n\n{group_list}")
        else:
            await message.answer("Нет доступных групп.")
    else:
        await message.answer("Эта команда доступна только преподавателю.")

@router.message(F.text == "Задания")
async def tasks_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user:
        role = user[3]
        if role == "student":
            tasks_text = await get_student_tasks(user_id)
            for task in tasks_text:
                task_id = task[0]
                task_name = task[1]
                task_description = task[2]
                task_deadline = task[3]
                buttons = await create_task_status_buttons(task_id)
                await message.answer(
                    f"<b>{task_name}</b>\n"
                    f"Описание: {task_description}\n"
                    f"Дедлайн: {task_deadline}\n",
                    reply_markup=buttons,
                    parse_mode="HTML"
                )  
        elif role == "teacher":
            async with aiosqlite.connect(DATABASE) as conn:
                cursor = await conn.cursor()
                await cursor.execute("""
                SELECT title, description, deadline, group_number 
                FROM tasks
                """)
                tasks = await cursor.fetchall()

            if tasks:
                text = "Все задания:\n\n"
                for task in tasks:
                    text += f"<b>{task[0]}</b>\nОписание: {task[1]}\nДедлайн: {task[2]}\nГруппа: {task[3]}\n\n"
                await message.answer(text, parse_mode="HTML")
            else:
                await message.answer("Нет доступных заданий.")

@router.message(Command("add_task"))
async def add_task_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user and user[3] == "teacher":
        await state.set_state(TaskForm.title)
        await message.answer("Введите название задания:")
    else:
        await message.answer("Эта команда доступна только преподавателям.")

@router.message(TaskForm.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    
    await state.set_state(TaskForm.description)
    await message.answer("Введите описание задания:")

@router.message(TaskForm.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    await state.set_state(TaskForm.deadline)
    await message.answer("Введите дедлайн задания (строго 'YYYY-MM-DD HH-MM-SS'):")

@router.message(TaskForm.deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    
    await state.set_state(TaskForm.checkpoints)
    await message.answer("Введите контрольные точки (через запятую):")

@router.message(TaskForm.checkpoints)
async def process_checkpoints(message: types.Message, state: FSMContext):
    await state.update_data(checkpoints=message.text)
    
    await state.set_state(TaskForm.group_number)
    await message.answer("Введите номер группы:")

@router.message(TaskForm.group_number)
async def process_group_number(message: types.Message, state: FSMContext):
    await state.update_data(group_number=message.text)

    user_data = await state.get_data()
    title = user_data['title']
    description = user_data['description']
    deadline = user_data['deadline']
    checkpoints = user_data['checkpoints']
    group_number = user_data['group_number']

    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()

        await cursor.execute("""
        INSERT INTO tasks (teacher_id, title, description, deadline, checkpoints, group_number)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (message.from_user.id, title, description, deadline, checkpoints, group_number))
        await conn.commit()

        task_id = cursor.lastrowid

        await cursor.execute("""
        SELECT user_id FROM users WHERE group_id = ?
        """, (group_number,))
        students = await cursor.fetchall()

        for student in students:
            student_id = student[0]
            await schedule_deadline_notification(task_id, student_id, deadline, message.bot)

        await conn.commit()

    await state.clear()

    await message.answer("Задание успешно добавлено и статус для студентов обновлен!")

@router.message(Command("del_task"))
async def del_task_handler(message: types.Message, state: FSMContext):
    logging.info(f"Received command: {message.text} from user_id: {message.from_user.id}")
    
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if user:
        logging.info(f"User found: {user}")
        role = user[3] 
        if role == "teacher":
            command_parts = message.text.split()
            if len(command_parts) != 2:
                await message.answer("Пожалуйста, укажите ID задания для удаления вместе с командой.\nПример: /del_task 1")
                return
            try:
                task_id = int(command_parts[1])
            except ValueError:
                await message.answer("Некорректный формат ID задания. Пожалуйста, укажите числовой ID.")
                return

            result = await delete_task(task_id, user_id)
            logging.info(f"Delete task result: {result}")
            await message.answer(result)
        else:
            await message.answer("Эта команда доступна только преподавателям.")
    else:
        logging.warning(f"User with ID {user_id} not found.")
        await message.answer("Студент не найден.")

@router.message(Command("task_statuses"))
async def task_status_handler(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user and user[3] == "teacher":
        statuses = await get_task_statuses()

        if statuses:
            text = "<b>Статусы выполнения заданий:</b>\n\n"
            for task_title, student_name, status in statuses:
                text += f"<b>Задание:</b> {task_title}\n<b>Студент:</b> {student_name}\n<b>Статус:</b> {status}\n\n"
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("Нет информации о статусах заданий.")
    else:
        await message.answer("Эта команда доступна только преподавателю.")

@router.callback_query(lambda call: call.data.startswith("status_"))
async def handle_task_status_change(call: CallbackQuery):
    data_parts = call.data.split("_")
    task_id = int(data_parts[1])
    new_status = data_parts[2]

    user_id = call.from_user.id
    user = await get_user(user_id)

    if user:
        async with aiosqlite.connect(DATABASE) as conn:
            cursor = await conn.cursor()
            await cursor.execute("""
                UPDATE task_status
                SET status = ?
                WHERE task_id = ? AND user_id = ?
            """, (new_status, task_id, user_id))
            await conn.commit()

        await call.message.answer(f"Статус задания {task_id} обновлён на: {new_status.capitalize()}.")
        await call.answer()

@router.message(F.text == "Начать чат с помощником")
async def start_chat(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if user and user[1]:
        await state.set_state(UserState.chatting)
        await message.answer("Чат с помощником начался! Напишите 'stop' для завершения.")
    else:
        await message.answer("Чат выключен.")

@router.message(StateFilter(UserState.chatting))
async def chat_with_helper(message: Message, state: FSMContext):
    user_message = message.text

    if user_message.lower() == 'stop':
        await state.clear()
        await message.answer("Чат завершен. Напишите 'Начать чат с помощником', чтобы снова начать.")
    else:
        model_response = get_response(user_message)
        await message.answer(model_response)

@router.message()
async def handle_inactive_chat(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != UserState.chatting:
        await message.answer("Чат неактивен. Напишите 'Начать чат с помощником', чтобы начать.")
