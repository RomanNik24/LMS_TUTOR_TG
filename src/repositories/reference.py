"""Reference-table repositories (subjects, exam types, grade scales).

Модуль-совместимость: часть вызывающего кода (src/api/v1/reference.py,
src/services/student.py) импортирует репозитории справочников из этого модуля.
Факльные реализации ExamType/GradeScale находятся в src.repositories.exam,
SubjectRepository реализован здесь поверх BaseRepository.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.reference import Subject
from src.repositories import BaseRepository
from src.repositories.exam import ExamTypeRepository, GradeScaleRepository

__all__ = ["SubjectRepository", "ExamTypeRepository", "GradeScaleRepository"]


class SubjectRepository(BaseRepository[Subject]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Subject)
