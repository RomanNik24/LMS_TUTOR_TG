"""Bot keyboards."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from src.core.config import settings


def get_guest_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Каталог услуг")],
            [KeyboardButton(text="Связаться с преподавателем")],
        ],
        resize_keyboard=True,
    )


def get_student_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=f"{settings.PUBLIC_BASE_URL}/app"))],
            [KeyboardButton(text="Расписание"), KeyboardButton(text="Мои ДЗ")],
        ],
        resize_keyboard=True,
    )


def get_staff_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открыть Admin App", web_app=WebAppInfo(url=f"{settings.PUBLIC_BASE_URL}/admin"))],
            [KeyboardButton(text="Сегодня"), KeyboardButton(text="На проверку")],
        ],
        resize_keyboard=True,
    )


def get_catalog_keyboard(current: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if current > 0:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"catalog_{current-1}"))
    if current < total - 1:
        row.append(InlineKeyboardButton(text="Далее ▶", callback_data=f"catalog_{current+1}"))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Связаться с преподавателем", url=settings.TEACHER_CONTACT_URL)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=confirm_data),
            InlineKeyboardButton(text="Отмена", callback_data=cancel_data),
        ]
    ])
