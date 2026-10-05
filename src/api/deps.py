"""API dependencies: auth, rate limiting."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.db.models.users import User
from src.db.session import get_session
from src.services.auth import AuthService


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    session_id: Annotated[str | None, Cookie(alias="session_id")] = None,
) -> User:
    """Get current user from session cookie."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Unauthenticated")

    # TODO: Validate session in Redis
    # For now, get user from session_id (which could be user_id for stub)
    try:
        user_id = int(session_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session") from None

    auth_service = AuthService(session)
    user = await auth_service.users.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Attach user to request state
    request.state.user = user
    return user


def require_role(*allowed_roles: UserRole):
    """Dependency to require specific role."""
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied")
        return user
    return checker


require_student = require_role(UserRole.STUDENT)
require_staff = require_role(UserRole.OWNER, UserRole.MANAGER)
require_owner = require_role(UserRole.OWNER)
