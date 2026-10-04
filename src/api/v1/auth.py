"""Auth API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.services.auth import AuthService
from src.schemas.auth import TelegramAuthRequest, LinkAuthRequest, MeResponse, InvitationCreateResponse
from src.core.config import settings
from src.core.exceptions import BusinessRuleError, NotFoundError

router = APIRouter()


@router.post("/auth/telegram", response_model=MeResponse)
async def auth_telegram(
    request: TelegramAuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate via Telegram Mini App initData."""
    auth = AuthService(session)
    user = await auth.validate_init_data(request.init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid initData")

    # Create session in Redis, set HttpOnly cookie
    # TODO: Implement session creation
    session_id = "stub-session-id"
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=settings.APP_ENV != "local",
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/",
    )

    return MeResponse(
        id=user.id,
        role=user.role.value,
        display_name=user.display_name,
        timezone=user.timezone,
        is_active=user.is_active,
    )


@router.post("/auth/link", response_model=MeResponse)
async def auth_link(
    request: LinkAuthRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate via one-time web login link."""
    auth = AuthService(session)
    try:
        user = await auth.consume_web_login(request.token)
    except BusinessRuleError as e:
        raise HTTPException(status_code=401, detail=e.message)

    session_id = "stub-session-id"
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=settings.APP_ENV != "local",
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/",
    )

    return MeResponse(
        id=user.id,
        role=user.role.value,
        display_name=user.display_name,
        timezone=user.timezone,
        is_active=user.is_active,
    )


@router.post("/auth/logout")
async def auth_logout(response: Response, session: AsyncSession = Depends(get_session)):
    """Logout: delete session."""
    response.delete_cookie("session_id", path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def get_me(session: AsyncSession = Depends(get_session)):
    """Get current user from session."""
    # TODO: Get user from session cookie
    raise HTTPException(status_code=401, detail="Not implemented")


@router.patch("/me", response_model=MeResponse)
async def update_me(session: AsyncSession = Depends(get_session)):
    """Update current user profile (timezone, display_name)."""
    raise HTTPException(status_code=401, detail="Not implemented")