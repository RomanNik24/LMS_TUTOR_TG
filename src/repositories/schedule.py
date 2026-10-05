"""Schedule repository."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import LessonStatus
from src.db.models.schedule import Lesson, LessonParticipant, ScheduleTemplate
from src.repositories import BaseRepository


class ScheduleTemplateRepository(BaseRepository[ScheduleTemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ScheduleTemplate)

    async def get_active_for_teacher(self, teacher_id: int) -> list[ScheduleTemplate]:
        stmt = select(ScheduleTemplate).where(
            ScheduleTemplate.teacher_id == teacher_id,
            ScheduleTemplate.is_active,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class LessonRepository(BaseRepository[Lesson]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Lesson)

    async def get_by_template_and_start(self, template_id: int, start_at: datetime) -> Lesson | None:
        stmt = select(Lesson).where(
            Lesson.template_id == template_id,
            Lesson.start_at == start_at,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_teacher_in_range(self, teacher_id: int, from_dt: datetime, to_dt: datetime) -> list[Lesson]:
        stmt = select(Lesson).where(
            Lesson.teacher_id == teacher_id,
            Lesson.start_at >= from_dt,
            Lesson.start_at < to_dt,
        ).order_by(Lesson.start_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_student_in_range(self, student_id: int, from_dt: datetime, to_dt: datetime) -> list[Lesson]:
        stmt = select(Lesson).join(LessonParticipant).where(
            LessonParticipant.student_id == student_id,
            Lesson.start_at >= from_dt,
            Lesson.start_at < to_dt,
        ).order_by(Lesson.start_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def check_teacher_overlap(self, teacher_id: int, start_at: datetime, end_at: datetime, exclude_id: int | None = None) -> bool:
        from sqlalchemy import exists
        stmt = select(exists().where(
            Lesson.teacher_id == teacher_id,
            Lesson.status != LessonStatus.CANCELLED,
            Lesson.start_at < end_at,
            Lesson.end_at > start_at,
        ))
        if exclude_id:
            stmt = stmt.where(Lesson.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()


class LessonParticipantRepository(BaseRepository[LessonParticipant]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LessonParticipant)

    async def get_for_lesson(self, lesson_id: int) -> list[LessonParticipant]:
        stmt = select(LessonParticipant).where(LessonParticipant.lesson_id == lesson_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_student_lesson(self, student_id: int, lesson_id: int) -> LessonParticipant | None:
        stmt = select(LessonParticipant).where(
            LessonParticipant.student_id == student_id,
            LessonParticipant.lesson_id == lesson_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
