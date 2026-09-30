from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Homework
from .base import BaseRepository

class HomeworkRepository(BaseRepository[Homework]):
    def __init__(self):
        super().__init__(Homework)

    async def get_by_lesson_id(self, session: AsyncSession, lesson_id: int) -> list[Homework]:
        """Получить все ДЗ по ID урока"""
        stmt = select(self.model).where(self.model.lesson_id == lesson_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
