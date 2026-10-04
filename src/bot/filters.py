"""Bot filters."""

from aiogram.filters import Filter
from aiogram.types import Message


class IsGuestFilter(Filter):
    """True if user has no account or is archived."""
    async def __call__(self, message: Message) -> bool:
        user = message.conf.get("current_user")
        return user is None


class IsStudentFilter(Filter):
    """True if user is student."""
    async def __call__(self, message: Message) -> bool:
        user = message.conf.get("current_user")
        return user and user.role == "student"


class IsStaffFilter(Filter):
    """True if user is owner or manager."""
    async def __call__(self, message: Message) -> bool:
        user = message.conf.get("current_user")
        return user and user.role in ("owner", "manager")
