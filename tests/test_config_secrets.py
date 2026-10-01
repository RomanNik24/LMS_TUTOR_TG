"""Регрессия: строгая проверка секретов и чтение переменных конфигурации.

1) ENVIRONMENT=production запрещает старт с заглушками JWT_SECRET_KEY/BOT_TOKEN;
   в dev/test заглушки допустимы (см. src/core/config.py::_validate_secrets).
2) MAX_UPLOAD_MB читается в settings.max_upload_mb — раньше в .env.example было
   MAX_UPLOAD_SIZE_MB, pydantic-settings не сопоставлял имя с полем
   max_upload_mb и из-за extra="ignore" лимит молча оставался дефолтным.
"""

import pytest
from pydantic import ValidationError

from src.core.config import Settings


# === Секреты ===

def test_production_rejects_placeholder_jwt_secret():
    with pytest.raises((ValidationError, RuntimeError)):
        Settings(
            environment="production",
            jwt_secret_key="dev-insecure-secret-change-me",
            bot_token="123456:real-token",
        )


def test_production_rejects_short_jwt_secret():
    with pytest.raises((ValidationError, RuntimeError)):
        Settings(
            environment="production",
            jwt_secret_key="short-key",
            bot_token="123456:real-token",
        )


def test_production_rejects_placeholder_bot_token():
    with pytest.raises((ValidationError, RuntimeError)):
        Settings(
            environment="production",
            jwt_secret_key="x" * 48,
            bot_token="change-me-bot-token",
        )


def test_production_accepts_strong_secrets():
    s = Settings(
        environment="production",
        jwt_secret_key="a" * 48,
        bot_token="123456:AAA-real-bot-token",
    )
    assert s.is_production is True


def test_development_allows_placeholders():
    s = Settings(environment="development")
    assert s.is_production is False


# === MAX_UPLOAD_MB (фикс имени переменной окружения) ===

def test_max_upload_mb_env_var_is_honored(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "25")
    s = Settings()
    assert s.max_upload_mb == 25


def test_max_upload_size_mb_legacy_alias_still_works(monkeypatch):
    """Старые .env с устаревшим именем не должны ломаться (AliasChoices)."""
    monkeypatch.delenv("MAX_UPLOAD_MB", raising=False)
    monkeypatch.delenv("max_upload_mb", raising=False)
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "30")
    s = Settings()
    assert s.max_upload_mb == 30


def test_max_upload_mb_default_without_env(monkeypatch):
    for name in ("MAX_UPLOAD_MB", "max_upload_mb", "MAX_UPLOAD_SIZE_MB"):
        monkeypatch.delenv(name, raising=False)
    s = Settings()
    assert s.max_upload_mb == 10


def test_dotenv_example_matches_field_name():
    """Имена переменных в .env.example обязаны резолвиться в поля Settings."""
    import re
    from pathlib import Path
    from pydantic_settings import BaseSettings

    text = Path(".env.example").read_text(encoding="utf-8")
    fields = set(Settings.model_fields.keys())
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if not m:
            continue
        env_name = m.group(1)
        aliases = {
            f for f in fields
            if f.lower() == env_name.lower()
            or getattr(Settings.model_fields[f], "validation_alias", None)
            in (env_name,)
            or _alias_contains(Settings.model_fields[f], env_name)
        }
        assert aliases, f".env.example: {env_name} не соответствует ни одному полю Settings"


def _alias_contains(field, env_name: str) -> bool:
    va = getattr(field, "validation_alias", None)
    if isinstance(va, AliasChoicesType):
        return env_name in va.choices
    return False


try:
    from pydantic import AliasChoices as AliasChoicesType
except Exception:  # pragma: no cover
    AliasChoicesType = type(None)
