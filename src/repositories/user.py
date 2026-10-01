from typing import Optional
from sqlalchemy import select, update
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

    async def get_by_role(self, session: AsyncSession, role: RoleEnum) -> list[User]:
        """Все пользователи с указанной ролью (для уведомлений админу)."""
        stmt = select(self.model).where(self.model.role == role)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def atomic_adjust_balance(
        self,
        session: AsyncSession,
        user_id: int,
        delta: int,
    ) -> Optional[int]:
        """
        Атомарное изменение баланса одним запросом:
        UPDATE users SET balance = balance + :delta WHERE id = :id.

        Никакого read-modify-write — гонка между параллельными пополнениями
        (ручная оплата в админке) исключена на уровне СУБД.
        Возвращает новый баланс или None, если пользователь не найден.
        """
        stmt = (
            update(self.model)
            .where(self.model.id == user_id)
            .values(balance=self.model.balance + delta)
            .returning(self.model.balance)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one_or_none()
