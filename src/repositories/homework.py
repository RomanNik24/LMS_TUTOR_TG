"""Homework repository."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import HomeworkStatus
from src.db.models.homework import Homework, HomeworkAssignment, HomeworkFile
from src.repositories import BaseRepository


class HomeworkRepository(BaseRepository[Homework]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Homework)


class HomeworkAssignmentRepository(BaseRepository[HomeworkAssignment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, HomeworkAssignment)

    async def get_by_homework_and_student(self, homework_id: int, student_id: int) -> HomeworkAssignment | None:
        stmt = select(HomeworkAssignment).where(
            HomeworkAssignment.homework_id == homework_id,
            HomeworkAssignment.student_id == student_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_student(self, student_id: int, status: HomeworkStatus | None = None) -> list[HomeworkAssignment]:
        stmt = select(HomeworkAssignment).where(HomeworkAssignment.student_id == student_id)
        if status:
            stmt = stmt.where(HomeworkAssignment.status == status)
        stmt = stmt.order_by(HomeworkAssignment.due_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_review_queue(self, teacher_id: int) -> list[HomeworkAssignment]:
        stmt = select(HomeworkAssignment).join(Homework).where(
            Homework.created_by == teacher_id,
            HomeworkAssignment.status == HomeworkStatus.SUBMITTED,
        ).order_by(HomeworkAssignment.submitted_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_candidates(self) -> list[HomeworkAssignment]:
        from datetime import datetime
        now = datetime.now()
        stmt = select(HomeworkAssignment).where(
            HomeworkAssignment.status.in_([HomeworkStatus.ASSIGNED, HomeworkStatus.NEEDS_REVISION]),
            HomeworkAssignment.due_at < now,
            HomeworkAssignment.extensions_count >= 2,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class HomeworkFileRepository(BaseRepository[HomeworkFile]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, HomeworkFile)

    async def count_student_files(self, assignment_id: int) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).where(
            HomeworkFile.assignment_id == assignment_id,
            HomeworkFile.role == "student_solution",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
