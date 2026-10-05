"""Bot FSM states."""

from aiogram.fsm.state import State, StatesGroup


class ConfirmRelinkState(StatesGroup):
    waiting_confirm = State()


class LogoutState(StatesGroup):
    waiting_confirm = State()
