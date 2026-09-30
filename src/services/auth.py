from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import User
from src.repositories import UserRepository


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def get_password_hash(self, password: str) -> str:
        """Хэширует пароль."""
        return pwd_context.hash(password)

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str,
    ) -> bool:
        """Сравнивает сырой пароль с хэшем из БД."""
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )

    async def authenticate_user(
        self,
        session: AsyncSession,
        login: str,
        password: str,
    ) -> Optional[User]:
        """
        Проверяет логин и пароль.

        Возвращает пользователя при успешной авторизации.
        Возвращает None, если логин или пароль неверны.
        """
        user = await self.user_repo.get_by_login(
            session,
            login,
        )

        if not user:
            return None

        if not self.verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user

    def create_access_token(self, user: User) -> str:
        """
        Создаёт JWT access token для пользователя.
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