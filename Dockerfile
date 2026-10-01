# MY_LMS — единый образ для api / bot / webapp (docs/02_tech_stack.md)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости для asyncpg/passlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Сначала зависимости — кэш слоёв не сбрасывается при правках кода
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry-core==1.9.0 \
 && poetry export -f requirements.txt --output requirements.txt --without-hashes || \
    pip install --no-cache-dir "fastapi" "uvicorn[standard]" "aiogram>=3" \
        "pydantic-settings" "sqlalchemy>=2" "alembic>=1.13" "asyncpg>=0.29" \
        "passlib[bcrypt]" "bcrypt==4.0.1" "python-jose[cryptography]" \
        "redis>=5" "arq>=0.28" "httpx" "websockets>=12" "flet>=1.0" "greenlet" \
        "python-multipart" "aiosqlite"

# Код проекта
COPY . .

# Не root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src.server"]
