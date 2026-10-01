import logging
from typing import Optional

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Токен бота обязателен в боевом окружении;
    # значение по умолчанию позволяет запускать API/миграции без него.
    bot_token: SecretStr = SecretStr("change-me-bot-token")

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "my_lms"

    # Redis (FSM-состояния бота, очереди задач воркера)
    redis_url: str = "redis://127.0.0.1:6379/0"

    # JWT settings
    jwt_secret_key: SecretStr = SecretStr("dev-insecure-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # URL публичного доступа к FastAPI (из него же строится ссылка Mini App)
    api_base_url: str = "http://127.0.0.1:8000"

    # Публичный HTTPS-базовый URL Mini App (требование Telegram).
    # Если задан — используется в web_app-кнопке напрямую; иначе URL
    # выводится из api_base_url (для локальной разработки через туннель).
    webapp_public_url: Optional[str] = None

    # Загрузка файлов ДЗ (до подключения S3/MinIO — локальная заглушка)
    upload_dir: str = "data/uploads"
    max_upload_mb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Сборка async-URL для подключения к базе данных (asyncpg)."""
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}"
            f"/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync-URL (psycopg2) — только для Alembic offline-режима."""
        return (
            f"postgresql://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}"
            f"/{self.db_name}"
        )

    @property
    def webapp_url(self) -> str:
        """URL Telegram Mini App (Flet), отдаваемый в кнопке web_app.

        В проде задайте WEBAPP_PUBLIC_URL (HTTPS-домен, требование Telegram);
        локально URL выводится из API_BASE_URL (/app — прокси FastAPI).
        """
        base = self.webapp_public_url or self.api_base_url
        return base.rstrip("/") + "/app"


settings = Settings()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


logger = setup_logging()