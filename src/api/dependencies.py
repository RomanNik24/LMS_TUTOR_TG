from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import RoleEnum, User
from src.db.session import get_async_session
from src.repositories import UserRepository
from src.services.auth import AuthService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


# Используется FastAPI для чтения:
# Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Получает текущего пользователя из JWT access token.
    """

    auth = AuthService()

    try:
        payload = auth.decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")

    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный идентификатор пользователя в токене",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository()

    user = await user_repo.get_by_id(
        session,
        user_id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Разрешает доступ только администратору.
    """

    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )

    return current_user


async def require_student_or_admin(
    student_id: int,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Администратор может работать с любым студентом.

    Студент может работать только со своими данными.
    """

    if current_user.role == RoleEnum.admin:
        return current_user

    if (
        current_user.role == RoleEnum.student
        and current_user.id == student_id
    ):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Нет доступа к данным этого ученика",
    )