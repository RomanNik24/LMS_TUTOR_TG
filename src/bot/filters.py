"""Bot filters."""

from aiogram.filters import Filter
from aiogram.types import Message

from src.db.models.users import User


class IsGuestFilter(Filter):
    """True if user has no account or is archived."""
    async def __call__(self, message: Message, current_user: User | None = None) -> bool:
        return current_user is None


class IsStudentFilter(Filter):
    """True if user is student."""
    async def __call__(self, message: Message, current_user: User | None = None) -> bool:
        return current_user is not None and current_user.role == "student"


class IsStaffFilter(Filter):
    """True if user is owner or manager."""
    async def __call__(self, message: Message, current_user: User | None = None) -> bool:
        return current_user is not None and current_user.role in ("owner", "manager")
