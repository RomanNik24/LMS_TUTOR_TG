from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Homework, HomeworkStatusEnum, Lesson, RoleEnum, User
from .base import BaseRepository


class HomeworkRepository(BaseRepository[Homework]):
    def __init__(self):
        super().__init__(Homework)

    async def get_for_student_with_user(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> Optional[list[tuple[Homework, User]]]:
        """Все ДЗ ученика + сам ученик ОДНИМ запросом (JOIN lessons + JOIN users).

        Возвращает список пар (homework, user); если ученика с ролью student
        и указанным id нет — None (сервис транслирует это в 404). Пользователь
        подтягивается тем же запросом, поэтому проверка существования не
        добавляет SELECT — N+1 по-прежнему нет.
        """
        stmt = (
            select(Homework, User)
            .join(Lesson, Homework.lesson_id == Lesson.id)
            .join(User, User.id == Lesson.student_id)
            .where(Lesson.student_id == student_id)
            .where(User.role == RoleEnum.student)
            .order_by(Homework.deadline)
        )
        result = await session.execute(stmt)
        rows = result.all()
        if not rows:
            # Отличаем «ученика нет» от «ученик есть, но ДЗ нет»: один точечный
            # SELECT только при пустом списке (обычный путь — 0 доп. запросов).
            exists = await session.execute(
                select(User.id).where(User.id == student_id, User.role == RoleEnum.student)
            )
            if exists.scalar_one_or_none() is None:
                return None
            # Ученик существует, но уроков/ДЗ нет — возвращаем пустой список;
            # вернуть пару всё равно не с чем, берём пользователя отдельным запросом.
            user = await session.get(User, student_id)
            return [] if user is not None else None
        return [(row[0], row[1]) for row in rows]

    async def get_for_student(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[Homework]:
        """Все ДЗ ученика ОДНИМ запросом (JOIN с уроками).

        В модели Homework нет student_id — он берётся из родительского урока,
        поэтому выборка через join, а не «список id уроков + IN(...)».
        """
        stmt = (
            select(Homework)
            .join(Lesson, Homework.lesson_id == Lesson.id)
            .where(Lesson.student_id == student_id)
            .order_by(Homework.deadline)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_lesson_id(self, session: AsyncSession, lesson_id: int) -> list[Homework]:
        """Получить все ДЗ по ID урока."""
        stmt = (
            select(self.model)
            .where(self.model.lesson_id == lesson_id)
            .order_by(self.model.deadline)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_lesson_ids(
        self,
        session: AsyncSession,
        lesson_ids: list[int],
    ) -> list[Homework]:
        """ДЗ по списку уроков одним запросом (устраняет N+1)."""
        if not lesson_ids:
            return []
        stmt = (
            select(self.model)
            .where(self.model.lesson_id.in_(lesson_ids))
            .order_by(self.model.deadline)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_due_before(
        self,
        session: AsyncSession,
        deadline_until: datetime,
        status: Optional[HomeworkStatusEnum] = HomeworkStatusEnum.pending,
        after: Optional[datetime] = 0,  # sentinel: не фильтровать по нижней границе
    ) -> list[Homework]:
        """ДЗ с дедлайном до указанной даты и заданным статусом (для воркера).

        `after=None` (явно переданный) снимает нижнюю границу; по умолчанию
        возвращаются также просроченные ДЗ (нужно для автозакрытия/отчётов).
        """
        stmt = select(self.model).where(self.model.deadline <= deadline_until)
        if after is not None and after != 0:
            stmt = stmt.where(self.model.deadline > after)
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        stmt = stmt.order_by(self.model.deadline)
        result = await session.execute(stmt)
        return list(result.scalars().all())
