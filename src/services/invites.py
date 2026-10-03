"""Одноразовые приглашения для входа в бот (docs/05 §3.1, docs/09 §2.4).

Паролей в системе нет: преподаватель создаёт профиль ученика и выпускает
приглашение — ссылку ``t.me/<bot>?start=inv_<token>``. Токен генерируется
``secrets.token_urlsafe(32)``, в БД хранится **только** его SHA-256 хэш,
срок жизни — 7 дней, использование — однократное.

Перевыпуск инвалидирует предыдущий активный токен того же профиля, чтобы
одновременно «живым» оставалось ровно одно приглашение.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import AuthToken, AuthTokenPurposeEnum, User

INVITE_TTL = timedelta(days=7)
TOKEN_PREFIX = "inv_"


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_invite_token(raw_token: str) -> str:
    """SHA-256 от сырого токена — единственное, что попадает в БД."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def invite_url(raw_token: str) -> str:
    bot_username = ""
    token = settings.bot_token.get_secret_value()
    # Формат реального токена "<digits>:<secret>" — username так не вычислить;
    # при наличии TELEGRAM_BOT_USERNAME он был бы подставлен сюда.
    return f"https://t.me/{bot_username}?start={TOKEN_PREFIX}{raw_token}" if bot_username \
        else f"t.me/BOT?start={TOKEN_PREFIX}{raw_token}"


class InviteService:
    def __init__(self) -> None:
        self._user_repo = None  # лениво, чтобы не тянуть репозитории в тесте

    async def issue(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        issued_by: Optional[int] = None,
    ) -> tuple[AuthToken, str]:
        """Выпустить (перевыпустить) приглашение. Возвращает (запись, сырой токен).

        Сырой токен существует только здесь — больше нигде не логируется и
        в БД не сохраняется.
        """
        # отзываем прежние активные приглашения этого профиля
        stale = await session.execute(
            select(AuthToken).where(
                AuthToken.user_id == user_id,
                AuthToken.purpose == AuthTokenPurposeEnum.invite,
                AuthToken.used_at.is_(None),
                AuthToken.revoked_at.is_(None),
            )
        )
        now = utcnow_naive()
        for tok in stale.scalars().all():
            tok.revoked_at = now

        raw_token = secrets.token_urlsafe(32)
        record = AuthToken(
            user_id=user_id,
            purpose=AuthTokenPurposeEnum.invite,
            token_hash=hash_invite_token(raw_token),
            issued_by=issued_by,
            expires_at=now + INVITE_TTL,
        )
        session.add(record)
        await session.flush()
        return record, raw_token

    async def redeem(
        self,
        session: AsyncSession,
        raw_token: str,
        telegram_id: int,
    ) -> tuple[Optional[User], str]:
        """Погасить приглашение и привязать telegram_id к профилю.

        Возвращает (user | None, status), где status:
        - "ok"               — привязано, токен помечен использованным;
        - "invalid"          — токена нет / просрочен / использован / отозван;
        - "already_linked"   — этот telegram_id уже привязан (повторный вход);
        - "conflict"         — id занят другим профилем.
        """
        record = await session.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == hash_invite_token(raw_token),
                AuthToken.purpose == AuthTokenPurposeEnum.invite,
            )
        )
        now = utcnow_naive()
        if (
            record is None
            or record.used_at is not None
            or record.revoked_at is not None
            or record.expires_at <= now
        ):
            return None, "invalid"

        from src.repositories import UserRepository

        repo = UserRepository()
        existing = await repo.get_by_telegram_id(session, telegram_id)
        if existing:
            if existing.id == record.user_id:
                # повторный вход того же профиля — токен всё равно гасим
                record.used_at = now
                await session.commit()
                return existing, "already_linked"
            return None, "conflict"

        user = await repo.update(session, record.user_id, telegram_id=telegram_id)
        record.used_at = now
        await session.commit()
        return user, "ok"


invite_service = InviteService()

__all__ = [
    "InviteService",
    "invite_service",
    "hash_invite_token",
    "invite_url",
    "INVITE_TTL",
    "TOKEN_PREFIX",
]
