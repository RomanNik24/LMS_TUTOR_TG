"""Тесты Этапа 5 — задачи воркера уведомлений (docs/01 п.5, docs/05 п.4).

Чистые функции-сборщики и асинхронные выборки тестируются на SQLite
in-memory + fakeredis без сети; доставка через aiogram Bot не мокается —
обёртки notify_* проверяются только на уровне импорта/конфигурации Arq.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import (
    Homework,
    HomeworkStatusEnum,
    Lesson,
    LessonStatusEnum,
    RoleEnum,
    User,
    utcnow,
)
from src.repositories import HomeworkRepository, UserRepository
from src.services.lesson import LessonService
from src.worker.tasks import (
    HW_DEADLINE_WINDOW_HOURS,
    LESSON_WINDOW_MINUTES,
    build_homework_reminders,
    build_lesson_reminders,
    collect_homework_reminders,
    collect_lesson_reminders,
    format_lesson_time,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _make_user(session, login="pete", telegram_id=111, role=RoleEnum.student, balance=5):
    user = User(
        login=login,
        role=role,
        password_hash="x",
        telegram_id=telegram_id,
        balance=balance,
    )
    session.add(user)
    await session.commit()
    return user


async def _make_lesson(session, student, start, status=LessonStatusEnum.scheduled):
    lesson = Lesson(
        student_id=student.id,
        subject="math",
        start_time=start,
        end_time=start + timedelta(hours=1),
        status=status,
    )
    session.add(lesson)
    await session.commit()
    return lesson


NOW = datetime(2026, 10, 1, 12, 0)  # naive UTC — как в src/db/models.utcnow()


class TestBuildLessonReminders:
    async def test_lesson_in_window_generates_reminder(self, db_session):
        student = await _make_user(db_session)
        # старт через 45 минут -> попадает в окно [30, 60)
        lesson = await _make_lesson(db_session, student, NOW + timedelta(minutes=45))
        lesson.student = student
        out = build_lesson_reminders([lesson])
        assert len(out) == 1
        tg_id, text = out[0]
        assert tg_id == 111
        assert "Напоминание" in text and "math" in text

    async def test_video_url_included(self, db_session):
        student = await _make_user(db_session)
        lesson = await _make_lesson(db_session, student, NOW + timedelta(minutes=45))
        lesson.video_url = "https://meet.example/abc"
        lesson.student = student
        _, text = build_lesson_reminders([lesson])[0]
        assert "https://meet.example/abc" in text

    async def test_student_without_telegram_skipped(self, db_session):
        student = await _make_user(db_session, telegram_id=None)
        lesson = await _make_lesson(db_session, student, NOW + timedelta(minutes=45))
        lesson.student = student
        assert build_lesson_reminders([lesson]) == []

    def test_format_lesson_time(self):
        assert format_lesson_time(datetime(2026, 10, 5, 9, 30)) == "05.10 09:30"


class TestCollectLessonReminders:
    async def test_window_boundaries(self, db_session):
        """Урок через 45 мин -> напоминание; через 5/90 мин -> нет."""
        s_near = await _make_user(db_session, login="near", telegram_id=1)
        s_too_soon = await _make_user(db_session, login="soon", telegram_id=2)
        s_far = await _make_user(db_session, login="far", telegram_id=3)
        await _make_lesson(db_session, s_near, NOW + timedelta(minutes=45))
        await _make_lesson(db_session, s_too_soon, NOW + timedelta(minutes=5))
        await _make_lesson(db_session, s_far, NOW + timedelta(minutes=90))

        out = await collect_lesson_reminders(db_session, now=NOW)
        ids = {tg for tg, _ in out}
        assert ids == {1}

    async def test_cancelled_lesson_not_reminded(self, db_session):
        s = await _make_user(db_session, telegram_id=7)
        await _make_lesson(
            db_session, s, NOW + timedelta(minutes=45),
            status=LessonStatusEnum.cancelled,
        )
        out = await collect_lesson_reminders(db_session, now=NOW)
        assert out == []

    async def test_no_duplicates_between_windows(self, db_session):
        """Окна [now+30, now+60) при запусках каждые 30 мин покрывают каждый урок один раз."""
        s = await _make_user(db_session, telegram_id=9)
        lesson_start = NOW + timedelta(minutes=50)
        await _make_lesson(db_session, s, lesson_start)
        run1 = await collect_lesson_reminders(db_session, now=NOW)
        run2 = await collect_lesson_reminders(db_session, now=NOW + timedelta(minutes=30))
        assert len(run1) == 1 and len(run2) == 0  # ровно одно попадание


class TestBuildHomeworkReminders:
    async def test_text_contains_description_and_deadline(self, db_session):
        s = await _make_user(db_session)
        lesson = await _make_lesson(db_session, s, NOW)
        hw = Homework(
            lesson_id=lesson.id,
            description="Сделать варианты ЕГЭ, задания 1-10",
            deadline=NOW + timedelta(hours=20),
            status=HomeworkStatusEnum.pending,
        )
        db_session.add(hw)
        await db_session.commit()
        hw.lesson = lesson
        lesson.student = s
        out = build_homework_reminders([hw])
        assert len(out) == 1
        _, text = out[0]
        assert "Дедлайн ДЗ через 24 часа" in text and "ЕГЭ" in text


class TestCollectHomeworkReminders:
    async def test_only_future_pending_in_window(self, db_session):
        s1 = await _make_user(db_session, login="s1", telegram_id=101)
        s2 = await _make_user(db_session, login="s2", telegram_id=102)
        s3 = await _make_user(db_session, login="s3", telegram_id=103)
        l1 = await _make_lesson(db_session, s1, NOW)
        l2 = await _make_lesson(db_session, s2, NOW)
        l3 = await _make_lesson(db_session, s3, NOW)
        # pending, дедлайн через 10 часов -> попадает
        db_session.add(Homework(lesson_id=l1.id, description="ok",
                                deadline=NOW + timedelta(hours=10),
                                status=HomeworkStatusEnum.pending))
        # просроченное -> не напоминаем
        db_session.add(Homework(lesson_id=l2.id, description="late",
                                deadline=NOW - timedelta(hours=1),
                                status=HomeworkStatusEnum.pending))
        # уже сдано -> не напоминаем
        db_session.add(Homework(lesson_id=l3.id, description="done",
                                deadline=NOW + timedelta(hours=10),
                                status=HomeworkStatusEnum.submitted))
        await db_session.commit()

        out = await collect_homework_reminders(db_session, now=NOW)
        ids = {tg for tg, _ in out}
        assert ids == {101}

    async def test_deduplication_via_redis(self, db_session):
        """Повторный вызов с тем же redis не отправляет дубли; новый дедлайн — снова шлёт."""
        import fakeredis.aioredis

        redis = fakeredis.aioredis.FakeRedis()
        s = await _make_user(db_session, telegram_id=201)
        lesson = await _make_lesson(db_session, s, NOW)
        hw = Homework(lesson_id=lesson.id, description="hw",
                      deadline=NOW + timedelta(hours=10),
                      status=HomeworkStatusEnum.pending)
        db_session.add(hw)
        await db_session.commit()

        first = await collect_homework_reminders(db_session, redis=redis, now=NOW)
        second = await collect_homework_reminders(db_session, redis=redis, now=NOW)
        assert len(first) == 1 and second == []

        # перенесли дедлайн -> ключ другой -> напоминание пройдёт заново
        hw.deadline = NOW + timedelta(hours=12)
        await db_session.commit()
        third = await collect_homework_reminders(db_session, redis=redis, now=NOW)
        assert len(third) == 1

    async def test_repo_get_due_before_status_filter(self, db_session):
        repo = HomeworkRepository()
        s = await _make_user(db_session, telegram_id=301)
        lesson = await _make_lesson(db_session, s, NOW)
        db_session.add(Homework(lesson_id=lesson.id, description="p",
                                deadline=NOW + timedelta(hours=5),
                                status=HomeworkStatusEnum.pending))
        db_session.add(Homework(lesson_id=lesson.id, description="g",
                                deadline=NOW + timedelta(hours=5),
                                status=HomeworkStatusEnum.graded))
        await db_session.commit()
        res = await repo.get_due_before(db_session, deadline_until=NOW + timedelta(hours=24))
        assert [h.description for h in res] == ["p"]


class TestAutoCloseIntegration:
    async def test_process_finished_lessons_closes_and_debits(self, db_session):
        """scheduled-урок с прошедшим end_time -> completed, баланс −1 (для обёртки cron)."""
        s = await _make_user(db_session, telegram_id=401, balance=4)
        past = utcnow() - timedelta(hours=3)
        lesson = await _make_lesson(db_session, s, past)

        service = LessonService()
        closed = await service.process_finished_lessons(db_session)
        await db_session.commit()
        assert closed == 1

        fresh_student = await UserRepository().get_by_id(db_session, s.id)
        assert fresh_student.balance == 3
        from src.repositories import LessonRepository
        fresh_lesson = await LessonRepository().get_by_id(db_session, lesson.id)
        assert fresh_lesson.status == LessonStatusEnum.completed

    async def test_upcoming_helpers_return_empty_when_nothing_due(self, db_session):
        out = await collect_lesson_reminders(db_session, now=NOW)
        assert out == []
        out_hw = await collect_homework_reminders(db_session, now=NOW)
        assert out_hw == []


class TestArqConfiguration:
    def test_worker_settings_functions_and_cron(self):
        from src.worker.settings import WorkerSettings

        names = [f.__name__ for f in WorkerSettings.functions]
        assert set(names) == {
            "notify_lesson_starts",
            "notify_homework_deadlines",
            "close_lesson_cycle",
        }
        # три cron-задачи зарегистрированы
        assert len(WorkerSettings.cron_jobs) == 3

    def test_windows_match_docs(self):
        assert LESSON_WINDOW_MINUTES == 30          # напоминание за 30 минут
        assert HW_DEADLINE_WINDOW_HOURS == 24       # дедлайн ДЗ за сутки
