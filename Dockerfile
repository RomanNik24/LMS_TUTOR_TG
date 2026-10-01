# Стадия 1 (deps): требования из poetry.lock.
# Стадия deps нужна только ради `poetry export`: poetry CLI не должен
# попадать в финальный образ. poetry-core — это библиотека, бинарника
# `poetry` она не даёт, поэтому раньше строка `poetry export ... ||`
# всегда падала в захардкоженный pip-fallback с unpinned-версиями.
# export — отдельный плагин в Poetry 2.x, поэтому ставим его явно.
FROM python:3.12-slim AS deps
WORKDIR /app
RUN pip install --no-cache-dir "poetry==2.5.1" "poetry-plugin-export==1.9.0"
COPY pyproject.toml poetry.lock ./
# --without-hashes: блокировка по версиям (файлы в lock есть, но экспорт
# с хешами тянет все ссылки). Основной+dev не нужен: тесты в образе не
# запускаются, aiosqlite/pytest — только для локальной разработки.
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only main \
 && pip install --no-cache-dir -r requirements.txt

# Стадия 2 (финальная): MY_LMS — единый образ для api / bot / webapp
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Требования из lock копируются из стадии deps: poetry CLI в финальный
# образ не попадает, но версии пакетов ровно те, что в poetry.lock.
COPY --from=deps /app/requirements.txt /tmp/requirements.txt

# Системные зависимости для asyncpg/passlib + установка из lock
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm -f /tmp/requirements.txt

# Код проекта
COPY . .

# Не root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src.server"]
