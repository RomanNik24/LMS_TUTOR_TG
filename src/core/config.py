"""Application configuration using Pydantic Settings."""

from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Локально конфигурация лежит в .env.local (см. .env.example и ТЗ).
        # В prod переменные приходят из окружения контейнера, файлы не нужны.
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "local"  # local, staging, prod
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lms"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram Bot
    BOT_TOKEN: str = ""
    BOT_MODE: str = "polling"  # polling, webhook
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""
    WEBHOOK_PATH_SECRET: str = ""
    OWNER_TELEGRAM_ID: int = 0
    TEACHER_CONTACT_URL: str = ""
    BOT_USERNAME: str = ""

    # Sessions
    SESSION_SECRET: str = ""
    SESSION_TTL_DAYS_STUDENT: int = 30
    SESSION_TTL_DAYS_STAFF: int = 7

    # S3 Storage
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "ru-1"
    S3_PUBLIC_URL: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Scheduler
    SCHEDULE_HORIZON_WEEKS: int = 4
    DEFAULT_TIMEZONE: str = "Europe/Moscow"

    # Telegram API (for RU access)
    TELEGRAM_API_BASE: str = "https://api.telegram.org"
    TELEGRAM_PROXY_URL: str = ""

    @model_validator(mode="after")
    def _require_secrets_in_prod(self) -> "Settings":
        """В prod запрещено молча стартовать с пустыми секретами."""
        if self.APP_ENV != "prod":
            return self

        required: dict[str, Any] = {
            "BOT_TOKEN": self.BOT_TOKEN,
            "SESSION_SECRET": self.SESSION_SECRET,
            "WEBHOOK_SECRET": self.WEBHOOK_SECRET,
            "S3_ENDPOINT_URL": self.S3_ENDPOINT_URL,
            "S3_ACCESS_KEY": self.S3_ACCESS_KEY,
            "S3_SECRET_KEY": self.S3_SECRET_KEY,
            "S3_BUCKET": self.S3_BUCKET,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            msg = f"APP_ENV=prod: обязательные переменные не заданы: {', '.join(missing)}"
            raise ValueError(msg)
        return self


settings = Settings()
