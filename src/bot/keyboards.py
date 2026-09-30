from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.web_app_info import WebAppInfo

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура для авторизованных пользователей с кнопкой Web App"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url="https://google.com/")
                )
            ]
        ],
        resize_keyboard=True
    )
