from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import MockExam
from .base import BaseRepository


class MockExamRepository(BaseRepository[MockExam]):
    def __init__(self):
        super().__init__(MockExam)

    async def get_student_exams(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[MockExam]:
        """Все пробники ученика в хронологическом порядке (для графика динамики)."""
        stmt = (
            select(self.model)
            .where(self.model.student_id == student_id)
            .order_by(self.model.date)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
