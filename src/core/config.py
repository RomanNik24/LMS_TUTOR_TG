import enum
import logging
from typing import Optional

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Значения-заглушки из .env.example / исторические дефолты. Использовать их
# в production нельзя: при ENVIRONMENT=production приложение не стартует,
# а в dev/test эти значения явно помечаются предупреждением в логах.
INSECURE_DEFAULT_JWT_SECRET = "dev-insecure-secret-change-me"
INSECURE_DEFAULT_BOT_TOKEN = "change-me-bot-token"
INSECURE_EXAMPLE_JWT_SECRETS = {
    INSECURE_DEFAULT_JWT_SECRET,
    "change-me-to-a-long-random-string",
}
INSECURE_EXAMPLE_BOT_TOKENS = {INSECURE_DEFAULT_BOT_TOKEN, "your-bot-token-here"}
MIN_SECRET_LENGTH = 32


class Environment(str, enum.Enum):
    development = "development"
    test = "test"
    production = "production"


class Settings(BaseSettings):
    # Окружение: DEVELOPMENT (по умолчанию) / TEST / PRODUCTION.
    # В production включается строгая проверка секретов (см. _validate_secrets).
    environment: Environment = Environment.development

    # Токен бота: в боевом окружении обязателен реальный значение;
    # заглушка допустима только локально (API/миграции работают без бота).
    bot_token: SecretStr = SecretStr(INSECURE_DEFAULT_BOT_TOKEN)

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "my_lms"

    # Redis (FSM-состояния бота, очереди задач воркера)
    redis_url: str = "redis://127.0.0.1:6379/0"

    # JWT settings. Дефолт — откровенно «вредная» заглушка, чтобы забытый
    # JWT_SECRET_KEY в проде приводил к ошибке старта, а не к тихой
    # возможности подделать токены (см. _validate_secrets).
    jwt_secret_key: SecretStr = SecretStr(INSECURE_DEFAULT_JWT_SECRET)
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
    def is_production(self) -> bool:
        return self.environment == Environment.production

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Не давать небезопасным заглушкам тихо уехать в production.

        Правила:
        - production: JWT_SECRET_KEY обязан быть задан, не совпадать ни с одной
          известной заглушкой и иметь длину >= MIN_SECRET_LENGTH; BOT_TOKEN —
          реальный токен (не заглушка). Любое нарушение — RuntimeError на старте.
        - development/test: заглушки допустимы, но помечаются предупреждением,
          чтобы их нельзя было не заметить в логах.
        """
        jwt_secret = self.jwt_secret_key.get_secret_value()
        bot_token = self.bot_token.get_secret_value()

        jwt_is_placeholder = (
            not jwt_secret or jwt_secret in INSECURE_EXAMPLE_JWT_SECRETS
        )
        bot_is_placeholder = not bot_token or bot_token in INSECURE_EXAMPLE_BOT_TOKENS

        if self.is_production:
            problems = []
            if jwt_is_placeholder:
                problems.append(
                    "JWT_SECRET_KEY не задан или равен небезопасной заглушке — "
                    "кто угодно сможет подделать токены. Сгенерируйте ключ: "
                    'python -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
            elif len(jwt_secret) < MIN_SECRET_LENGTH:
                problems.append(
                    f"JWT_SECRET_KEY слишком короткий ({len(jwt_secret)} символов, "
                    f"минимум {MIN_SECRET_LENGTH})"
                )
            if bot_is_placeholder:
                problems.append(
                    "BOT_TOKEN не задан или равен заглушке из .env.example — "
                    "в production нужен реальный токен от @BotFather"
                )
            if problems:
                raise RuntimeError(
                    "Запуск в ENVIRONMENT=production запрещён с текущими "
                    "настройками:\n  - " + "\n  - ".join(problems)
                )
        else:
            logger_ = logging.getLogger(__name__)
            if jwt_is_placeholder:
                logger_.warning(
                    "Используется НЕБЕЗОПАСНЫЙ JWT_SECRET_KEY по умолчанию. "
                    "Это приемлемо только для локальной разработки; перед "
                    "деплоем задайте собственный ключ в .env (ENVIRONMENT=production "
                    "откажется стартовать с этим значением)."
                )
            if bot_is_placeholder:
                logger_.warning(
                    "BOT_TOKEN не настроен (заглушка) — бот не сможет "
                    "подключиться к Telegram."
                )
        return self

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


def load_settings() -> Settings:
    """Загрузка настроек с понятной диагностикой ошибок конфигурации.

    Pydantic оборачивает исключения model_validator в ValidationError,
    поэтому переупаковываем проблему секретов обратно в RuntimeError —
    он читаемо валит старт любого сервиса (uvicorn/arq/бот) без трейсбека.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:  # noqa: BLE001
        for err in getattr(exc, "errors", lambda: [])():
            inner = err.get("ctx", {}).get("error") if isinstance(err, dict) else None
            if isinstance(inner, RuntimeError):
                raise inner from exc
        raise


settings = load_settings()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


logger = setup_logging()