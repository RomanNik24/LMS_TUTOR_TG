"""Stats service: dashboard, earnings, reports."""

from datetime import datetime, timedelta
from typing: Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.schedule import LessonRepository, LessonParticipantRepository
from src.repositories.homework import HomeworkAssignmentRepository
from src.repositories.user import UserRepository
from src.repositories.exam import MockExamResultRepository
from src.core.enums import UserRole, LessonStatus, HomeworkStatus
from src.db.models.schedule import Lesson, LessonParticipant
from src.db.models.homework import HomeworkAssignment
from src.db.models.exam import MockExamResult
from src.db.models.users import User
from src.core.timeutils import utc_now, start_of_day, end_of_day, local_date_str


class StatsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.lessons = LessonRepository(session)
        self.participants = LessonParticipantRepository(session)
        self.assignments = HomeworkAssignmentRepository(session)
        self.users = UserRepository(session)
        self.exam_results = MockExamResultRepository(session)

    async def get_today_dashboard(self, actor: User) -> dict:
        now = utc_now()
        today_start = start_of_day(now, actor.timezone)
        today_end = end_of_day(now, actor.timezone)

        # Lessons today
        if actor.role == UserRole.STUDENT:
            lessons_today = await self.lessons.get_for_student_in_range(actor.id, today_start, today_end)
        else:
            lessons_today = await self.lessons.get_for_teacher_in_range(actor.id, today_start, today_end)

        # Homework review queue (staff)
        review_queue = []
        if actor.role in (UserRole.OWNER, UserRole.MANAGER):
            review_queue = await self.assignments.get_review_queue(actor.id)

        # Students with unsubmitted homework for today's lessons
        not_submitted = []

        # Lessons without attendance marking
        unmarked = []

        # Upcoming deadlines (24h)
        upcoming_deadlines = []

        # Earnings (owner only)
        earned_month = 0
        expected_month = 0
        if actor.role == UserRole.OWNER:
            month_start = start_of_day(now.replace(day=1), actor.timezone)
            # Earned: completed billable lessons this month
            # Expected: scheduled lessons this month at current prices

        return {
            "lessons_today": lessons_today,
            "review_queue": review_queue[:5],
            "review_queue_total": len(review_queue),
            "not_submitted": not_submitted,
            "unmarked_lessons": unmarked,
            "upcoming_deadlines": upcoming_deadlines,
            "earned_month": earned_month,
            "expected_month": expected_month,
        }

    async def get_earnings(
        self,
        actor: User,
        from_dt: datetime,
        to_dt: datetime,
        group_by: str = "week",
    ) -> dict:
        if actor.role != UserRole.OWNER:
            raise PermissionDeniedError("view_finances")

        # Earned: sum of price_snapshot for completed billable lessons
        stmt = select(func.sum(LessonParticipant.price_snapshot)).join(Lesson).where(
            LessonParticipant.is_billable == True,
            LessonParticipant.price_snapshot.is_not(None),
            Lesson.status.in_([LessonStatus.COMPLETED, LessonStatus.CANCELLED]),
            Lesson.start_at >= from_dt,
            Lesson.start_at < to_dt,
        )
        result = await self.session.execute(stmt)
        earned = result.scalar() or 0

        # Expected: sum of current lesson_price for scheduled lessons
        stmt = select(func.sum(StudentProfile.lesson_price)).join(LessonParticipant).join(Lesson).where(
            Lesson.status == LessonStatus.SCHEDULED,
            Lesson.start_at >= from_dt,
            Lesson.start_at < to_dt,
        )
        # Need to join StudentProfile
        # ... simplified for stub

        return {"earned": earned, "expected": 0}

    async def get_student_report(self, actor: User, student_id: int, from_dt: datetime, to_dt: datetime) -> dict:
        """Student progress report: homework %, mock exams, on-time %."""
        if actor.role == UserRole.STUDENT and actor.id != student_id:
            raise PermissionDeniedError("view_report")

        student = await self.users.get(student_id)
        if not student:
            raise NotFoundError("Student", student_id)

        # Homework stats
        assignments = await self.assignments.get_for_student(student_id)
        filtered = [a for a in assignments if from_dt <= (a.graded_at or utc_now()) < to_dt and a.status == HomeworkStatus.GRADED]

        # Weekly average percentage
        weekly_avg = {}

        # Mock exam dynamics
        exam_results = await self.exam_results.get_for_student(student_id)
        filtered_exams = [r for r in exam_results if from_dt <= r.exam_date < to_dt]

        # On-time percentage
        on_time = sum(1 for a in assignments if a.submitted_at and a.submitted_at <= a.original_due_at)
        total_submitted = sum(1 for a in assignments if a.status in (HomeworkStatus.GRADED, HomeworkStatus.EXPIRED))

        return {
            "homework_weekly_avg": weekly_avg,
            "mock_exams": filtered_exams,
            "on_time_percent": (on_time / total_submitted * 100) if total_submitted else 0,
        }