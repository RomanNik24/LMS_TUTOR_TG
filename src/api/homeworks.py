"""Эндпоинты домашних заданий: выдача, сдача, оценка."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_current_user,
    get_db_session,
    require_admin,
    require_student_or_admin,
)
from src.api.schemas import (
    CreateHomeworkRequest,
    GradeHomeworkRequest,
    HomeworkDetailResponse,
    SubmitHomeworkRequest,
)
from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import Lesson, RoleEnum, User
from src.services.homework import HomeworkService

router = APIRouter(prefix="/homeworks", tags=["Homeworks"])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    raise exc


async def _detail(service: HomeworkService, session: AsyncSession, hw_id: int) -> HomeworkDetailResponse:
    """Собрать DTO с student_id через урок (в модели ДЗ нет student_id)."""
    hw = await service.hw_repo.get_by_id(session, hw_id)
    if not hw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ДЗ не найдено")
    lesson: Lesson = await service.lesson_repo.get_by_id(session, hw.lesson_id)  # type: ignore[assignment]
    return _hw_detail(hw, lesson)


def _hw_detail(hw, lesson: Optional[Lesson]) -> HomeworkDetailResponse:
    """Homework + его урок -> HomeworkDetailResponse (без обращений к БД).

    В модели Homework нет поля student_id — читаем из родительского урока;
    model_validate на ORM-объекте упадёт (missing field), поэтому dict вручную.
    """
    data = {
        "id": hw.id,
        "lesson_id": hw.lesson_id,
        "student_id": lesson.student_id if lesson else 0,
        "description": hw.description,
        "deadline": hw.deadline,
        "status": hw.status.value if hasattr(hw.status, "value") else hw.status,
        "student_file_url": hw.student_file_url,
        "score": hw.score,
    }
    return HomeworkDetailResponse.model_validate(data)


@router.post("/", response_model=HomeworkDetailResponse, status_code=201)
async def assign_homework(
    data: CreateHomeworkRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> HomeworkDetailResponse:
    """Выдать ДЗ к уроку (админ)."""
    service = HomeworkService()
    try:
        hw = await service.assign_homework(
            session=session,
            lesson_id=data.lesson_id,
            description=data.description,
            deadline=data.deadline,
        )
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return await _detail(service, session, hw.id)


@router.post("/{homework_id}/submit", response_model=HomeworkDetailResponse)
async def submit_homework(
    homework_id: int,
    data: SubmitHomeworkRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HomeworkDetailResponse:
    """Ученик сдаёт ДЗ (файл или кнопка «Сделал» без файла)."""
    service = HomeworkService()
    try:
        await service.submit_homework(
            session=session,
            homework_id=homework_id,
            student_id=current_user.id,
            file_url=data.file_url,
        )
    except (NotFoundError, ValidationError, PermissionError) as exc:
        raise _translate(exc) from exc
    return await _detail(service, session, homework_id)


@router.post("/{homework_id}/grade", response_model=HomeworkDetailResponse)
async def grade_homework(
    homework_id: int,
    data: GradeHomeworkRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> HomeworkDetailResponse:
    """Оценить сданное ДЗ (админ)."""
    service = HomeworkService()
    try:
        await service.grade_homework(session, homework_id, data.score)
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return await _detail(service, session, homework_id)


@router.get("/{student_id}", response_model=List[HomeworkDetailResponse])
async def list_student_homeworks(
    student_id: int,
    current_user: User = Depends(require_student_or_admin),
    session: AsyncSession = Depends(get_db_session),
) -> List[HomeworkDetailResponse]:
    """Список ДЗ ученика ОДНИМ запросом (устранён N+1).

    Раньше здесь был цикл `_detail(hw.id)` на каждое ДЗ — по 2 дополнительных
    запроса (homework + lesson) на элемент. Теперь уроки подтягиваются тем же
    JOIN-запросом, что и сами ДЗ.
    """
    service = HomeworkService()
    pairs = await service.get_student_homeworks_with_lessons(session, student_id)
    return [_hw_detail(hw, lesson) for hw, lesson in pairs]
