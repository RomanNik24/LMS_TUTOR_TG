# MY_LMS — Telegram-бот и Mini App для частного репетитора

## О проекте
**MY_LMS** — система автоматизации частного репетитора (информатика и математика, ОГЭ/ЕГЭ) на базе Telegram-бота и веб-интерфейса (Mini App внутри Telegram + сайт в браузере).

Бренд: **«Ромчик | ИнфоМат»**

## Стек технологий

### Бэкенд
- Python 3.11, uv
- FastAPI + Uvicorn
- Aiogram 3.x (Telegram Bot)
- SQLAlchemy 2.0 (async) + PostgreSQL 16
- Redis 7 (сессии, FSM, TaskIQ брокер)
- TaskIQ (фоновые задачи, scheduler)
- S3-совместимое хранилище (файлы ДЗ)
- Alembic (миграции)

### Фронтенд
- React 18 + TypeScript (strict)
- Vite + React Router
- TanStack Query (server state)
- Tailwind CSS + shadcn/ui
- Recharts (графики)
- Vitest + Testing Library + MSW + Playwright

### Инфраструктура
- Docker + Docker Compose
- Nginx (reverse proxy, статика, SSL)
- GitHub Actions (CI/CD)
- VPS в РФ (Timeweb/Selectel)

## Структура монорепозитория

```
.
├── .github/workflows/     # CI/CD
├── docs/                  # Документация (00-12)
├── src/                   # Бэкенд (Python)
│   ├── api/               # FastAPI роутеры /api/v1
│   ├── bot/               # Aiogram хэндлеры, FSM
│   ├── services/          # Бизнес-логика
│   ├── repositories/      # Доступ к БД
│   ├── schemas/           # Pydantic схемы
│   ├── db/                # Модели, миграции
│   ├── core/              # Конфиг, логирование, исключения
│   └── worker/            # TaskIQ задачи
├── frontend/              # Фронтенд (React + TS)
│   ├── src/
│   │   ├── api/           # Клиент, типы из OpenAPI
│   │   ├── features/      # Фичи (auth, schedule, homework...)
│   │   ├── components/    # UI компоненты
│   │   ├── layouts/       # Layouts
│   │   ├── lib/           # Утилиты, тексты, Telegram SDK
│   │   └── styles/        # Tailwind + токены дизайна
│   └── public/
├── tests/                 # Бэкенд тесты
├── scripts/               # Вспомогательные скрипты
├── nginx/                 # Nginx конфиги
├── docker-compose.yml     # Локальная разработка
├── docker-compose.prod.yml # Продакшн
├── pyproject.toml         # Python зависимости
└── README.md
```

## Быстрый старт (локально)

### Требования
- Docker + Docker Compose
- Node.js 20+ (для фронтенда)
- Python 3.11 + uv (для бэкенда вне Docker)

### Запуск через Docker Compose
```bash
# Клонировать репозиторий
git clone https://github.com/RomanNik24/LMS_TUTOR_TG.git
cd LMS_TUTOR_TG

# Скопировать .env.example в .env.local и заполнить
cp .env.example .env.local

# Запустить все сервисы
docker compose up -d
```

Сервисы будут доступны на:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173 (dev) или http://localhost:80 (через nginx)
- MinIO Console: http://localhost:9001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Разработка бэкенда (вне Docker)
```bash
cd LMS_TUTOR_TG
uv sync --frozen --all-extras
cp .env.example .env.local
# Заполнить .env.local
uv run uvicorn src.main:app --reload --port 8000
```

### Разработка фронтенда
```bash
cd LMS_TUTOR_TG/frontend
pnpm install
cp .env.example .env.local
pnpm dev
```

## Документация
Все ключевые решения описаны в папке `docs/`:
- `00_README_INDEX.md` — индекс документации
- `01_project_overview.md` — бизнес-логика, MVP, user stories
- `02_tech_stack.md` — стек технологий
- `03_architecture.md` — архитектура, слои, потоки данных
- `04_database_schema.md` — схема БД, шкалы экзаменов
- `05_bot_logic_and_fsm.md` — логика бота, команды, уведомления
- `06_agent_rules.md` — правила для ИИ-агентов
- `07_design.md` — дизайн-система, экраны, тон
- `08_api_spec.md` — REST API контракт
- `09_security_and_privacy.md` — безопасность, приватность
- `10_deployment_and_ops.md` — деплой, бэкапы, мониторинг
- `11_roadmap.md` — этапы разработки
- `12_frontend_guide.md` — гайд по фронтенду для питонистов

## Деплой
См. `docs/10_deployment_and_ops.md` для полного описания.

Кратко:
1. Настроить VPS в РФ (Ubuntu, Docker, firewall)
2. Зарегистрировать домен, получить SSL (Let's Encrypt)
3. Создать S3 бакеты (файлы + бэкапы)
4. Заполнить `.env` на сервере (staging и prod отдельно)
5. Настроить GitHub Secrets для CI/CD
6. Запустить миграции: `alembic upgrade head`
7. Деплой через GitHub Actions (push в main → staging → ручное подтверждение → prod)

## Лицензия
MIT