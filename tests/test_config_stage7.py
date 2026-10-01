"""Этап 7 (безопасность, п.1): запрет дефолтных секретов в production.

Проверяет правила из src/core/config.Settings._validate_secrets:
- ENVIRONMENT=production + заглушка/короткий JWT_SECRET_KEY или BOT_TOKEN
  -> RuntimeError при импорте конфигурации (приложение не стартует);
- корректные секреты в production -> старт разрешён;
- dev/test с заглушками -> запуск возможен, но с предупреждением в логах.
"""

import importlib
import logging
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOOD_JWT = "s" * 48  # >= MIN_SECRET_LENGTH, не заглушка
GOOD_BOT = "123456:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _run_snippet(env: dict[str, str]) -> subprocess.CompletedProcess:
    """Загружает конфигурацию в дочернем процессе с изолированным окружением.

    Дочерний процесс нужен потому, что settings — singleton на уровне модуля:
    только свежий импорт гарантирует чтение именно переданных переменных.
    .env не подмешивается: cwd — временный каталог вне репозитория.
    """
    code = (
        "import sys; sys.path.insert(0, {root!r});\n"
        "from src.core.config import Settings;\n"
        "s = Settings();\n"
        "print('OK', s.environment.value)\n"
    ).format(root=str(PROJECT_ROOT))
    full_env = {"PATH": "/usr/bin:/bin", **env}
    return subprocess.run(
        [sys.executable, "-c", code],
        env=full_env,
        capture_output=True,
        text=True,
        cwd=str(Path.cwd().anchor),  # корень ФС: рядом точно нет .env проекта
    )


# --- production: запрещённые комбинации -----------------------------------

@pytest.mark.parametrize(
    "env, expected_in_stderr",
    [
        # Забытый JWT_SECRET_KEY: берётся дефолтная заглушка — старт падает.
        (
            {"ENVIRONMENT": "production", "BOT_TOKEN": GOOD_BOT},
            "JWT_SECRET_KEY не задан или равен небезопасной заглушке",
        ),
        # Явная заглушка dev-insecure-secret-change-me.
        (
            {
                "ENVIRONMENT": "production",
                "BOT_TOKEN": GOOD_BOT,
                "JWT_SECRET_KEY": "dev-insecure-secret-change-me",
            },
            "JWT_SECRET_KEY не задан или равен небезопасной заглушке",
        ),
        # Заглушка из .env.example тоже ловится.
        (
            {
                "ENVIRONMENT": "production",
                "BOT_TOKEN": GOOD_BOT,
                "JWT_SECRET_KEY": "change-me-to-a-long-random-string",
            },
            "JWT_SECRET_KEY не задан или равен небезопасной заглушке",
        ),
        # Слишком короткий, но «не похожий на заглушку» ключ.
        (
            {
                "ENVIRONMENT": "production",
                "BOT_TOKEN": GOOD_BOT,
                "JWT_SECRET_KEY": "short-secret",
            },
            "слишком короткий",
        ),
        # Дефолтный BOT_TOKEN в проде.
        (
            {
                "ENVIRONMENT": "production",
                "JWT_SECRET_KEY": GOOD_JWT,
            },
            "BOT_TOKEN не задан или равен заглушке",
        ),
        # Заглушка your-bot-token-here из .env.example.
        (
            {
                "ENVIRONMENT": "production",
                "BOT_TOKEN": "your-bot-token-here",
                "JWT_SECRET_KEY": GOOD_JWT,
            },
            "BOT_TOKEN не задан или равен заглушке",
        ),
        # Пустые значения тоже считаются незаполненными.
        (
            {
                "ENVIRONMENT": "production",
                "BOT_TOKEN": "",
                "JWT_SECRET_KEY": "",
            },
            "запрещён",
        ),
    ],
)
def test_production_rejects_insecure_secrets(env, expected_in_stderr):
    proc = _run_snippet(env)
    assert proc.returncode != 0, f"конфиг должен был упасть, stdout: {proc.stdout}"
    combined = proc.stderr + proc.stdout
    assert "RuntimeError" in combined
    assert expected_in_stderr in combined


# --- production: валидная конфигурация стартует ----------------------------


def test_production_accepts_strong_secrets():
    proc = _run_snippet(
        {
            "ENVIRONMENT": "production",
            "BOT_TOKEN": GOOD_BOT,
            "JWT_SECRET_KEY": GOOD_JWT,
        }
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK production" in proc.stdout


# --- dev/test: заглушки допустимы, но помечены warning ---------------------


def test_development_allows_placeholders_with_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="src.core.config"):
        module = importlib.reload(
            importlib.import_module("src.core.config")
        )
    s = module.Settings(
        environment="development",
        bot_token="change-me-bot-token",
        jwt_secret_key="dev-insecure-secret-change-me",
    )
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    # Singleton-импорт сам по себе предупреждает о дефолтах (в CI без .env).
    assert any("НЕБЕЗОПАСНЫЙ JWT_SECRET_KEY" in w for w in warnings) or hasattr(s, "jwt_secret_key")
    # Прямая конструкция с заглушками обязана выдать оба предупреждения.
    assert any("НЕБЕЗОПАСНЫЙ JWT_SECRET_KEY" in w for w in warnings)
    assert any("BOT_TOKEN не настроен" in w for w in warnings)
    assert module.Environment.test.value == "test"


def test_test_environment_does_not_raise_on_placeholders():
    from src.core.config import Settings

    s = Settings(
        environment="test",
        bot_token="change-me-bot-token",
        jwt_secret_key="dev-insecure-secret-change-me",
    )
    assert s.is_production is False
