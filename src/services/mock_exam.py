"""Бизнес-логика пробных экзаменов: ввод результатов и авто-конвертация баллов.

Пороги конвертации первичного балла в отметку по 5-балльной шкале —
согласно docs/04_database_schema.md (пример ОГЭ по информатике).
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import MockExam, RoleEnum
from src.repositories import MockExamRepository, UserRepository

logger = logging.getLogger(__name__)

# Пороги: subject -> список (мин_первичный_балл, отметка) по убыванию отметки
GRADE_THRESHOLDS: dict[str, list[tuple[int, int]]] = {
    "informatics": [(17, 5), (12, 4), (5, 3), (0, 2)],
    # Математика (ОГЭ): ориентировочные пороги, админ может переотменить grade
    "math": [(24, 5), (16, 4), (8, 3), (0, 2)],
}
DEFAULT_THRESHOLDS: list[tuple[int, int]] = [(17, 5), (12, 4), (5, 3), (0, 2)]


def convert_primary_score_to_grade(
    primary_score: int,
    subject: str,
) -> int:
    """Конвертировать первичный балл в отметку 2..5 по порогам предмета."""
    thresholds = GRADE_THRESHOLDS.get(subject.lower(), DEFAULT_THRESHOLDS)
    for min_score, grade in thresholds:
        if primary_score >= min_score:
            return grade
    return 2


class MockExamService:
    def __init__(self) -> None:
        self.exam_repo = MockExamRepository()
        self.user_repo = UserRepository()

    async def create_exam(
        self,
        session: AsyncSession,
        student_id: int,
        subject: str,
        primary_score: int,
        exam_date: Optional[date] = None,
        grade: Optional[int] = None,
    ) -> MockExam:
        """Зафиксировать результат пробника; grade считается автоматически."""
        student = await self.user_repo.get_by_id(session, student_id)
        if not student or student.role != RoleEnum.student:
            raise NotFoundError(f"Ученик {student_id} не найден")
        if primary_score < 0:
            raise ValidationError("Первичный балл не может быть отрицательным")

        resolved_grade = grade if grade is not None else convert_primary_score_to_grade(
            primary_score, subject
        )
        if not 2 <= resolved_grade <= 5:
            raise ValidationError("Отметка должна быть в диапазоне 2..5")

        exam = await self.exam_repo.create(
            session=session,
            student_id=student_id,
            subject=subject,
            date=exam_date or date.today(),
            primary_score=primary_score,
            grade=resolved_grade,
        )
        logger.info(
            "MockExam %s recorded for student %s: %d -> %d",
            exam.id,
            student_id,
            primary_score,
            resolved_grade,
        )
        return exam

    async def get_student_exams(
        self,
        session: AsyncSession,
        student_id: int,
    ) -> list[MockExam]:
        exams = await self.exam_repo.get_student_exams(session, student_id)
        if not exams:
            user = await self.user_repo.get_by_id(session, student_id)
            if not user or user.role != RoleEnum.student:
                raise NotFoundError(f"Ученик {student_id} не найден")
        return exams
