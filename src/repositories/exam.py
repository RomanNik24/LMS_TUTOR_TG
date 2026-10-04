"""Exam repository."""

from typing import Optional
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import BaseRepository
from src.db.models.exam import MockExamResult
from src.db.models.reference import ExamType, GradeScale


class MockExamResultRepository(BaseRepository[MockExamResult]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MockExamResult)

    async def get_for_student(self, student_id: int, exam_type_id: Optional[int] = None) -> list[MockExamResult]:
        stmt = select(MockExamResult).where(MockExamResult.student_id == student_id)
        if exam_type_id:
            stmt = stmt.where(MockExamResult.exam_type_id == exam_type_id)
        stmt = stmt.order_by(MockExamResult.exam_date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExamTypeRepository(BaseRepository[ExamType]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ExamType)

    async def get_active(self) -> list[ExamType]:
        stmt = select(ExamType).where(ExamType.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class GradeScaleRepository(BaseRepository[GradeScale]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, GradeScale)

    async def get_scale_for_exam(self, exam_type_id: int, exam_year: int) -> list[GradeScale]:
        stmt = select(GradeScale).where(
            GradeScale.exam_type_id == exam_type_id,
            GradeScale.valid_year <= exam_year,
        ).order_by(GradeScale.valid_year.desc(), GradeScale.primary_score)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())