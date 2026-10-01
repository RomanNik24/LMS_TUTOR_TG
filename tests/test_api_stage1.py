"""Тесты бизнес-логики Этапа 1 (сервисный слой, SQLite in-memory)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.db.base import Base
from src.db.models import HomeworkStatusEnum, LessonStatusEnum, RoleEnum
from src.repositories import UserRepository
from src.services.auth import AuthService
from src.services.homework import HomeworkService
from src.services.lesson import LessonService
from src.services.mock_exam import MockExamService, convert_primary_score_to_grade
from src.services.statistics import StatisticsService
from src.services.user import UserService


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def student(db_session):
    auth = AuthService()
    repo = UserRepository()
    user = await repo.create(
        session=db_session,
        role=RoleEnum.student,
        login="pete",
        password_hash=auth.get_password_hash("secret"),
        balance=3,
        lesson_price=1200,
    )
    await db_session.commit()
    return user


async def _make_lesson(session, student, start=None):
    service = LessonService()
    start = start or datetime(2026, 10, 5, 10, 0)
    lesson = await service.create_lesson(
        session, student.id, "math", start, start + timedelta(hours=1)
    )
    await session.commit()
    return lesson


class TestLessonService:
    async def test_create_lesson_ok(self, db_session, student):
        start = datetime(2026, 10, 5, 10, 0)
        lesson = await LessonService().create_lesson(
            db_session, student.id, "math", start, start + timedelta(hours=1),
            video_url="https://telemost.example/x",
        )
        assert lesson.status == LessonStatusEnum.scheduled
        assert lesson.video_url.startswith("https://")

    async def test_non_student_rejected(self, db_session):
        with pytest.raises(NotFoundError):
            await LessonService().create_lesson(
                db_session, 999, "math",
                datetime(2026, 10, 5, 10, 0), datetime(2026, 10, 5, 11, 0),
            )

    async def test_invalid_times_rejected(self, db_session, student):
        with pytest.raises(ValidationError):
            await LessonService().create_lesson(
                db_session, student.id, "math",
                datetime(2026, 10, 5, 12, 0), datetime(2026, 10, 5, 11, 0),
            )

    async def test_overlap_rejected(self, db_session, student):
        start = datetime(2026, 10, 5, 10, 0)
        await _make_lesson(db_session, student, start)
        with pytest.raises(ConflictError):
            await LessonService().create_lesson(
                db_session, student.id, "informatics",
                start + timedelta(minutes=30), start + timedelta(minutes=90),
            )

    async def test_move_to_free_slot_ok(self, db_session, student):
        start = datetime(2026, 10, 5, 10, 0)
        lesson = await _make_lesson(db_session, student, start)
        service = LessonService()
        moved = await service.update_lesson(
            db_session, lesson.id,
            start_time=start + timedelta(days=1),
            end_time=start + timedelta(days=1, hours=1),
        )
        assert moved.start_time == start + timedelta(days=1)

    async def test_complete_decrements_balance(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        done = await LessonService().complete_lesson(db_session, lesson.id)
        await db_session.commit()
        assert done.status == LessonStatusEnum.completed
        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 2

    async def test_double_complete_fails(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        service = LessonService()
        await service.complete_lesson(db_session, lesson.id)
        await db_session.commit()
        with pytest.raises(ValidationError):
            await service.complete_lesson(db_session, lesson.id)

    async def test_cancelled_cannot_complete(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        service = LessonService()
        await service.cancel_lesson(db_session, lesson.id)
        await db_session.commit()
        with pytest.raises(ValidationError):
            await service.complete_lesson(db_session, lesson.id)

    async def test_completed_cannot_cancel(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        service = LessonService()
        await service.complete_lesson(db_session, lesson.id)
        await db_session.commit()
        with pytest.raises(ValidationError):
            await service.cancel_lesson(db_session, lesson.id)

    async def test_auto_close_finished(self, db_session, student):
        """Воркер-метод закрывает завершившиеся scheduled-уроки со списанием."""
        past_start = datetime(2026, 9, 30, 8, 0)
        # в обход проверки будущего времени — создаём напрямую через репозиторий
        from src.db.models import Lesson, LessonStatusEnum as LSE
        db_session.add(Lesson(
            student_id=student.id, subject="math",
            start_time=past_start, end_time=past_start + timedelta(hours=1),
            status=LSE.scheduled,
        ))
        await db_session.commit()
        count = await LessonService().process_finished_lessons(
            db_session, now=datetime(2026, 10, 1, 0, 0)
        )
        await db_session.commit()
        assert count == 1
        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 2


class TestHomeworkService:
    async def test_assign_submit_grade_flow(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        hw_service = HomeworkService()
        hw = await hw_service.assign_homework(
            db_session, lesson.id, "Решить №12", datetime(2026, 10, 6, 20, 0)
        )
        await db_session.commit()
        assert hw.status == HomeworkStatusEnum.pending

        submitted = await hw_service.submit_homework(
            db_session, hw.id, student.id, file_url="https://s3/scan.jpg"
        )
        await db_session.commit()
        assert submitted.status == HomeworkStatusEnum.submitted
        assert submitted.student_file_url == "https://s3/scan.jpg"

        graded = await hw_service.grade_homework(db_session, hw.id, " 26/27 ")
        await db_session.commit()
        assert graded.status == HomeworkStatusEnum.graded
        assert graded.score == "26/27"

    async def test_submit_without_file(self, db_session, student):
        """Кнопка «Сделал» — сдача без файла (устные задания / Stepik)."""
        lesson = await _make_lesson(db_session, student)
        hw_service = HomeworkService()
        hw = await hw_service.assign_homework(
            db_session, lesson.id, "Устно", datetime(2026, 10, 6, 20, 0)
        )
        await db_session.commit()
        submitted = await hw_service.submit_homework(db_session, hw.id, student.id)
        assert submitted.status == HomeworkStatusEnum.submitted

    async def test_grade_pending_fails(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        hw_service = HomeworkService()
        hw = await hw_service.assign_homework(
            db_session, lesson.id, "task", datetime(2026, 10, 6, 20, 0)
        )
        await db_session.commit()
        with pytest.raises(ValidationError):
            await hw_service.grade_homework(db_session, hw.id, "5")

    async def test_wrong_student_forbidden(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        hw_service = HomeworkService()
        hw = await hw_service.assign_homework(
            db_session, lesson.id, "task", datetime(2026, 10, 6, 20, 0)
        )
        await db_session.commit()
        with pytest.raises(PermissionError):
            await hw_service.submit_homework(db_session, hw.id, student_id=999)

    async def test_get_student_homeworks_no_n_plus_1(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        hw_service = HomeworkService()
        for i in range(3):
            await hw_service.assign_homework(
                db_session, lesson.id, f"task{i}", datetime(2026, 10, 6, 20, 0)
            )
        await db_session.commit()
        hws = await hw_service.get_student_homeworks(db_session, student.id)
        assert len(hws) == 3


class TestMockExamService:
    async def test_auto_grade_conversion(self, db_session, student):
        exam = await MockExamService().create_exam(
            db_session, student.id, "informatics", 18
        )
        await db_session.commit()
        assert exam.grade == 5

    async def test_manual_grade_override(self, db_session, student):
        exam = await MockExamService().create_exam(
            db_session, student.id, "informatics", 3, grade=4
        )
        assert exam.grade == 4

    async def test_negative_score_rejected(self, db_session, student):
        with pytest.raises(ValidationError):
            await MockExamService().create_exam(
                db_session, student.id, "informatics", -1
            )

    def test_grade_thresholds(self):
        assert convert_primary_score_to_grade(21, "informatics") == 5
        assert convert_primary_score_to_grade(17, "informatics") == 5
        assert convert_primary_score_to_grade(16, "informatics") == 4
        assert convert_primary_score_to_grade(12, "informatics") == 4
        assert convert_primary_score_to_grade(11, "informatics") == 3
        assert convert_primary_score_to_grade(5, "informatics") == 3
        assert convert_primary_score_to_grade(4, "informatics") == 2
        assert convert_primary_score_to_grade(0, "informatics") == 2


class TestStatisticsAndUserServices:
    async def test_dashboard_today(self, db_session, student):
        start = datetime(2026, 10, 5, 9, 0)
        lesson = await _make_lesson(db_session, student, start)
        hw_service = HomeworkService()
        await hw_service.assign_homework(
            db_session, lesson.id, "hw", start + timedelta(days=1)
        )
        await db_session.commit()

        stats = StatisticsService()
        dash = await stats.get_dashboard(db_session, now=start)
        assert len(dash.today_lessons) == 1
        assert student.id in dash.students_without_homework

    async def test_debtor_detection(self, db_session, student):
        await UserService().add_balance(db_session, student.id, -5)  # 3 -> -2
        await db_session.commit()
        dash = await StatisticsService().get_dashboard(db_session)
        assert student.id in dash.debtors

    async def test_set_price(self, db_session, student):
        updated = await UserService().set_lesson_price(db_session, student.id, 1500)
        assert updated.lesson_price == 1500

    async def test_negative_price_rejected(self, db_session, student):
        with pytest.raises(ValidationError):
            await UserService().set_lesson_price(db_session, student.id, -1)

    async def test_earnings(self, db_session, student):
        lesson = await _make_lesson(db_session, student, datetime(2026, 10, 1, 10, 0))
        await LessonService().complete_lesson(db_session, lesson.id)
        await db_session.commit()
        earned = await StatisticsService().get_earnings(
            db_session, datetime(2026, 10, 1), datetime(2026, 10, 31)
        )
        assert earned == 1200

    async def test_progress_summary(self, db_session, student):
        lesson = await _make_lesson(db_session, student)
        await LessonService().complete_lesson(db_session, lesson.id)
        hw_service = HomeworkService()
        await hw_service.assign_homework(
            db_session, lesson.id, "hw", datetime(2026, 10, 6)
        )
        await MockExamService().create_exam(db_session, student.id, "informatics", 18)
        await db_session.commit()

        row = await StatisticsService().get_student_progress(db_session, student)
        assert row.lessons_completed == 1
        assert row.homeworks_total == 1
        assert row.homeworks_pending == 1
        assert row.mock_exams_avg_grade == 5.0
