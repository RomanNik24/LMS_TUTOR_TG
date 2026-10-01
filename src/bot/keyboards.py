from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types.web_app_info import WebAppInfo

from src.core.config import settings


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура авторизованных пользователей с кнопкой Mini App.

    URL берётся из настроек (webapp_url), а не захардкожен (docs/05_bot_logic).
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ],
            [KeyboardButton(text="📚 Каталог курсов")],
        ],
        resize_keyboard=True,
    )
