from aiogram.fsm.state import State, StatesGroup

class LoginStates(StatesGroup):
    wait_for_login = State()
    wait_for_password = State()
