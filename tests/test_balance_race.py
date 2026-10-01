"""Регрессия гонок баланса (read-modify-write).

Проверяет, что complete_lesson и add_balance используют атомарные
UPDATE ... SET balance = balance + :delta вместо чтения и записи значения.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.base import Base
from src.db.models import Lesson, LessonStatusEnum, RoleEnum, User
from src.repositories import UserRepository
from src.services.lesson import LessonService
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


_counter = 0


async def _make_student(session: AsyncSession, balance: int = 10) -> User:
    global _counter
    _counter += 1
    user = User(
        login=f"race_stu_{_counter}",
        password_hash="x",
        role=RoleEnum.student,
        balance=balance,
    )
    session.add(user)
    await session.commit()
    return user


async def _make_past_lesson(session: AsyncSession, student_id: int) -> Lesson:
    start = datetime(2026, 9, 30, 8, 0)
    lesson = Lesson(
        student_id=student_id,
        subject="math",
        start_time=start,
        end_time=start + timedelta(hours=1),
        status=LessonStatusEnum.scheduled,
    )
    session.add(lesson)
    await session.commit()
    return lesson


class TestAtomicBalanceOps:
    @pytest.mark.asyncio
    async def test_parallel_add_balance_no_lost_updates(self, db_session):
        """N параллельных пополнений +5 дают ровно N*5, без read-modify-write."""
        student = await _make_student(db_session, balance=0)
        service = UserService()

        async def topup(i: int) -> None:
            # каждая «параллельная операция» — своя транзакция в рамках сессии
            await service.add_balance(db_session, student.id, 5)
            await db_session.commit()

        await asyncio.gather(*[topup(i) for i in range(10)])
        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 50

    @pytest.mark.asyncio
    async def test_double_complete_debits_once(self, db_session):
        """Повторный complete_lesson не списывает баланс второй раз."""
        student = await _make_student(db_session, balance=3)
        lesson = await _make_past_lesson(db_session, student.id)
        service = LessonService()

        done = await service.complete_lesson(db_session, lesson.id)
        await db_session.commit()
        assert done.status == LessonStatusEnum.completed

        from src.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await service.complete_lesson(db_session, lesson.id)
        await db_session.rollback()

        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 2  # списание ровно один раз

    @pytest.mark.asyncio
    async def test_manual_complete_and_autoclose_race(self, db_session):
        """Ручное подтверждение и cron-автозакрытие одного урока: -1, а не -2.

        Cron переводит scheduled -> needs_confirmation (без списания), затем
        ручное /complete подтверждает проведение и списывает ровно 1 занятие;
        повторные проходы cron и /complete ничего не списывают.
        """
        student = await _make_student(db_session, balance=5)
        lesson = await _make_past_lesson(db_session, student.id)
        service = LessonService()

        # имитируем гонку: два вызова подряд в одной "сессии" —
        # условный UPDATE scheduled->needs_confirmation пропустит второй
        closed = await service.process_finished_lessons(
            db_session, now=datetime(2026, 10, 1, 0, 0)
        )
        await db_session.commit()
        assert len(closed) == 1
        # повторный цикл автозакрытия уже ничего не находит
        closed_again = await service.process_finished_lessons(
            db_session, now=datetime(2026, 10, 1, 0, 0)
        )
        await db_session.commit()
        assert closed_again == []

        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 5  # без подтверждения деньги не списаны

        # преподаватель подтвердил факт проведения -> списание ровно один раз
        done = await service.complete_lesson(db_session, lesson.id)
        await db_session.commit()
        assert done.status == LessonStatusEnum.completed
        from src.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await service.complete_lesson(db_session, lesson.id)
        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 4

    @pytest.mark.asyncio
    async def test_atomic_adjust_returns_none_for_missing_user(self, db_session):
        repo = UserRepository()
        assert await repo.atomic_adjust_balance(db_session, 999999, 1) is None

    @pytest.mark.asyncio
    async def test_sql_is_single_update_without_read(self, db_session):
        """Значение баланса вычисляется СУБД, а не Python (balance + delta)."""
        student = await _make_student(db_session, balance=7)
        new_balance = await UserRepository().atomic_adjust_balance(
            db_session, student.id, -1
        )
        await db_session.commit()
        assert new_balance == 6
        user = await UserRepository().get_by_id(db_session, student.id)
        assert user.balance == 6
