"""Бизнес-логика домашних заданий: выдача, сдача, оценка."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import (
    Homework,
    HomeworkStatusEnum,
    Lesson,
    LessonStatusEnum,
    RoleEnum,
)
from src.repositories import HomeworkRepository, LessonRepository, UserRepository

logger = logging.getLogger(__name__)


class HomeworkService:
    def __init__(self) -> None:
        self.hw_repo = HomeworkRepository()
        self.lesson_repo = LessonRepository()
        self.user_repo = UserRepository()

    async def assign_homework(
        self,
        session: AsyncSession,
        lesson_id: int,
        description: str,
        deadline: datetime,
    ) -> Homework:
        """Выдать ДЗ к уроку (только несуществующий/непроведённый урок)."""
        lesson = await self.lesson_repo.get_by_id(session, lesson_id)
        if not lesson:
            raise NotFoundError(f"Урок {lesson_id} не найден")
        if lesson.status == LessonStatusEnum.cancelled:
            raise ValidationError("Нельзя выдать ДЗ к отменённому уроку")

        hw = await self.hw_repo.create(
            session=session,
            lesson_id=lesson_id,
            description=description,
            deadline=deadline,
            status=HomeworkStatusEnum.pending,
        )
        logger.info("Homework %s assigned to lesson %s", hw.id, lesson_id)
        return hw

    async def submit_homework(
        self,
        session: AsyncSession,
        homework_id: int,
        student_id: int,
        file_url: Optional[str] = None,
    ) -> Homework:
        """
        Ученик сдаёт ДЗ: pending/submitted -> submitted.

        Файл необязателен — задания устно/на Stepik сдаются кнопкой «Сделал».
        """
        hw = await self._get_hw_for_student(session, homework_id, student_id)

        if hw.status == HomeworkStatusEnum.graded:
            raise ValidationError("Задание уже проверено")

        values: dict = {"status": HomeworkStatusEnum.submitted}
        if file_url:
            values["student_file_url"] = file_url

        updated = await self.hw_repo.update(session, homework_id, **values)
        assert updated is not None
        return updated

    async def grade_homework(
        self,
        session: AsyncSession,
        homework_id: int,
        score: str,
    ) -> Homework:
        """Админ ставит оценку (строка вида '26/27' или 'Зачёт')."""
        hw = await self.hw_repo.get_by_id(session, homework_id)
        if not hw:
            raise NotFoundError(f"ДЗ {homework_id} не найдено")
        if hw.status == HomeworkStatusEnum.pending:
            raise ValidationError("Ученик ещё не сдал задание")
        if not score.strip():
            raise ValidationError("Оценка не может быть пустой")

        updated = await self.hw_repo.update(
            session, homework_id, score=score.strip(), status=HomeworkStatusEnum.graded
        )
        assert updated is not None
        return updated

    async def get_student_homeworks(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[Homework]:
        """Все ДЗ ученика без N+1.

        Реализация — ОДИН SQL-запрос (JOIN lessons), а не «список id уроков +
        IN(...)»: раньше это было 2 запроса, а в эндпоинте /students/{id}/homeworks
        — полноценный N+1 (запрос на каждый урок).

        Дополнительно проверяется существование ученика с ролью student:
        иначе GET /students/{несуществующий}/homeworks возвращал бы 200 [],
        хотя по REST-семантике здесь обязано быть 404 (как в /schedule и
        /balance). Ученик подтягивается тем же запросом, что и ДЗ (JOIN users),
        поэтому общее число SELECT не растёт — N+1 по-прежнему нет.
        """
        pairs = await self.hw_repo.get_for_student_with_user(session, student_id)
        if pairs is None:
            raise NotFoundError(f"Ученик {student_id} не найден")
        return [hw for hw, _user in pairs]

    async def get_student_homeworks_with_lessons(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[tuple[Homework, Optional[Lesson]]]:
        """ДЗ ученика + родительские уроки ОДНИМ запросом (eager load).

        Для эндпоинтов, которым нужен student_id из урока: без этого списка
        вызывающий код делает по одному запросу на каждое ДЗ (N+1).
        """
        stmt = (
            select(Homework, Lesson)
            .join(Lesson, Homework.lesson_id == Lesson.id)
            .where(Lesson.student_id == student_id)
            .order_by(Homework.deadline)
        )
        result = await session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_overdue_for_lesson(
        self,
        session: AsyncSession,
        lesson: Lesson,
    ) -> list[Homework]:
        """Несданные ДЗ по уроку (для дашборда: кто не сделал к сегодняшнему уроку)."""
        hws = await self.hw_repo.get_by_lesson_id(session, lesson.id)
        return [h for h in hws if h.status == HomeworkStatusEnum.pending]

    async def _get_hw_for_student(
        self,
        session: AsyncSession,
        homework_id: int,
        student_id: int,
    ) -> Homework:
        hw = await self.hw_repo.get_by_id(session, homework_id)
        if not hw:
            raise NotFoundError(f"ДЗ {homework_id} не найдено")
        lesson = await self.lesson_repo.get_by_id(session, hw.lesson_id)
        if not lesson or lesson.student_id != student_id:
            raise PermissionError("Задание принадлежит другому ученику")
        return hw
