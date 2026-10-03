from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import User
from src.repositories import UserRepository


class AuthService:
    """Выдача и проверка токенов доступа.

    Парольная аутентификация удалена из системы (docs/09 §2.4): вход — только
    по одноразовым приглашениям и верифицированной initData Mini App. Методы
    ниже работают с уже идентифицированным пользователем.
    """

    def __init__(self):
        self.user_repo = UserRepository()

    def create_access_token(self, user: User) -> str:
        """
        Создаёт JWT access token для пользователя.

        Используется server-side (Flet-приложение ходит в API от имени
        вошедшего через initData пользователя). Клиентские секреты не выдаёт.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(
            minutes=settings.access_token_expire_minutes
        )

        payload = {
            "sub": str(user.id),
            "role": user.role.value,
            "iat": now,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict:
        """
        Декодирует и проверяет JWT access token.

        Если токен недействительный или просрочен,
        python-jose выбросит JWTError.
        """
        return jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )

    async def get_user_by_telegram_id(
        self,
        session: AsyncSession,
        telegram_id: int,
    ) -> Optional[User]:
        """Пользователь по подтверждённому telegram_id (после verify_init_data)."""
        return await self.user_repo.get_by_telegram_id(session, telegram_id)

    async def link_telegram_id(
        self,
        session: AsyncSession,
        user_id: int,
        telegram_id: int,
    ) -> Optional[User]:
        """
        Привязывает telegram_id к аккаунту пользователя.

        Выбрасывает ValueError, если telegram_id
        уже привязан к другому пользователю.
        """
        existing_user = await self.user_repo.get_by_telegram_id(
            session,
            telegram_id,
        )

        if existing_user and existing_user.id != user_id:
            raise ValueError(
                "Этот Telegram аккаунт уже привязан к другому пользователю."
            )

        return await self.user_repo.update(
            session,
            user_id,
            telegram_id=telegram_id,
        )