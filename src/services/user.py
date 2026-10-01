"""Бизнес-логика пользователей: тарифы и пополнение баланса занятий."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import RoleEnum, User
from src.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self) -> None:
        self.user_repo = UserRepository()

    async def _get_student(self, session: AsyncSession, student_id: int) -> User:
        user = await self.user_repo.get_by_id(session, student_id)
        if not user or user.role != RoleEnum.student:
            raise NotFoundError(f"Ученик {student_id} не найден")
        return user

    async def set_lesson_price(
        self,
        session: AsyncSession,
        student_id: int,
        price: int,
    ) -> User:
        """Индивидуальный ценник занятия (docs/01, п.4.2 «Управление тарифами»)."""
        if price < 0:
            raise ValidationError("Стоимость занятия не может быть отрицательной")
        await self._get_student(session, student_id)
        updated = await self.user_repo.update(session, student_id, lesson_price=price)
        assert updated is not None
        return updated

    async def add_balance(
        self,
        session: AsyncSession,
        student_id: int,
        delta: int,
    ) -> User:
        """
        Ручная корректировка баланса преподавателем (оплата вне системы).

        Атомарный UPDATE ... SET balance = balance + :delta — параллельные
        пополнения и списания за уроки не теряют друг друга
        (нет read-modify-write гонки).
        """
        await self._get_student(session, student_id)
        new_balance = await self.user_repo.atomic_adjust_balance(
            session, student_id, delta
        )
        if new_balance is None:
            raise NotFoundError(f"Ученик {student_id} не найден")
        updated = await self.user_repo.get_by_id(session, student_id)
        assert updated is not None
        logger.info(
            "Balance of student %s changed by %d (new: %d)",
            student_id,
            delta,
            new_balance,
        )
        return updated
