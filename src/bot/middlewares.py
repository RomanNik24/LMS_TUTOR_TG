"""Bot middlewares."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TgUser


class AuthMiddleware(BaseMiddleware):
    """Attach current user to handler data based on telegram_id."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser = data.get("event_from_user")
        if not tg_user:
            data["current_user"] = None
            return await handler(event, data)

        # TODO: Get user from DB via telegram_id
        # For now, stub
        data["current_user"] = None
        return await handler(event, data)
