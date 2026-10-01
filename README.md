# MY_LMS

Telegram-экосистема для автоматизации работы репетитора: бот, Mini App, расписание, домашние задания, пробные экзамены и баланс занятий.

## Возможности

- **Бот (Aiogram 3)** — вход по логину/паролю, команды `/schedule`, `/homeworks`, `/catalog`, `/app` (кнопка открытия Mini App), FSM на RedisStorage.
- **Mini App (Flet + прокси `/app` с WebSocket)** — кабинеты администратора и ученика: дашборд, расписание, ДЗ, пробники, отчёты, загрузка файлов.
- **REST API (FastAPI)** — уроки (создание/перенос/отмена/проведение/подтверждение), ДЗ (выдача/сдача/оценка), пробники с автоотметкой по порогам, статистика и заработок, RBAC (admin/student) через JWT.
- **Worker (Arq + Redis)** — напоминания об уроках («через N минут», в часовой зоне пользователя), напоминания о несданных ДЗ к дедлайну, автозакрытие завершившихся уроков **без автосписания** (статус `needs_confirmation`, деньги списываются только после подтверждения преподавателем).
- **PostgreSQL + Alembic** — SQLAlchemy 2 (async), миграции; атомарное изменение баланса (без гонок read-modify-write).

## Архитектура

Слои (подробно в `docs/03_architecture.md`):

```
bot / webapp (UI) → api (FastAPI) → services (бизнес-логика) → repositories → db (SQLAlchemy) → PostgreSQL
worker (Arq) ──────────────↗                Redis: FSM бота, очереди задач, дедупликация напоминаний
```

Документация проекта — в папке `docs/` (обзор, техстек, архитектура, схема БД, FSM бота, правила для ИИ-агентов).

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения (в `ENVIRONMENT=production` приложение не стартует с заглушками `BOT_TOKEN` / `JWT_SECRET_KEY`).
2. Поднимите инфраструктуру и сервисы:

```bash
docker compose up -d          # postgres, redis, migrate, api, webapp, worker
python seed.py                # первичный администратор (только dev!)
```

Локальная разработка без Docker:

```bash
poetry install
alembic upgrade head
uvicorn src.main:app --reload        # API :8000
python -m src.webapp.main            # Flet :8550 (или открыть http://localhost:8000/app/)
python -m src.worker                 # воркер уведомлений
python -m src.bot.main               # Telegram-бот
```

## Тесты

```bash
pytest tests/ -q        # 127 тестов: API, сервисы, репозитории, бот, воркер, конфиг, WS-прокси
```

## Структура репозитория

| Путь | Назначение |
|---|---|
| `src/api` | Роутеры FastAPI, схемы Pydantic, зависимости RBAC |
| `src/services` | Бизнес-логика (уроки, ДЗ, пробники, статистика, пользователи) |
| `src/repositories` | Слой доступа к данным (SQLAlchemy async) |
| `src/db` | Модели, сессии, базовый класс |
| `src/bot` | Aiogram-бот: хэндлеры, FSM, клавиатуры, middleware |
| `src/webapp` | Flet Mini App (админ + ученик), работает только через API |
| `src/worker` | Arq-воркер: cron-напоминания и автозакрытие |
| `src/core` | Конфигурация, исключения, утилиты времени/часовых зон |
| `alembic/` | Миграции схемы БД |
| `tests/` | Pytest-набор по всем слоям |

## Известные ограничения (security debt — план «Этап 7»)

- Личность в Mini App определяется из непроверяемого `initDataUnsafe`; серверная HMAC-верификация `initData` не реализована.
- Нет rate-limiting на `/login` и механизма отзыва JWT.
- Требуется HTTPS/reverse-proxy для продакшена (Telegram требует публичный HTTPS-домен Mini App).

## Лицензия

Private.
