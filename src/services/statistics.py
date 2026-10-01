"""Сервис статистики и дашборда (docs/01_project_overview.md, п.4.2)."""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional
from fractions import Fraction

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import HomeworkStatusEnum, Lesson, LessonStatusEnum, RoleEnum, User, utcnow
from src.repositories import (
    HomeworkRepository,
    LessonRepository,
    MockExamRepository,
    UserRepository,
)


@dataclass
class StudentProgress:
    """Сводка по ученику для отчётов."""

    student_id: int
    login: str
    balance: int
    lessons_completed: int
    homeworks_total: int
    homeworks_pending: int
    mock_exams_avg_grade: Optional[float]
    debtors_flag: bool


@dataclass
class DashboardSummary:
    """Главный дашборд администратора за один день."""

    date: str
    today_lessons: list[Lesson] = field(default_factory=list)
    # Уроки сегодня, к которым есть несданное ДЗ (ученик -> список уроков)
    students_without_homework: list[int] = field(default_factory=list)
    debtors: list[int] = field(default_factory=list)
    cancelled_count: int = 0
    earned_period: int = 0


class StatisticsService:
    def __init__(self) -> None:
        self.lesson_repo = LessonRepository()
        self.hw_repo = HomeworkRepository()
        self.exam_repo = MockExamRepository()
        self.user_repo = UserRepository()

    async def get_dashboard(
        self,
        session: AsyncSession,
        now: Optional[datetime] = None,
    ) -> DashboardSummary:
        """Расписание на сегодня + несданные ДЗ к сегодняшним урокам + должники."""
        now = now or utcnow()
        day_start = datetime.combine(now.date(), time.min)
        day_end = day_start + timedelta(days=1)

        lessons = await self.lesson_repo.get_in_period(session, day_start, day_end)
        today_lessons = [l for l in lessons if l.status == LessonStatusEnum.scheduled]

        no_hw_students: set[int] = set()
        lesson_ids = [l.id for l in today_lessons]
        hws = await self.hw_repo.get_by_lesson_ids(session, lesson_ids)
        pending_by_lesson = {
            h.lesson_id for h in hws if h.status == HomeworkStatusEnum.pending
        }
        lesson_by_id = {l.id: l for l in today_lessons}
        for lid in pending_by_lesson:
            lesson = lesson_by_id.get(lid)
            if lesson:
                no_hw_students.add(lesson.student_id)

        students = await self.user_repo.get_all_students(session)
        debtors = [s.id for s in students if s.balance <= 0]

        cancelled = await self.lesson_repo.count_cancelled_in_period(
            session, day_start, day_end
        )

        return DashboardSummary(
            date=now.date().isoformat(),
            today_lessons=today_lessons,
            students_without_homework=sorted(no_hw_students),
            debtors=debtors,
            cancelled_count=cancelled,
        )

    async def get_student_progress(
        self,
        session: AsyncSession,
        student: User,
    ) -> StudentProgress:
        """Прогресс одного ученика: уроки, ДЗ, средний балл пробников."""
        lessons = await self.lesson_repo.get_student_lessons(session, student.id)
        completed = sum(1 for l in lessons if l.status == LessonStatusEnum.completed)

        hws = await self.hw_repo.get_by_lesson_ids(
            session, [l.id for l in lessons]
        )
        pending = sum(1 for h in hws if h.status == HomeworkStatusEnum.pending)

        exams = await self.exam_repo.get_student_exams(session, student.id)
        avg_grade = (
            round(sum(e.grade for e in exams) / len(exams), 2) if exams else None
        )

        return StudentProgress(
            student_id=student.id,
            login=student.login,
            balance=student.balance,
            lessons_completed=completed,
            homeworks_total=len(hws),
            homeworks_pending=pending,
            mock_exams_avg_grade=avg_grade,
            debtors_flag=student.balance <= 0,
        )

    async def get_all_progress(self, session: AsyncSession) -> list[StudentProgress]:
        """Сводная статистика по всем ученикам."""
        students = await self.user_repo.get_all_students(session)
        return [await self.get_student_progress(session, s) for s in students]

    async def get_earnings(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
    ) -> int:
        """Заработок за период: сумма lesson_price проведённых уроков."""
        lessons = await self.lesson_repo.get_in_period(
            session, start, end, status=LessonStatusEnum.completed
        )
        total = 0
        for lesson in lessons:
            student = await self.user_repo.get_by_id(session, lesson.student_id)
            if student:
                total += student.lesson_price
        return total
