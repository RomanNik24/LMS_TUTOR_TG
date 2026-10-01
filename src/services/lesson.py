"""Бизнес-логика уроков: создание/перенос/отмена, проведение со списанием баланса."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.db.models import Lesson, LessonStatusEnum, RoleEnum, User, utcnow
from src.repositories import LessonRepository, UserRepository

logger = logging.getLogger(__name__)


class LessonService:
    def __init__(self) -> None:
        self.lesson_repo = LessonRepository()
        self.user_repo = UserRepository()

    @staticmethod
    def _validate_times(start_time: datetime, end_time: datetime) -> None:
        """Проверка корректности временного окна урока."""
        if end_time <= start_time:
            raise ValidationError("Время окончания урока должно быть позже начала")

    async def _get_student(self, session: AsyncSession, student_id: int) -> User:
        user = await self.user_repo.get_by_id(session, student_id)
        if not user or user.role != RoleEnum.student:
            raise NotFoundError(f"Ученик {student_id} не найден")
        return user

    async def create_lesson(
        self,
        session: AsyncSession,
        student_id: int,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        video_url: Optional[str] = None,
        board_url: Optional[str] = None,
    ) -> Lesson:
        """Создать урок с проверкой времени и пересечения слотов."""
        await self._get_student(session, student_id)
        self._validate_times(start_time, end_time)

        if await self.lesson_repo.has_overlap(
            session, student_id, start_time, end_time
        ):
            raise ConflictError("У ученика уже есть урок в это время")

        lesson = await self.lesson_repo.create(
            session=session,
            student_id=student_id,
            subject=subject,
            start_time=start_time,
            end_time=end_time,
            status=LessonStatusEnum.scheduled,
            video_url=video_url,
            board_url=board_url,
        )
        logger.info("Lesson %s created for student %s", lesson.id, student_id)
        return lesson

    async def update_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
        *,
        subject: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        video_url: Optional[str] = None,
        board_url: Optional[str] = None,
    ) -> Lesson:
        """Перенос/редактирование урока (только для scheduled)."""
        lesson = await self.lesson_repo.get_by_id(session, lesson_id)
        if not lesson:
            raise NotFoundError(f"Урок {lesson_id} не найден")
        if lesson.status != LessonStatusEnum.scheduled:
            raise ValidationError("Изменять можно только запланированные уроки")

        new_start = start_time or lesson.start_time
        new_end = end_time or lesson.end_time
        self._validate_times(new_start, new_end)

        if (new_start != lesson.start_time or new_end != lesson.end_time) and (
            await self.lesson_repo.has_overlap(
                session, lesson.student_id, new_start, new_end, exclude_id=lesson_id
            )
        ):
            raise ConflictError("У ученика уже есть урок в новое время")

        values: dict = {}
        if subject is not None:
            values["subject"] = subject
        if start_time is not None:
            values["start_time"] = start_time
        if end_time is not None:
            values["end_time"] = end_time
        if video_url is not None:
            values["video_url"] = video_url
        if board_url is not None:
            values["board_url"] = board_url

        updated = await self.lesson_repo.update(session, lesson_id, **values)
        assert updated is not None
        return updated

    async def cancel_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
    ) -> Lesson:
        """Отменить урок (scheduled/needs_confirmation -> cancelled; баланс не списывается)."""
        lesson = await self.lesson_repo.get_by_id(session, lesson_id)
        if not lesson:
            raise NotFoundError(f"Урок {lesson_id} не найден")
        if lesson.status == LessonStatusEnum.completed:
            raise ValidationError("Проведённый урок нельзя отменить")
        updated = await self.lesson_repo.update(
            session, lesson_id, status=LessonStatusEnum.cancelled
        )
        assert updated is not None
        return updated

    async def complete_lesson(
        self,
        session: AsyncSession,
        lesson_id: int,
    ) -> Lesson:
        """
        Провести урок: status -> completed и списать 1 занятие с баланса.

        Вызывается преподавателем вручную (POST /lessons/{id}/complete), в том
        числе для подтверждения урока в статусе needs_confirmation после
        автозакрытия воркером. Баланс списывается ТОЛЬКО здесь — на этапе
        подтверждения факта проведения (docs/01, п.4.2).

        Баланс может уйти в минус — это сигнал «должника» для дашборда
        (docs/01, п.4.2: приём платежей вне системы, учёт вручную).

        Гонки исключены на уровне СУБД:
        - статус меняется условным UPDATE ... WHERE status IN
          ('scheduled','needs_confirmation') (mark_completed_atomic) — при
          параллельном ручном /complete и подтверждении из воркера ровно один
          вызов считает урок завершённым;
        - баланс меняется атомарно UPDATE ... SET balance = balance - 1
          (atomic_adjust_balance), без read-modify-write.
        Оба запроса выполняются в одной транзакции сессии.
        """
        lesson = await self.lesson_repo.get_by_id(session, lesson_id)
        if not lesson:
            raise NotFoundError(f"Урок {lesson_id} не найден")
        if lesson.status == LessonStatusEnum.cancelled:
            raise ValidationError("Отменённый урок нельзя провести")

        # Атомарный переход scheduled|needs_confirmation -> completed.
        # None => урок уже завершён конкурентным вызовом (или изменился статус).
        updated = await self.lesson_repo.mark_completed_atomic(session, lesson_id)
        if updated is None:
            raise ValidationError("Урок уже проведён")

        new_balance = await self.user_repo.atomic_adjust_balance(
            session, lesson.student_id, -1
        )
        if new_balance is None:
            raise NotFoundError("Ученик урока не найден")

        logger.info(
            "Lesson %s completed, balance of student %s set to %d",
            lesson_id,
            lesson.student_id,
            new_balance,
        )
        return updated

    async def process_finished_lessons(
        self,
        session: AsyncSession,
        now: Optional[datetime] = None,
    ) -> list[Lesson]:
        """Автозакрытие завершившихся уроков БЕЗ списания баланса (воркер).

        Урок scheduled -> needs_confirmation: деньги НЕ списываются, пока
        преподаватель явно не подтвердит проведение (POST /{id}/complete) или
        не отменит урок (если занятие не состоялось). Возвращает список
        уроков, переведённых в needs_confirmation в этом проходе.
        """
        now = now or utcnow()
        lessons = await self.lesson_repo.get_finished_scheduled_until(session, now)
        closed: list[Lesson] = []
        for lesson in lessons:
            marked = await self.lesson_repo.mark_needs_confirmation_atomic(
                session, lesson.id
            )
            if marked is not None:
                closed.append(marked)
        return closed
