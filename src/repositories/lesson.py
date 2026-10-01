from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Lesson, LessonStatusEnum
from .base import BaseRepository


class LessonRepository(BaseRepository[Lesson]):
    def __init__(self):
        super().__init__(Lesson)

    async def mark_completed_atomic(
        self, session: AsyncSession, lesson_id: int
    ) -> Optional[Lesson]:
        """
        Атомарный переход scheduled|needs_confirmation -> completed
        (условный UPDATE).

        WHERE status IN ('scheduled', 'needs_confirmation') гарантирует, что
        при параллельных вызовах (ручное /complete из API и cron-подтверждение
        из воркера) ровно один запрос обновит строку; второй получит None и не
        приведёт к повторному списанию баланса. Возвращает обновлённый урок
        либо None, если урок уже завершён/отменён или не найден.
        """
        stmt = (
            update(self.model)
            .where(self.model.id == lesson_id)
            .where(
                self.model.status.in_(
                    [LessonStatusEnum.scheduled, LessonStatusEnum.needs_confirmation]
                )
            )
            .values(status=LessonStatusEnum.completed)
            .returning(self.model)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one_or_none()

    async def mark_needs_confirmation_atomic(
        self, session: AsyncSession, lesson_id: int
    ) -> Optional[Lesson]:
        """
        Атомарный переход scheduled -> needs_confirmation (условный UPDATE).

        Используется cron-автозакрытием: урок помечается «ждёт подтверждения»
        БЕЗ списания баланса. WHERE status='scheduled' — повторный cron-проход
        или параллельная отмена/завершение не дадут второго перехода.
        """
        stmt = (
            update(self.model)
            .where(self.model.id == lesson_id)
            .where(self.model.status == LessonStatusEnum.scheduled)
            .values(status=LessonStatusEnum.needs_confirmation)
            .returning(self.model)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one_or_none()

    async def get_student_lessons(
        self,
        session: AsyncSession,
        student_id: int,
        after: Optional[datetime] = None,
    ) -> list[Lesson]:
        """Получить уроки ученика, отсортированные по времени начала."""
        stmt = (
            select(self.model)
            .where(self.model.student_id == student_id)
            .order_by(self.model.start_time)
        )
        if after is not None:
            stmt = stmt.where(self.model.start_time >= after)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_in_period(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        status: Optional[LessonStatusEnum] = None,
    ) -> list[Lesson]:
        """Уроки всех учеников в временном окне (для дашборда/отчётов)."""
        stmt = select(self.model).where(
            self.model.start_time >= start,
            self.model.start_time < end,
        )
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        stmt = stmt.order_by(self.model.start_time)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_lesson_ids_for_student(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[int]:
        """Только ID уроков ученика (используется для выбора ДЗ без N+1)."""
        stmt = select(self.model.id).where(self.model.student_id == student_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def has_overlap(
        self,
        session: AsyncSession,
        student_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Проверка пересечения слотов у ученика (scheduled-уроки)."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.student_id == student_id,
                self.model.status == LessonStatusEnum.scheduled,
                self.model.start_time < end_time,
                self.model.end_time > start_time,
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count_completed_in_period(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        student_id: Optional[int] = None,
    ) -> int:
        """Сколько уроков проведено (completed) за период."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.status == LessonStatusEnum.completed,
                self.model.start_time >= start,
                self.model.start_time < end,
            )
        )
        if student_id is not None:
            stmt = stmt.where(self.model.student_id == student_id)
        result = await session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_cancelled_in_period(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
    ) -> int:
        """Статистика отменённых занятий за период (docs/01, п.4.2)."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.status == LessonStatusEnum.cancelled,
                self.model.start_time >= start,
                self.model.start_time < end,
            )
        )
        result = await session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_upcoming_starting_between(
        self,
        session: AsyncSession,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Lesson]:
        """Scheduled-уроки, начинающиеся в окне [from_dt, to_dt) — для воркера."""
        stmt = (
            select(self.model)
            .where(
                self.model.status == LessonStatusEnum.scheduled,
                self.model.start_time >= from_dt,
                self.model.start_time < to_dt,
            )
            .order_by(self.model.start_time)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_finished_scheduled_until(
        self,
        session: AsyncSession,
        now: datetime,
    ) -> list[Lesson]:
        """Завершившиеся уроки со статусом scheduled (ждут списания баланса)."""
        stmt = (
            select(self.model)
            .where(
                self.model.status == LessonStatusEnum.scheduled,
                self.model.end_time <= now,
            )
            .order_by(self.model.start_time)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_finished_completed_since(
        self,
        session: AsyncSession,
        since: datetime,
    ) -> list[Lesson]:
        """Завершённые (completed) уроки, закончившиеся после `since`.

        Используется воркером для подтверждения автозакрытия ученику/админу.
        """
        stmt = (
            select(self.model)
            .where(
                self.model.status == LessonStatusEnum.completed,
                self.model.end_time >= since,
            )
            .order_by(self.model.start_time)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
