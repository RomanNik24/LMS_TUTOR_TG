"""Точка входа Telegram-бота (Aiogram 3).

FSM хранится в Redis (docs/02_tech_stack.md) — состояния переживают рестарт.
Сессии БД внедряются через DbSessionMiddleware из единого src/db/session.py.
"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from src.bot.handlers.base import router
from src.bot.middlewares.db import DbSessionMiddleware
from src.core.config import logger, settings


def _build_storage() -> RedisStorage:
    """FSM-хранилище в Redis."""
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def key_builder(
        bot: Bot,
        event_update_type: str | int,
        event_context: dict,
    ) -> StorageKey:
        # Ключи по user_id вместо chat_id (стандартный DefaultKeyBuilder
        # использует chat_id=user_id, что ломает FSM в ЛС при разных чатах)
        return StorageKey(
            bot_id=bot.id,
            user_id=event_context["from_user"].id,
            chat_id=event_context["chat"].id,
        )

    return RedisStorage(redis=redis, key_builder=key_builder)


async def main() -> None:
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=_build_storage())

    # Подключаем Middleware для внедрения сессии БД во все обработчики
    dp.message.middleware(DbSessionMiddleware())

    # Подключаем роутеры
    dp.include_router(router)

    logger.info("Запуск Telegram-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
