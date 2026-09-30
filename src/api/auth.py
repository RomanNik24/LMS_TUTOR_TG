from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.api.schemas import LoginRequest, TokenResponse
from src.services.auth import AuthService


router = APIRouter(
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