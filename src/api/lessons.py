"""Эндпоинты уроков: CRUD + проведение (списание баланса).

Вся бизнес-логика — в LessonService; роутер только транслирует
исключения сервисов в HTTP-коды (docs/03_architecture.md).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin
from src.api.schemas import (
    CreateLessonRequest,
    LessonResponse,
    UpdateLessonRequest,
)
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.db.models import RoleEnum, User
from src.repositories import UserRepository
from src.services.lesson import LessonService

router = APIRouter(prefix="/lessons", tags=["Lessons"])


def _translate(exc: Exception) -> HTTPException:
    """Трансляция доменных исключений в HTTP."""
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    raise exc


async def _get_lesson_or_404(service: LessonService, session: AsyncSession, lesson_id: int):
    lesson = await service.lesson_repo.get_by_id(session, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Урок не найден")
    return lesson


@router.post("/{student_id}", response_model=LessonResponse, status_code=201)
async def create_lesson(
    student_id: int,
    data: CreateLessonRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> LessonResponse:
    """Создать урок для ученика (админ)."""
    service = LessonService()
    try:
        lesson = await service.create_lesson(
            session=session,
            student_id=student_id,
            subject=data.subject,
            start_time=data.start_time,
            end_time=data.end_time,
            video_url=data.video_url,
            board_url=data.board_url,
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _translate(exc) from exc
    return LessonResponse.model_validate(lesson)


@router.patch("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    data: UpdateLessonRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> LessonResponse:
    """Перенос/редактирование урока (админ)."""
    service = LessonService()
    try:
        lesson = await service.update_lesson(
            session,
            lesson_id,
            subject=data.subject,
            start_time=data.start_time,
            end_time=data.end_time,
            video_url=data.video_url,
            board_url=data.board_url,
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        raise _translate(exc) from exc
    return LessonResponse.model_validate(lesson)


@router.post("/{lesson_id}/cancel", response_model=LessonResponse)
async def cancel_lesson(
    lesson_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> LessonResponse:
    """Отменить урок (баланс не списывается)."""
    service = LessonService()
    try:
        lesson = await service.cancel_lesson(session, lesson_id)
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return LessonResponse.model_validate(lesson)


@router.post("/{lesson_id}/complete", response_model=LessonResponse)
async def complete_lesson(
    lesson_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> LessonResponse:
    """Провести урок: статус completed + списание 1 занятия с баланса."""
    service = LessonService()
    try:
        lesson = await service.complete_lesson(session, lesson_id)
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return LessonResponse.model_validate(lesson)


@router.delete("/{lesson_id}", status_code=204)
async def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Удалить урок вместе с ДЗ (каскад). Проведённые уроки удалять нельзя."""
    service = LessonService()
    lesson = await _get_lesson_or_404(service, session, lesson_id)
    if lesson.status.value == "completed":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Проведённый урок нельзя удалить — используйте отмену только для scheduled",
        )
    await service.lesson_repo.delete(session, lesson_id)
