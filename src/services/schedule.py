"""Schedule service: lessons, templates, generation."""

from datetime import datetime, timedelta, time
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.schedule import ScheduleTemplateRepository, LessonRepository, LessonParticipantRepository
from src.repositories.user import UserRepository
from src.repositories.service import AuditLogRepository
from src.services.auth import AuthService
from src.core.exceptions import NotFoundError, PermissionDeniedError, BusinessRuleError
from src.core.enums import UserRole, LessonStatus, AttendanceStatus
from src.db.models.schedule import ScheduleTemplate, ScheduleTemplateParticipant, Lesson, LessonParticipant
from src.db.models.users import User
from src.core.timeutils import utc_now


class ScheduleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.templates = ScheduleTemplateRepository(session)
        self.lessons = LessonRepository(session)
        self.participants = LessonParticipantRepository(session)
        self.users = UserRepository(session)
        self.auth = AuthService(session)
        self.audit = AuditLogRepository(session)

    async def create_lesson(
        self,
        actor: User,
        subject_id: int,
        teacher_id: int,
        start_at: datetime,
        end_at: datetime,
        student_ids: list[int],
        video_url_override: Optional[str] = None,
        board_url_override: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Lesson:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_lesson")

        # Check teacher overlap
        if await self.lessons.check_teacher_overlap(teacher_id, start_at, end_at):
            raise BusinessRuleError("lesson_overlap", "В это время уже есть урок")

        lesson = await self.lessons.create(
            subject_id=subject_id,
            teacher_id=teacher_id,
            start_at=start_at,
            end_at=end_at,
            video_url_override=video_url_override,
            board_url_override=board_url_override,
            topic=topic,
            status=LessonStatus.SCHEDULED,
        )

        for student_id in student_ids:
            student = await self.users.get(student_id)
            if not student or student.role != UserRole.STUDENT:
                raise NotFoundError("Student", student_id)
            await self.participants.create(
                lesson_id=lesson.id,
                student_id=student_id,
                attendance=AttendanceStatus.PENDING,
                is_billable=False,
            )

        await self.audit.log(
            action="lesson.created",
            entity_type="lesson",
            entity_id=lesson.id,
            data={"subject_id": subject_id, "teacher_id": teacher_id, "start_at": start_at.isoformat()},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return lesson

    async def reschedule_lesson(
        self,
        actor: User,
        lesson_id: int,
        new_start_at: datetime,
        new_end_at: datetime,
    ) -> Lesson:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("reschedule_lesson")

        lesson = await self.lessons.get(lesson_id)
        if not lesson:
            raise NotFoundError("Lesson", lesson_id)

        # Check overlap
        if await self.lessons.check_teacher_overlap(lesson.teacher_id, new_start_at, new_end_at, exclude_id=lesson_id):
            raise BusinessRuleError("lesson_overlap", "В это время уже есть урок")

        old_start = lesson.start_at
        old_end = lesson.end_at
        lesson.start_at = new_start_at
        lesson.end_at = new_end_at
        lesson.is_detached = True

        await self.audit.log(
            action="lesson.rescheduled",
            entity_type="lesson",
            entity_id=lesson_id,
            data={
                "old_start_at": old_start.isoformat(),
                "old_end_at": old_end.isoformat(),
                "new_start_at": new_start_at.isoformat(),
                "new_end_at": new_end_at.isoformat(),
            },
            actor_user_id=actor.id,
        )
        # TODO: Create notifications for participants
        await self.session.commit()
        return lesson

    async def cancel_lesson(
        self,
        actor: User,
        lesson_id: int,
        reason: str,
        billable_student_ids: list[int],
    ) -> Lesson:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("cancel_lesson")

        lesson = await self.lessons.get(lesson_id)
        if not lesson:
            raise NotFoundError("Lesson", lesson_id)

        lesson.status = LessonStatus.CANCELLED
        lesson.cancelled_at = utc_now()
        lesson.cancelled_by = actor.id
        lesson.cancel_reason = reason

        for participant in lesson.participants:
            participant.attendance = AttendanceStatus.CANCELLED
            participant.is_billable = participant.student_id in billable_student_ids

        await self.audit.log(
            action="lesson.cancelled",
            entity_type="lesson",
            entity_id=lesson_id,
            data={"reason": reason, "billable_student_ids": billable_student_ids},
            actor_user_id=actor.id,
        )
        # TODO: Create notifications
        await self.session.commit()
        return lesson

    async def complete_lesson(
        self,
        actor: User,
        lesson_id: int,
        attendances: list[dict],  # [{student_id, attendance, is_billable}]
    ) -> Lesson:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("complete_lesson")

        lesson = await self.lessons.get(lesson_id)
        if not lesson:
            raise NotFoundError("Lesson", lesson_id)

        lesson.status = LessonStatus.COMPLETED
        lesson.completed_at = utc_now()

        # Get student profiles for price snapshots
        from src.repositories.user import StudentProfileRepository
        profiles = StudentProfileRepository(self.session)

        for att in attendances:
            student_id = att["student_id"]
            participant = await self.participants.get_for_student_lesson(student_id, lesson_id)
            if not participant:
                continue
            participant.attendance = AttendanceStatus(att["attendance"])
            participant.is_billable = att.get("is_billable", False)

            if participant.is_billable:
                profile = await profiles.get(student_id)
                if profile:
                    participant.price_snapshot = profile.lesson_price

        await self.audit.log(
            action="lesson.completed",
            entity_type="lesson",
            entity_id=lesson_id,
            data={"attendances": attendances},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return lesson

    async def create_template(
        self,
        actor: User,
        teacher_id: int,
        subject_id: int,
        weekday: int,
        start_local_time: str,  # HH:MM
        duration_minutes: int,
        timezone: str,
        starts_on: datetime,
        ends_on: Optional[datetime],
        student_ids: list[int],
    ) -> ScheduleTemplate:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_template")

        template = await self.templates.create(
            teacher_id=teacher_id,
            subject_id=subject_id,
            weekday=weekday,
            start_local_time=start_local_time,
            duration_minutes=duration_minutes,
            timezone=timezone,
            starts_on=starts_on.date(),
            ends_on=ends_on.date() if ends_on else None,
        )

        for student_id in student_ids:
            student = await self.users.get(student_id)
            if not student or student.role != UserRole.STUDENT:
                raise NotFoundError("Student", student_id)
            await self.session.execute(
                ScheduleTemplateParticipant.__table__.insert().values(template_id=template.id, student_id=student_id)
            )

        await self.session.commit()
        return template

    async def generate_lessons(self, horizon_weeks: int = 4) -> int:
        """Generate lessons from active templates. Returns count created."""
        from src.core.config import settings
        templates = await self.templates.get_active_for_teacher(0)  # Get all active templates
        # Actually we need all active templates regardless of teacher
        stmt = select(ScheduleTemplate).where(ScheduleTemplate.is_active == True)
        result = await self.session.execute(stmt)
        templates = list(result.scalars().all())

        created = 0
        until = utc_now() + timedelta(weeks=horizon_weeks)

        for template in templates:
            # Generate occurrences
            current = template.starts_on
            template_tz = ZoneInfo(template.timezone)

            while current <= (template.ends_on or until.date()) and current <= until.date():
                if current.weekday() + 1 == template.weekday:  # ISO weekday 1-7
                    # Parse local time
                    hour, minute = map(int, template.start_local_time.split(":"))
                    local_dt = datetime.combine(current, time(hour, minute), tzinfo=template_tz)
                    start_at = local_dt.astimezone(ZoneInfo("UTC"))
                    end_at = start_at + timedelta(minutes=template.duration_minutes)

                    # Check if already exists (idempotency)
                    existing = await self.lessons.get_by_template_and_start(template.id, start_at)
                    if not existing:
                        lesson = await self.lessons.create(
                            subject_id=template.subject_id,
                            teacher_id=template.teacher_id,
                            start_at=start_at,
                            end_at=end_at,
                            template_id=template.id,
                            status=LessonStatus.SCHEDULED,
                        )
                        # Add participants
                        stmt = select(ScheduleTemplateParticipant).where(
                            ScheduleTemplateParticipant.template_id == template.id
                        )
                        result = await self.session.execute(stmt)
                        participants = result.scalars().all()
                        for p in participants:
                            await self.participants.create(
                                lesson_id=lesson.id,
                                student_id=p.student_id,
                                attendance=AttendanceStatus.PENDING,
                                is_billable=False,
                            )
                        created += 1

                current += timedelta(days=1)

            template.generated_until = min(until.date(), template.ends_on or until.date())

        await self.session.commit()
        return created