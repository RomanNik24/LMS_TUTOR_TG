from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_db_session,
    require_admin,
    require_student_or_admin,
)
from src.api.schemas import (
    BalanceResponse,
    CreateLessonRequest,
    CreateStudentRequest,
    HomeworkResponse,
    LessonResponse,
    UserResponse,
)
from src.db.models import (
    HomeworkStatusEnum,
    LessonStatusEnum,
    RoleEnum,
    User,
)
from src.repositories import (
    HomeworkRepository,
    LessonRepository,
    UserRepository,
)
from src.services.auth import AuthService


router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


# ───────────────── GET ─────────────────


@router.get(
    "/",
    response_model=List[UserResponse],
)
async def get_all_students(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Получение списка всех учеников.

    Доступно только администратору.
    """

    repo = UserRepository()

    return await repo.get_all_students(session)


@router.get(
    "/{student_id}/balance",
    response_model=BalanceResponse,
)
async def get_student_balance(
    student_id: int,
    current_user: User = Depends(require_student_or_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Получить баланс ученика.

    Администратор может посмотреть баланс любого ученика.
    Студент — только свой баланс.
    """

    repo = UserRepository()

    user = await repo.get_by_id(
        session,
        student_id,
    )

    if not user or user.role != RoleEnum.student:
        raise HTTPException(
            status_code=404,
            detail="Ученик не найден",
        )

    return BalanceResponse(
        balance=user.balance,
    )


@router.get(
    "/{student_id}/schedule",
    response_model=List[LessonResponse],
)
async def get_student_schedule(
    student_id: int,
    current_user: User = Depends(require_student_or_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Получить расписание ученика.

    Администратор может посмотреть расписание любого ученика.
    Студент — только своё расписание.
    """

    user_repo = UserRepository()

    user = await user_repo.get_by_id(
        session,
        student_id,
    )

    if not user or user.role != RoleEnum.student:
        raise HTTPException(
            status_code=404,
            detail="Ученик не найден",
        )

    lesson_repo = LessonRepository()

    return await lesson_repo.get_student_lessons(
        session,
        student_id,
    )


@router.get(
    "/{student_id}/homeworks",
    response_model=List[HomeworkResponse],
)
async def get_student_homeworks(
    student_id: int,
    current_user: User = Depends(require_student_or_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Получить все домашние задания ученика.

    Администратор может посмотреть ДЗ любого ученика.
    Студент — только свои задания.
    """

    user_repo = UserRepository()

    user = await user_repo.get_by_id(
        session,
        student_id,
    )

    if not user or user.role != RoleEnum.student:
        raise HTTPException(
            status_code=404,
            detail="Ученик не найден",
        )

    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()

    lessons = await lesson_repo.get_student_lessons(
        session,
        student_id,
    )

    homeworks = []

    for lesson in lessons:
        lesson_hws = await hw_repo.get_by_lesson_id(
            session,
            lesson.id,
        )
        homeworks.extend(lesson_hws)

    return homeworks


# ───────────────── POST ─────────────────


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
)
async def create_student(
    data: CreateStudentRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Создать нового ученика.

    Доступно только администратору.
    """

    auth = AuthService()
    user_repo = UserRepository()

    existing = await user_repo.get_by_login(
        session,
        data.login,
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Логин уже занят",
        )

    user = await user_repo.create(
        session=session,
        role=RoleEnum.student,
        login=data.login,
        password_hash=auth.get_password_hash(data.password),
        balance=data.balance,
        lesson_price=data.lesson_price,
    )

    await session.commit()

    return user


@router.post(
    "/{student_id}/lessons",
    response_model=LessonResponse,
    status_code=201,
)
async def create_lesson(
    student_id: int,
    data: CreateLessonRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Создать урок для ученика.

    Доступно только администратору.
    """

    user_repo = UserRepository()

    user = await user_repo.get_by_id(
        session,
        student_id,
    )

    if not user or user.role != RoleEnum.student:
        raise HTTPException(
            status_code=404,
            detail="Ученик не найден",
        )

    lesson_repo = LessonRepository()

    lesson = await lesson_repo.create(
        session=session,
        student_id=student_id,
        subject=data.subject,
        start_time=data.start_time,
        end_time=data.end_time,
        status=LessonStatusEnum.scheduled,
    )

    await session.commit()

    return lesson