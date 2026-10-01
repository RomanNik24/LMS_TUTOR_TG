from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Homework, HomeworkStatusEnum
from .base import BaseRepository


class HomeworkRepository(BaseRepository[Homework]):
    def __init__(self):
        super().__init__(Homework)

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
