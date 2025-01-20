from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_role = State()
    waiting_name = State()
    waiting_group = State()
    waiting_feedback = State() 
    chatting = State()

class TaskForm(StatesGroup):
    title = State()
    description = State()
    deadline = State()
    checkpoints = State()
    group_number = State()