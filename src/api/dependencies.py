from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

# Единый источник сессий БД — src/db/session.py (см. docs/03_architecture.md)
from src.db.models import RoleEnum, User
from src.db.session import get_db_session
from src.repositories import UserRepository
from src.services.auth import AuthService

__all__ = ["get_db_session", "oauth2_scheme", "get_current_user",
           "require_admin", "require_student_or_admin"]


# Используется FastAPI для чтения:
# Authorization: Bearer <token>
# Токен выдаётся серверу Mini App после успешной верификации initData
# (парольного входа в системе нет — docs/09 §2.4).
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/webapp-identify",
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