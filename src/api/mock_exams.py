"""Эндпоинты пробных экзаменов."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin, require_student_or_admin
from src.api.schemas import CreateMockExamRequest, MockExamResponse
from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import User
from src.services.mock_exam import MockExamService

router = APIRouter(prefix="/mock-exams", tags=["MockExams"])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    raise exc


@router.post("/{student_id}", response_model=MockExamResponse, status_code=201)
async def create_mock_exam(
    student_id: int,
    data: CreateMockExamRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> MockExamResponse:
    """Зафиксировать результат пробника; отметка считается по порогам предмета."""
    service = MockExamService()
    try:
        exam = await service.create_exam(
            session=session,
            student_id=student_id,
            subject=data.subject,
            primary_score=data.primary_score,
            exam_date=data.date,
            grade=data.grade,
        )
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return MockExamResponse.model_validate(exam)


@router.get("/{student_id}", response_model=List[MockExamResponse])
async def list_mock_exams(
    student_id: int,
    current_user: User = Depends(require_student_or_admin),
    session: AsyncSession = Depends(get_db_session),
) -> List[MockExamResponse]:
    """История пробников ученика (динамика для графика отчётов)."""
    service = MockExamService()
    try:
        exams = await service.get_student_exams(session, student_id)
    except NotFoundError as exc:
        raise _translate(exc) from exc
    return [MockExamResponse.model_validate(e) for e in exams]
