"""Auth service: invitations, sessions, Telegram auth."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.user import UserRepository, AuthTokenRepository
from src.repositories.service import AuditLogRepository
from src.core.security import generate_token, hash_token, validate_telegram_init_data
from src.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from src.core.enums import UserRole, AuthTokenPurpose
from src.db.models.users import User, AuthToken


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.tokens = AuthTokenRepository(session)
        self.audit = AuditLogRepository(session)

    async def create_invite(
        self,
        actor: User,
        target_user_id: int,
        purpose: AuthTokenPurpose = AuthTokenPurpose.INVITE,
        ttl_days: int = 7,
    ) -> tuple[str, AuthToken]:
        """Create invitation token. Returns (raw_token, token_record)."""
        target = await self.users.get(target_user_id)
        if not target:
            raise NotFoundError("User", target_user_id)

        # Revoke existing active invites for this user/purpose
        # (handled by unique constraint on token_hash, but we can clean up)

        raw_token = generate_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now() + timedelta(days=ttl_days)

        token = await self.tokens.create(
            purpose=purpose,
            user_id=target_user_id,
            token_hash=token_hash,
            created_by=actor.id,
            expires_at=expires_at,
        )
        await self.audit.log(
            action="invite.created",
            entity_type="auth_token",
            entity_id=token.id,
            data={"user_id": target_user_id, "purpose": purpose.value},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return raw_token, token

    async def accept_invite(self, raw_token: str, telegram_id: int) -> User:
        """Accept invitation and bind telegram_id."""
        token_hash = hash_token(raw_token)
        token = await self.tokens.get_valid_invite(token_hash)
        if not token:
            raise BusinessRuleError("invite_invalid", "Ссылка недействительна или устарела")

        target = await self.users.get(token.user_id)
        if not target:
            raise NotFoundError("User", token.user_id)

        # Check if this telegram_id is already linked to another user
        existing = await self.users.get_by_telegram_id(telegram_id)
        if existing and existing.id != target.id:
            raise BusinessRuleError(
                "telegram_already_linked",
                "Этот Telegram-аккаунт уже привязан к другому профилю.",
            )

        # If target already has different telegram_id, require confirmation
        if target.telegram_id and target.telegram_id != telegram_id:
            raise BusinessRuleError(
                "relink_required",
                "У профиля уже привязан другой Telegram. Требуется подтверждение.",
            )

        target.telegram_id = telegram_id
        token.used_at = datetime.now()
        await self.audit.log(
            action="invite.accepted",
            entity_type="user",
            entity_id=target.id,
            data={"telegram_id": telegram_id},
            actor_user_id=target.id,
        )
        await self.session.commit()
        return target

    async def confirm_relink(self, raw_token: str, telegram_id: int) -> User:
        """Confirm relinking telegram_id to a different profile."""
        token_hash = hash_token(raw_token)
        token = await self.tokens.get_valid_invite(token_hash)
        if not token:
            raise BusinessRuleError("invite_invalid", "Ссылка недействительна или устарела")

        target = await self.users.get(token.user_id)
        if not target:
            raise NotFoundError("User", token.user_id)

        # Unlink old telegram_id if any
        if target.telegram_id:
            await self.audit.log(
                action="telegram.unlinked",
                entity_type="user",
                entity_id=target.id,
                data={"old_telegram_id": target.telegram_id},
                actor_user_id=target.id,
            )

        target.telegram_id = telegram_id
        token.used_at = datetime.now()
        await self.audit.log(
            action="telegram.relinked",
            entity_type="user",
            entity_id=target.id,
            data={"new_telegram_id": telegram_id},
            actor_user_id=target.id,
        )
        await self.session.commit()
        return target

    async def revoke_invite(self, token_id: int, actor: User) -> None:
        token = await self.tokens.get(token_id)
        if not token:
            raise NotFoundError("AuthToken", token_id)
        token.revoked_at = datetime.now()
        await self.audit.log(
            action="invite.revoked",
            entity_type="auth_token",
            entity_id=token_id,
            actor_user_id=actor.id,
        )
        await self.session.commit()

    async def create_web_login(self, user_id: int, ttl_minutes: int = 10) -> tuple[str, AuthToken]:
        """Create one-time web login link."""
        raw_token = generate_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        token = await self.tokens.create(
            purpose=AuthTokenPurpose.WEB_LOGIN,
            user_id=user_id,
            token_hash=token_hash,
            created_by=None,
            expires_at=expires_at,
        )
        await self.session.commit()
        return raw_token, token

    async def consume_web_login(self, raw_token: str) -> User:
        """Consume web login token and return user."""
        token_hash = hash_token(raw_token)
        token = await self.tokens.get_valid_web_login(token_hash)
        if not token:
            raise BusinessRuleError("invite_invalid", "Ссылка недействительна или устарела")

        user = await self.users.get(token.user_id)
        if not user:
            raise NotFoundError("User", token.user_id)

        token.used_at = datetime.now()
        await self.session.commit()
        return user

    async def validate_init_data(self, init_data: str) -> User | None:
        """Validate Telegram initData and return user if found."""
        parsed = validate_telegram_init_data(init_data)
        if not parsed:
            return None
        telegram_id = int(parsed.get("id", 0))
        return await self.users.get_by_telegram_id(telegram_id)

    async def unlink_telegram(self, user_id: int, actor: User) -> None:
        target = await self.users.get(user_id)
        if not target:
            raise NotFoundError("User", user_id)
        old_id = target.telegram_id
        target.telegram_id = None
        await self.audit.log(
            action="telegram.unlinked",
            entity_type="user",
            entity_id=user_id,
            data={"old_telegram_id": old_id},
            actor_user_id=actor.id,
        )
        await self.session.commit()