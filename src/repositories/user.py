from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User, RoleEnum
from .base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_all_students(self, session: AsyncSession) -> list[User]:
        """Получить всех учеников"""
        stmt = select(self.model).where(self.model.role == RoleEnum.student)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_login(self, session: AsyncSession, login: str) -> Optional[User]:
        """Найти пользователя по логину"""
        stmt = select(self.model).where(self.model.login == login)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Найти пользователя по telegram_id"""
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
