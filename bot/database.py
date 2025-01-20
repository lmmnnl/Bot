import aiosqlite
import logging
logging.basicConfig(level=logging.INFO)

DATABASE = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            group_id INTEGER,
            role TEXT NOT NULL DEFAULT 'student'
        )
        """)

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            deadline TEXT NOT NULL,
            checkpoints TEXT,
            status TEXT DEFAULT 'Not started',
            group_number INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES users (user_id)
        )
        """)

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_status (
            task_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'Not started',
            FOREIGN KEY (task_id) REFERENCES tasks (task_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            PRIMARY KEY (task_id, user_id)
        )
        """)

        await conn.commit()

async def add_user(user_id, username, group_id=None, role='student'):
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username, group_id, role)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, group_id, role)
        )
        await conn.commit()

async def update_username(user_id: int, username: str):
    async with aiosqlite.connect(DATABASE) as conn:
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (username, user_id)
                )
                await conn.commit() 
        except Exception as e:
            print(f"Ошибка при обновлении имени: {e}")

async def update_group_number(user_id: int, group_number: str):
    async with aiosqlite.connect(DATABASE) as conn:
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE users SET group_id = ? WHERE user_id = ?",
                    (group_number, user_id)
                )
                await conn.commit() 
        except Exception as e:
            print(f"Ошибка при обновлении номера группы: {e}")

async def get_user(user_id):
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def update_user_role(user_id: int, role: str):
    query = "UPDATE users SET role = ? WHERE user_id = ?"
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute(query, (role, user_id))
        await conn.commit()

async def get_sorted_groups():
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()

        await cursor.execute("""
        SELECT group_id, username
        FROM users
        ORDER BY group_id, username
        """)

        rows = await cursor.fetchall()

        groups = {}
        for row in rows:
            group_id = row[0]
            username = row[1]

            if group_id not in groups:
                groups[group_id] = []

            groups[group_id].append(username)

        return groups

async def add_task_to_db(teacher_id, title, description, deadline, checkpoints, group_number):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """
            INSERT INTO tasks (teacher_id, title, description, deadline, checkpoints, group_number)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (teacher_id, title, description, deadline, checkpoints, group_number)
        )
        await db.commit()

async def get_student_tasks(user_id: int) -> str:
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()
        await cursor.execute("""
        SELECT task_id, title, description, deadline, deadline
        FROM tasks
        WHERE group_number = (SELECT group_id FROM users WHERE user_id = ?)
        """, (user_id,))
        tasks = await cursor.fetchall()

    if tasks:
        return tasks
    return "Нет заданий для вашей группы."

async def delete_task(task_id: int, teacher_id: int):
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()

        await cursor.execute("SELECT role FROM users WHERE user_id = ?", (teacher_id,))
        user = await cursor.fetchone()
        if not user or user[0] != 'teacher':
            return "Ошибка: только преподаватель может удалить задание."

        await cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            return f"Задание с ID {task_id} не найдено."

        await cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        await conn.commit()

        return f"Задание с ID {task_id} успешно удалено."

async def get_task_statuses():
    async with aiosqlite.connect(DATABASE) as conn:
        cursor = await conn.cursor()
        await cursor.execute(f"SELECT * FROM task_status")
        
        statuses = await cursor.fetchall()
        return statuses

async def update_task_status(student_id: int, task_id: int, status: str):
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute("""
            INSERT INTO task_status (task_id, user_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(task_id, user_id) DO UPDATE SET status = ?
        """, (task_id, student_id, status, status))
        await conn.commit()
