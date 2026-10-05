"""Bot setup and command registration."""

from aiogram import Bot, Dispatcher

from src.bot.client import create_bot, create_dispatcher
from src.bot.handlers import router as handlers_router
from src.bot.middlewares import AuthMiddleware


def setup_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure bot and dispatcher."""
    bot = create_bot()
    dp = create_dispatcher()

    # Middlewares
    dp.message.middleware(AuthMiddleware())

    # Routers
    dp.include_router(handlers_router)

    return bot, dp


async def set_bot_commands(bot: Bot):
    """Register bot commands with scopes."""
    from aiogram.types import BotCommand  # noqa: F401 (TODO: role scopes)

    # TODO: Set commands per role using BotCommandScopeChat
    # For now, set default commands
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="app", description="Открыть приложение"),
        BotCommand(command="today", description="Расписание на сегодня"),
        BotCommand(command="hw", description="Мои ДЗ / На проверку"),
        BotCommand(command="web", description="Войти в браузере"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="logout", description="Отвязать аккаунт"),
    ]
    await bot.set_my_commands(commands)
