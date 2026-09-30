from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Lesson
from .base import BaseRepository

class LessonRepository(BaseRepository[Lesson]):
    def __init__(self):
        super().__init__(Lesson)

    async def get_student_lessons(self, session: AsyncSession, student_id: int) -> list[Lesson]:
        """Получить все уроки конкретного ученика"""
        stmt = select(self.model).where(self.model.student_id == student_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
