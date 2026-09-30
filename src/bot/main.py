import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.config import settings, logger
from src.bot.handlers.base import router
from src.bot.middlewares.db import DbSessionMiddleware

async def main():
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем Middleware для внедрения сессии БД во все обработчики
    dp.message.middleware(DbSessionMiddleware())
    
    # Подключаем роутеры
    dp.include_router(router)
    
    logger.info("Запуск Telegram-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
