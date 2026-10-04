"""User repository."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories import BaseRepository
from src.db.models.users import User, StudentProfile, Guardian, AuthToken
from src.core.enums import UserRole, AuthTokenPurpose


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_students(self, teacher_id: int, active_only: bool = True) -> list[User]:
        stmt = select(User).where(User.role == UserRole.STUDENT)
        if active_only:
            stmt = stmt.where(User.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_staff(self) -> list[User]:
        stmt = select(User).where(User.role.in_([UserRole.OWNER, UserRole.MANAGER]))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class StudentProfileRepository(BaseRepository[StudentProfile]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, StudentProfile)

    async def get_by_user_id(self, user_id: int) -> StudentProfile | None:
        return await self.get(user_id)


class GuardianRepository(BaseRepository[Guardian]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Guardian)


class AuthTokenRepository(BaseRepository[AuthToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuthToken)

    async def get_valid_invite(self, token_hash: str) -> AuthToken | None:
        from datetime import datetime
        stmt = select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.purpose == AuthTokenPurpose.INVITE,
            AuthToken.used_at.is_(None),
            AuthToken.revoked_at.is_(None),
            AuthToken.expires_at > datetime.now(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_valid_web_login(self, token_hash: str) -> AuthToken | None:
        from datetime import datetime
        stmt = select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.purpose == AuthTokenPurpose.WEB_LOGIN,
            AuthToken.used_at.is_(None),
            AuthToken.revoked_at.is_(None),
            AuthToken.expires_at > datetime.now(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()