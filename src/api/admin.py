"""Административные эндпоинты: дашборд, статистика, тарифы, баланс."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, require_admin
from src.api.schemas import (
    BalanceUpdateRequest,
    DashboardResponse,
    EarningsResponse,
    LessonPriceRequest,
    StudentProgressResponse,
    UserResponse,
)
from src.core.exceptions import NotFoundError, ValidationError
from src.db.models import User
from src.services.statistics import StatisticsService
from src.services.user import UserService

router = APIRouter(prefix="/admin", tags=["Admin"])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, ValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    raise exc


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardResponse:
    """Сводка дня: расписание, несданные ДЗ к сегодняшним урокам, должники."""
    service = StatisticsService()
    summary = await service.get_dashboard(session)
    return DashboardResponse(
        date=summary.date,
        today_lessons=summary.today_lessons,
        students_without_homework=summary.students_without_homework,
        debtors=summary.debtors,
        cancelled_count=summary.cancelled_count,
    )


@router.get("/progress", response_model=List[StudentProgressResponse])
async def get_all_progress(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> List[StudentProgressResponse]:
    """Сводная успеваемость по всем ученикам."""
    service = StatisticsService()
    rows = await service.get_all_progress(session)
    return [StudentProgressResponse(**row.__dict__) for row in rows]


@router.get("/earnings", response_model=EarningsResponse)
async def get_earnings(
    start: datetime = Query(..., description="Начало периода (ISO)"),
    end: datetime = Query(..., description="Конец периода (ISO)"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> EarningsResponse:
    """Заработок за период по проведённым урокам."""
    service = StatisticsService()
    earned = await service.get_earnings(session, start, end)
    return EarningsResponse(start=start, end=end, earned=earned)


@router.patch("/{student_id}/price", response_model=UserResponse)
async def set_lesson_price(
    student_id: int,
    data: LessonPriceRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Индивидуальный ценник занятия для ученика."""
    service = UserService()
    try:
        user = await service.set_lesson_price(session, student_id, data.lesson_price)
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return UserResponse.model_validate(user)


@router.post("/{student_id}/balance", response_model=UserResponse)
async def adjust_balance(
    student_id: int,
    data: BalanceUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Ручное пополнение/списание баланса занятий (оплата вне системы)."""
    service = UserService()
    try:
        user = await service.add_balance(session, student_id, data.delta)
    except (NotFoundError, ValidationError) as exc:
        raise _translate(exc) from exc
    return UserResponse.model_validate(user)
