from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.schemas import (
    LoginRequest,
    TokenResponse,
    WebAppIdentifyRequest,
    WebAppIdentifyResponse,
)
from src.repositories import UserRepository
from src.services.auth import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Авторизация пользователя по логину и паролю.

    При успешной авторизации возвращает JWT access token.
    """

    auth = AuthService()

    user = await auth.authenticate_user(
        session=session,
        login=data.login,
        password=data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )

@router.post(
    "/webapp-identify",
    response_model=WebAppIdentifyResponse,
)
async def webapp_identify(
    data: WebAppIdentifyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> WebAppIdentifyResponse:
    """
    Идентификация пользователя Mini App по telegram_id.

    Flet-сервер не имеет прямого доступа к БД (docs/03_architecture.md):
    он получает профиль и JWT-токен через этот эндпоинт.

    ВНИМАНИЕ (Этап безопасности): telegram_id пока не подтверждается
    верификацией initData — будет закрыто на этапе hardening.
    """
    user_repo = UserRepository()

    user = await user_repo.get_by_telegram_id(
        session,
        data.telegram_id,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Привяжите аккаунт через /login в боте.",
        )

    auth = AuthService()

    return WebAppIdentifyResponse(
        access_token=auth.create_access_token(user),
        token_type="bearer",
        user={
            "id": user.id,
            "login": user.login,
            "role": user.role.value,
        },
    )
