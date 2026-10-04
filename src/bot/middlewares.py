"""Bot middlewares."""

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from typing import Callable, Awaitable, Any, Dict

from src.core.config import settings
from src.services.auth import AuthService
from src.db.session import get_session


class AuthMiddleware(BaseMiddleware):
    """Attach current user to handler data based on telegram_id."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser = data.get("event_from_user")
        if not tg_user:
            data["current_user"] = None
            return await handler(event, data)

        # TODO: Get user from DB via telegram_id
        # For now, stub
        data["current_user"] = None
        return await handler(event, data)