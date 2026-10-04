"""Aiogram bot client."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.config import settings


def create_bot() -> Bot:
    """Create Bot instance with default properties."""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create Dispatcher instance."""
    return Dispatcher()
