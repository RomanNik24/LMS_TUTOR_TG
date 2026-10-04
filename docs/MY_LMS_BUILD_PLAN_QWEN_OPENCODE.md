# MY_LMS — детальный атомарный план построения проекта (MVP + Full)

> **Назначение:** рабочий master-plan для двух исполнителей: **QWEN-CODER** пишет и тестирует код; **OpenCode** выполняет Git/терминал/БД/Docker/окружения/деплой и проводит реальные эксплуатационные проверки.
> **Архитектурная стратегия:** новый проект строится с нуля строго по `/docs`. Старый `LMS_TUTOR_TG` используется только как reference; его архитектура, модели и legacy-функции не переносятся автоматически.

## 0. Правило атомарности

Каждая задача ниже — отдельный рабочий элемент. Для задачи, меняющей репозиторий, обязательны: отдельная ветка → один основной commit → PR → review → merge. После merge исполнитель останавливается. Следующую задачу нельзя начинать автоматически.

### Ответственность исполнителей
| Исполнитель | Делает | Не делает |
|---|---|---|
| **QWEN-CODER** | Python/SQLAlchemy/Alembic/Pydantic/FastAPI/Aiogram/TaskIQ/React/TS/тесты/CI-конфиги/документацию | не правит production-БД вручную и не придумывает бизнес-правила |
| **OpenCode** | shell, Git, Docker/Compose, PostgreSQL/Redis/MinIO/S3, реальные миграции, staging/prod, secrets, healthchecks, smoke/acceptance | не «чинит» бизнес-логику ручным SQL и не меняет код вместо QWEN без отдельной задачи |

### Порядок взаимодействия
- QWEN выполняет кодовую задачу и делает commit/PR.
- OpenCode после merge запускает реальные проверки в соответствующем окружении; при необходимости выполняет только операционную часть.
- Если OpenCode находит дефект кода, он не исправляет его в обход плана: создаётся новая bug-fix задача для QWEN.
- Если задача требует изменения ТЗ, сначала фиксируется решение владельца и обновляется документация, затем код.

## 1. Источники истины и обязательные ограничения

- `docs/00_README_INDEX.md` — индекс; `01` — бизнес; `02` — стек; `03` — архитектура; `04` — БД; `05` — бот/FSM; `06` — правила агентов; `07` — дизайн/тон; `08` — API; `09` — security/privacy; `10` — deployment; `11` — roadmap; `12` — frontend.
- При конфликте приоритет: `07 → 01 → 04 → 08 → остальные`. Не разрешать конфликт молча.
- Стек фиксирован: Python 3.11 + uv + FastAPI + Aiogram 3 + SQLAlchemy async + PostgreSQL 16+ + Redis 7 + TaskIQ + S3; React + TypeScript strict + Vite + pnpm + React Router + TanStack Query + Tailwind + shadcn + Recharts.
- Сессия: Redis + HttpOnly/Secure/SameSite=Lax cookie. Паролей нет. Browser JWT/Bearer не является целевым механизмом.
- Роли: `owner`, `manager`, `student`; guest — только bot state. Финансы — только owner.
- Нет платежей, баланса занятий, должников и Flet UI.
- Время в DB/API — UTC/TIMESTAMPTZ; пользовательское отображение — в его IANA timezone.
- Frontend не содержит бизнес-правила; сервер является источником истины.

# MVP — этап M0: предпроектная фиксация

### M0.01 — Составить ADR по конфликтам ТЗ
**Исполнитель:** **QWEN-CODER**
**Commit/Operation:** `docs: record approved specification decisions`
Зафиксировать: тон bot (05 vs 07), `WEBHOOK_SECRET`/`WEBHOOK_PATH_SECRET`, cookie/fallback bearer из 03, порядок/источник шкал 2026.
**DoD:** Есть явное решение владельца по каждому спорному пункту.

### M0.02 — Создать новый GitHub repository и защитить main
**Исполнитель:** **OPENCODE**
**Commit/Operation:** `ops`
Новый repo/remote, protected main, PR required, force-push запрещён.
**DoD:** Работа идёт только через feature/fix branches.

### M0.03 — Создать QWEN.md для clean-build режима
**Исполнитель:** **QWEN-CODER**
**Commit/Operation:** `docs: add project agent rules`
Правила one-task-at-a-time, docs-first, роль QWEN/OpenCode, DoD, stop conditions.
**DoD:** Документ согласован и лежит в root.

### M0.04 — Настроить labels/milestones/issue conventions
**Исполнитель:** **OPENCODE**
**Commit/Operation:** `ops`
Создать labels `mvp`, `full`, `backend`, `frontend`, `db`, `infra`, `security`, `bug`.
**DoD:** Трекер позволяет однозначно связывать задачу с планом.

### M0.05 — Проверить `/docs` и сформировать traceability matrix
**Исполнитель:** **QWEN-CODER**
**Commit/Operation:** `docs: add requirements traceability matrix`
Для каждого обязательного требования указать docs section и будущий task ID.
**DoD:** Ни одно MVP-требование не осталось без владельца.

### M0.06 — Проверить официальные источники экзаменационных шкал 2026
**Исполнитель:** **OPENCODE**
**Commit/Operation:** `ops`
Подготовить источник и зафиксировать материалы, которые QWEN затем занесёт в seed.
**DoD:** Источники сохранены; seed не выполняется до этой проверки.

# MVP — этап M1: Инструментальная база, core и целевая БД
**Цель:** Получить чистый исполняемый backend foundation и целевую PostgreSQL schema.

### M1.01 — Зафиксировать Python 3.11
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: standardize python 3.11`

Обновить `pyproject`, Docker и tooling. Убрать расхождение между `^3.10` и Docker 3.12.

### M1.02 — Зафиксировать uv как package manager
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: migrate dependency management to uv`

Добавить lockfile и воспроизводимый install path.

### M1.03 — Не добавлять password/JWT dependencies
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: remove password and jwt dependencies`

Не добавлять `passlib`, `bcrypt`, `python-jose` и связанный код.

### M1.04 — Подтвердить target runtime dependencies
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: add target backend dependencies`

Добавить только необходимые целевому ТЗ пакеты: MyPy strict tooling, Ruff, TaskIQ stack, aioboto3, Pillow/pillow-heif, greenlet и прочее согласно `docs/02`.

### M1.05 — Ввести целевую структуру `core`
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: add core configuration primitives`

Создать:
- `core/config.py`
- `core/enums.py`
- `core/timeutils.py`
- `core/security.py`
- `core/logging.py`
- `core/texts.py`

Перенести только foundation-код, без массового business logic migration.

### M1.06 — Перейти на конфигурацию из ТЗ
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: align environment configuration with specification`

Перейти к `APP_ENV`, `DATABASE_URL`, `BOT_MODE`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `OWNER_TELEGRAM_ID`, `TEACHER_CONTACT_URL`, `PUBLIC_BASE_URL`, `SESSION_SECRET`, `S3_*`, `SENTRY_DSN`, `DEFAULT_TIMEZONE`, `BOT_USERNAME`, `SCHEDULE_HORIZON_WEEKS` и т.д.

### M1.07 — Ввести единый набор исключений
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: introduce domain exception hierarchy`

Добавить `PermissionDeniedError`, `NotFoundError`, `BusinessRuleError`, `ExternalServiceError` и целевые бизнес-ошибки по API spec.

### M1.08 — Ввести единый API error envelope
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add api error envelope`

Формат:
`{"error":{"code":"...","message":"...","details":{...}}}`

Добавить обработчики 400/401/403/404/409/413/415/422/429/500 и request-id.

### M1.09 — Ввести base DTO/schema слой
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: add role-specific api schemas`

Начать разделение response models по роли и use case. Не использовать одну универсальную модель пользователя для всех ролей.

### M1.10 — Перестроить ORM base/types
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: align orm primitives with postgres target`

Целевые принципы:
- BIGINT IDENTITY;
- `TIMESTAMPTZ`;
- JSONB где указано;
- единая enum policy;
- `updated_at` по требованиям;
- PostgreSQL-specific types/constraints.

### M1.11 — Создать целевые domain models
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add target domain models`

Покрыть таблицы из `docs/04`:
- references;
- users/student profiles/guardians/tokens;
- schedule/templates/participants;
- homeworks/materials/assignments/extensions/files;
- mock exam results;
- notifications/audit log.

### M1.12 — Пересоздать clean initial migration
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: replace legacy schema with target initial migration`

Если владелец подтвердил отсутствие требуемых production-данных, сделать одну чистую initial migration. Иначе этот commit не выполнять без отдельного migration strategy.

### M1.13 — Добавить PostgreSQL extensions/constraints baseline
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add postgres extensions and baseline constraints`

В том числе `btree_gist` и необходимые FK/unique/check constraints.

### M1.14 — Перенести репозитории на constructor-injected session
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: standardize repository session ownership`

Repository принимает session через constructor/context и никогда не делает `commit`.

### M1.15 — Перенести commit boundary в services
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: enforce service transaction boundaries`

Одна business operation = одна транзакция service. Middleware/routers/repositories не коммитят.

### M1.16 — Ввести `actor` в service contracts
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: add actor-aware service contracts`

Все операции, которые меняют данные или читают защищённые ресурсы, принимают actor/context и проверяют права на уровне service.

### M1.17 — Ввести `Notifier` interface
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add notifier abstraction`

Сервисы не импортируют aiogram. Пока можно иметь stub implementation.

### M1.18 — Создать `/api/v1` skeleton
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add versioned api skeleton`

Сформировать `/api/v1/auth`, `/reference`, `/student`, `/admin`, `/files` и `/health` без полной бизнес-реализации.

### M1.19 — Включить Ruff + MyPy strict + pre-commit
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: enforce backend quality tooling`

Сделать конфигурацию воспроизводимой и обязательной в CI.

# MVP — этап M2: Users, RBAC, Telegram Auth, invitations, privacy
**Цель:** Закрыть identity/security до добавления сложных бизнес-доменов.

### M2.01 — Реализовать enum ролей `owner/manager/student`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: replace legacy roles with target roles`

Удалить `admin` из domain API.

### M2.02 — Реализовать owner bootstrap
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: bootstrap first owner from telegram id`

Использовать `OWNER_TELEGRAM_ID`; сделать idempotent bootstrap script без ручного создания admin.

### M2.03 — Реализовать `student_profiles`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student profile domain`

Вынести student-specific fields из `users`, добавить timezone/status/archive attributes согласно ТЗ.

### M2.04 — Реализовать archive/restore
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add user archive and restore`

Архивированный пользователь не может аутентифицироваться и не должен получать active access.

### M2.05 — Реализовать Redis session store
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add server-side redis sessions`

Session ID хранится в `HttpOnly` cookie. Redis — source of truth.

### M2.06 — Подключить session auth dependency
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: authenticate api via server sessions`

Удалить использование Bearer JWT как primary browser auth.

### M2.07 — Добавить session revocation
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: revoke user sessions on identity changes`

Вызывать `revoke_all_for_user` минимум при:
- archive;
- role change;
- Telegram ID relink/change.

### M2.08 — Реализовать `POST /auth/telegram`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add telegram web auth endpoint`

Server-side validation initData + user resolution + session creation.

### M2.09 — Реализовать `POST /auth/link`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add browser link authentication`

Token-based invite login according to API spec.

### M2.10 — Реализовать invitation issuance
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student invitation issuance`

Endpoint/service for owner/manager; expiration; `web_login` purpose; creator audit.

### M2.11 — Исправить invite URL
**Исполнитель:** **QWEN-CODER**
**Commit:** `fix: build canonical telegram invite url`

Использовать конфигурируемый bot username и `https://t.me/<bot>?start=...`.

### M2.12 — Реализовать invitation revoke/list
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: manage student invitations`

`GET/POST/DELETE` согласно `/api/v1` contract.

### M2.13 — Реализовать `ConfirmRelinkState`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add telegram relink confirmation flow`

Никакой тихой перезаписи чужого Telegram ID.

### M2.14 — Добавить audit events для auth/link/archive
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: audit identity and access changes`

Хранить в PostgreSQL `audit_log`.

### M2.15 — Role-aware 404 policy
**Исполнитель:** **QWEN-CODER**
**Commit:** `fix: hide protected student existence from unauthorized roles`

Для чужих student resources возвращать 404, когда это требует ТЗ, а не 403.

### M2.16 — Разделить DTO по ролям
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: enforce role-specific user responses`

Student schemas не должны содержать finance/private staff-only fields.

### M2.17 — Удалить balance/lesson_price из student-facing auth models
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: remove financial fields from student api`

Это только удаление из public/student contracts; полный removal domain-функционала будет отдельной задачей в этапе 6.

### M2.18 — CSRF enforcement
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: enforce csrf origin protection`

Для mutating browser requests:
- обязательный корректный `Origin`;
- требование `X-Requested-With` согласно ТЗ;
- fail closed.

### M2.19 — Rate limits по доменному ключу
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement target rate limits`

Отдельно проверить:
- auth 10/min/IP;
- invite attempts 5/10m per telegram_id;
- files 30/10m user;
- REST 120/min user.

### M2.20 — Безопасные response headers и production OpenAPI policy
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: harden http security headers`

HSTS/CSP/frame-ancestors и закрытие `/openapi.json` в production.

### M2.21 — Auth/privacy integration suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover roles sessions relink archive and privacy`

Обязательные negative cases для owner/manager/student.

# MVP — этап M3: Расписание, групповые уроки, шаблоны и attendance
**Цель:** Реализовать расписание без гонок и с корректной временем/ценами.

### M3.01 — Reference subjects/exam basics
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add subject reference api`

CRUD/read endpoints согласно `/reference`.

### M3.02 — Schedule templates domain
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add schedule template domain`

Создание/редактирование/participants для recurring schedule.

### M3.03 — Lesson participant model
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add group lesson participants`

`lesson_participants` с attendance, billable, price_snapshot.

### M3.04 — Lesson create service
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: create lessons through schedule service`

Урок больше не создаётся напрямую из router/repository.

### M3.05 — Teacher overlap database constraint
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: prevent teacher lesson overlap in postgres`

Использовать exclusion constraint с `tstzrange` + `btree_gist`.

### M3.06 — Lesson uniqueness for generated template occurrences
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add template occurrence uniqueness`

UNIQUE `(template_id, start_at)` и идемпотентная генерация.

### M3.07 — Lesson lifecycle
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement lesson lifecycle`

`schedule/completed/cancelled` + completed/cancelled metadata.

### M3.08 — Attendance and billable flags
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: record attendance and billable state`

Для каждого участника отдельно.

### M3.09 — Price snapshot
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: snapshot participant lesson price`

При фиксации billable state сохранять цену в `lesson_participants.price_snapshot`. Не считать прошлый earning по текущей цене профиля.

### M3.10 — Reschedule operation
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement lesson reschedule`

Проверка конфликтов + audit + будущая интеграция с notification/outbox.

### M3.11 — Cancel operation
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement lesson cancellation`

Причина/metadata по ТЗ, без физического удаления.

### M3.12 — Detach overrides
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: support detached lesson overrides`

Изменённое occurrence не должно повторно затираться генератором template.

### M3.13 — Generate future lessons
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: generate lessons from templates`

Горизонт `SCHEDULE_HORIZON_WEEKS`, idempotency.

### M3.14 — Timezone-aware scheduling
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: calculate schedule in user timezone`

Стандарт хранения UTC-aware; отображение и day boundaries в timezone пользователя.

### M3.15 — DST regression suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover schedule timezone and dst transitions`

Проверить переходы DST и границы локального дня.

### M3.16 — Student `/today`
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student today endpoint`

Только student-visible data, без finance.

### M3.17 — Admin schedule endpoints
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin schedule api`

CRUD templates/lessons/participants/reschedule/cancel/complete.

### M3.18 — Schedule audit tests
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover group lessons conflicts and price snapshots`

Race/negative tests, teacher overlap, group participants, detached occurrence.

# MVP — этап M4: Домашние задания, S3 и файловый сервис
**Цель:** Реализовать полный lifecycle ДЗ и приватные файлы.

### M4.01 — Homework domain
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework domain`

`homeworks`, `homework_materials` и поля `kind`, `exam_type_id`, `max_score`, due mode и т.п.

### M4.02 — Homework assignments
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework assignments`

Отдельная выдача для каждого assignee.

### M4.03 — Assignment statuses
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement homework assignment state machine`

`assigned/submitted/needs_revision/graded/expired`.

### M4.04 — Group assignment
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: assign homework to groups`

Один homework может быть выдан нескольким студентам с отдельным состоянием каждого.

### M4.05 — Submission metadata
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework submission fields`

`submission_type`, `submitted_at`, comments, score/graded metadata и post-expiry grading data.

### M4.06 — Extension domain
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework deadline extensions`

Журнал расширений + максимум 2.

### M4.07 — Extend deadline service
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: enforce homework extension limit`

Код ошибки `homework_extension_limit`.

### M4.08 — Expiry service
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: expire overdue homework assignments`

Перевод в `expired` по дедлайну.

### M4.09 — Submission service
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: submit homework assignment`

Проверка состояния и правил просрочки согласно ТЗ.

### M4.10 — Return for revision
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: return homework for revision`

`needs_revision` + feedback.

### M4.11 — Grade homework
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: grade homework assignments`

Числовая оценка с validation range, `graded_by`, `graded_at`, комментариями.

### M4.12 — Teacher materials/files model
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework materials and files`

Не смешивать файл teacher material и student submission.

### M4.13 — S3 storage abstraction
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add private s3 file storage`

aioboto3; private bucket; object key abstraction.

### M4.14 — Local MinIO development storage
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: add minio development environment`

Только для local/integration use.

### M4.15 — MIME/content validation
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: validate uploaded file type and content`

Разрешённые типы: jpg/png/heic/pdf; проверка MIME + extension + decoded content.

### M4.16 — File size/count limits
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: enforce homework file limits`

≤10 MB на файл, ≤10 файлов на assignment.

### M4.17 — HEIC processing
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: convert heic uploads to jpeg`

Pillow + pillow-heif, с корректной обработкой ориентации/метаданных.

### M4.18 — Presigned URL endpoint
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add presigned file urls`

`/api/v1/files/{file_id}/url`, авторизация на каждую ссылку.

### M4.19 — Student homework API
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student homework api`

Списки/детали/submit/extend согласно spec; без staff-only данных.

### M4.20 — Admin homework API
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin homework api`

CRUD, assignments, materials, grading, return, extension, review queue.

### M4.21 — Homework negative-case suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover homework lifecycle and file constraints`

Проверить expiry, two extensions, over-limit files, invalid MIME, score range, role access.

# MVP — этап M5: Outbox, TaskIQ, scheduler и уведомления
**Цель:** Сделать уведомления durable, идемпотентными и управляемыми через outbox.

### M5.01 — Перейти с Arq на TaskIQ
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: migrate worker runtime to taskiq`

Удалить Arq после переноса минимального worker runtime.

### M5.02 — TaskIQ Redis broker
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: configure taskiq redis broker`

### M5.03 — Scheduler process
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add taskiq scheduler`

Выделенный scheduler как процесс/контейнер.

### M5.04 — Notification entity/outbox repository
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add notification outbox repository`

Поля включая type, payload, recipient, dedup key, status, retry metadata.

### M5.05 — Notification service
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add notification service`

Services создают outbox event, но не отправляют Telegram напрямую.

### M5.06 — Dispatcher with locking/dedup
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: dispatch notification outbox`

Надёжная дедупликация на БД, а не только Redis TTL.

### M5.07 — Retry policy
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add notification retry policy`

Повторы по ТЗ, статусы `sent/failed/skipped`.

### M5.08 — TelegramNotifier
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement telegram notifier`

Единый reusable Bot client/session strategy, без создания нового Bot per recipient.

### M5.09 — bot blocked handling
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: handle telegram bot blocked recipients`

Фиксировать `bot_blocked`/skipped state и не зацикливать retries.

### M5.10 — Quiet hours and timezone
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: enforce notification quiet hours`

Тихие часы 22:00–08:00 в локальном timezone пользователя, с правилами для urgent notifications.

### M5.11 — Lesson reminder exactly 30 minutes
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: send exact lesson reminders`

Проверка должна выполняться с минутной гранулярностью и отправлять reminder для `start_at` примерно ровно `now+30m`, с idempotent dedup.

### M5.12 — Homework deadline reminder 24h
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: send homework deadline reminders`

Не daily global reminder, а per-deadline 24h window.

### M5.13 — New homework notifications
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify students about new homework`

### M5.14 — Homework graded/revision notifications
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify students about homework review result`

### M5.15 — Lesson cancel/reschedule notifications
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify lesson schedule changes`

### M5.16 — Staff homework submitted/expired notifications
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify staff about homework events`

### M5.17 — Student joined notification
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify staff about student telegram link`

### M5.18 — Morning digest
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add staff morning digest`

08:00 local/targeted timezone policy, состав согласно ТЗ.

### M5.19 — Generate scheduled lessons job
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: schedule recurring lesson generation`

Использовать service, не дублировать business logic в task.

### M5.20 — Expire assignments job
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: schedule homework expiry job`

### M5.21 — Notify unmarked lessons job
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: notify about unmarked lessons`

### M5.22 — Cleanup tokens job
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: cleanup expired auth tokens`

### M5.23 — Heartbeat job
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add worker heartbeat`

### M5.24 — Scheduler/worker integration suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover outbox retries quiet hours and scheduler jobs`

Проверить idempotency, retry windows, timezone, blocked bot, duplicate events.

# MVP — этап M6: Пробники, отчёты, dashboard и финансы
**Цель:** Реализовать правильные экзамены и owner-only аналитику без balance/debtors.

### M6.01 — Exam types reference
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add exam type references`

4 типа экзаменов по ТЗ.

### M6.02 — Grade scale model
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add database driven grade scales`

Шкалы только в БД; код не содержит hardcoded threshold table.

### M6.03 — Populate verified grade scales
**Исполнитель:** **QWEN-CODER**
**Commit:** `data: add verified exam grade scales`

Перед commit сверить текущие данные с официальным источником, который назначен владельцем/ТЗ. Не вносить «предположительные» цифры.

### M6.04 — OGE geometry rule
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement oge geometry scoring rule`

Только если это прямо требуется `docs/04`.

### M6.05 — `max_primary` handling
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: handle exam maximum score rules`

Нестандартный максимум не конвертировать по неподходящей шкале.

### M6.06 — Exam result creation/update
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement mock exam result domain`

`mock_exam_results` и связь с assignment/result lifecycle.

### M6.07 — Auto-create exam result from mock-exam homework
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: create exam result from graded mock homework`

Запрещать ручное переопределение calculated grade, кроме предусмотренного ТЗ механизма.

### M6.08 — Exam endpoints
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add mock exam api`

CRUD/read/update/delete according to `/api/v1`.

### M6.09 — Student reports domain
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement student reports`

Недавний прогресс, weekly percent, on-time percentage, mock exam dynamics.

### M6.10 — Report aggregation queries
**Исполнитель:** **QWEN-CODER**
**Commit:** `perf: optimize report aggregations`

Избегать N+1 и ручного парсинга score strings.

### M6.11 — Dashboard foundation
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin dashboard metrics`

Локальное «сегодня», queue/review/deadline/unmarked/earnings metrics.

### M6.12 — Review queue and unmarked lessons widgets
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add dashboard operational queues`

Очередь проверки; прошедшие уроки без отметки.

### M6.13 — Upcoming deadlines 24h
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add dashboard upcoming deadlines`

Использовать реальные assignment due_at и timezone rules.

### M6.14 — Finance expected/earned queries
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: calculate owner finance from billable snapshots`

Формулы используют `price_snapshot`, а не current student price.

### M6.15 — Finance breakdowns
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add finance breakdowns and cancellation stats`

Owner-only view; earning/expected/cancellations according to spec.

### M6.16 — Finance CSV export
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add owner finance csv export`

Проверка доступа owner-only.

### M6.17 — Remove balance model fields
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: remove legacy balance fields`

Удалить из ORM/service/API/UI остатки `balance`, `debtors_flag`, `lesson_price` там, где они больше не нужны.

### M6.18 — Remove balance services/routes/tests
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: remove legacy balance domain`

Удалить `atomic_adjust_balance`, `add_balance`, `InsufficientBalanceError`, `/balance`, debtor dashboard paths и race tests.

### M6.19 — Remove balance-related bot texts/tasks
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: remove legacy balance messaging`

Убрать формулировки «спишется занятие», «баланс», «должник».

### M6.20 — Owner-only finance security suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: enforce finance owner-only access`

Owner success; manager/student negative cases; DTO/schema privacy checks.

### M6.21 — Exam/dashboard/report regression suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover exams reports dashboard and finance`

Включая grading thresholds, score ranges, timezone day boundaries, price snapshot calculations.

# MVP — этап M7: Telegram bot, меню, каталог и deep links
**Цель:** Сделать bot тонким транспортом и точкой входа.

### M7.01 — Bot client abstraction
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add telegram bot client abstraction`

Единая точка конфигурации API/proxy/webhook.

### M7.02 — AuthMiddleware
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add bot auth middleware`

Состояния guest/student/staff; единый user context.

### M7.03 — Role-aware command menus
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add role specific telegram menus`

Разные команды и кнопки для guest/student/staff.

### M7.04 — `setMyCommands` scopes
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: register telegram commands by chat scope`

Использовать BotCommandScopeChat где требует ТЗ.

### M7.05 — Guest `/start` flow
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement guest start flow`

Каталог + teacher contact + invite entry points.

### M7.06 — Student bot commands
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement student bot commands`

`/today`, `/hw`, `/app`, `/web`, `/help`, `/logout`, `/start` relink behavior согласно ТЗ.

### M7.07 — Staff bot commands
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: implement staff bot commands`

Staff должен получать staff-меню, а не student-меню.

### M7.08 — `/app` deep link
**Исполнитель:** **QWEN-CODER**
**Commit:** `fix: make app command open correct web app`

Не отправлять повторно главное меню.

### M7.09 — `/web` login
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add web login command`

Генерация/выдача browser login link согласно auth flow.

### M7.10 — Homework deep links
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add homework deep links`

Переход на конкретное ДЗ/assignment.

### M7.11 — Confirm relink FSM
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: connect telegram relink confirmation to bot`

Сервис + FSM + audit + session revocation.

### M7.12 — Catalog from database
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: load catalog from database`

Убрать статический `bot/catalog.py`.

### M7.13 — Catalog pagination callbacks
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add catalog inline pagination`

`◀ Назад / Далее ▶` через message edit + `callback.answer()`.

### M7.14 — Centralize bot texts
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: move bot texts to texts module`

Брендинг и тон из `docs/07`.

### M7.15 — Bot error handler and fallback
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add global bot error handling`

Global error handler; `callback.answer()`; fallback на сообщения вне сценария.

### M7.16 — `my_chat_member` and allowed updates
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: handle telegram chat membership updates`

Изменять `bot_blocked` состояние через bot events.

### M7.17 — Combine API + bot runtime model
**Исполнитель:** **QWEN-CODER**
**Commit:** `refactor: run api and bot in target application process`

Подготовить lifecycle/webhook model, не делая ещё production deployment.

### M7.18 — Webhook endpoint
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add telegram webhook endpoint`

`/telegram/webhook/{secret}` согласно спецификации.

### M7.19 — Bot integration tests
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: cover telegram role menus auth and relink`

# MVP — этап M8: React frontend и сквозная интеграция
**Цель:** реализовать Student/Admin UI после готовых backend contracts, затем пройти MVP acceptance.

### M8.01 — React/Vite TypeScript scaffold
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: scaffold frontend application`

Использовать стек из docs: React + TS + Vite + React Router + TanStack Query + Tailwind + shadcn + Recharts.

### M8.02 — Strict TypeScript/tooling
**Исполнитель:** **QWEN-CODER**
**Commit:** `chore: enforce strict frontend tooling`

No `any`, no `@ts-ignore`.

### M8.03 — Generated API types
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: generate frontend api types from openapi`

Добавить codegen path и drift check.

### M8.04 — Frontend API/query layer
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add typed api client and query layer`

TanStack Query; business logic не в UI components.

### M8.05 — Design tokens and UI primitives
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add design system primitives`

Перенести `docs/07`: tokens, `StatusBadge`, buttons, cards, forms, alerts.

### M8.06 — Student app shell
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student app shell`

Навигация и responsive layout.

### M8.07 — Student schedule screen
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student schedule screen`

Today/upcoming, local time formatting.

### M8.08 — Student homework screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student homework screens`

List/detail/upload/status/revision.

### M8.09 — Student reports screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student reports screens`

Recharts; без неверного предположения шкалы 1–5.

### M8.10 — Student profile/auth screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add student profile and auth screens`

`/login/:token`, session state, logout.

### M8.11 — Admin app shell
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin application shell`

Side navigation and role gating.

### M8.12 — Admin students/staff screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin people screens`

Students, staff, invitations, archive/restore.

### M8.13 — Admin schedule screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin schedule screens`

Templates/lessons/participants/reschedule/cancel/complete.

### M8.14 — Admin homework/review screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin homework screens`

Creation, assignments, review queue, grade, revision, extensions.

### M8.15 — Admin mock exam screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin mock exam screens`

DB-driven result UX.

### M8.16 — Admin dashboard
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add admin dashboard`

Queues, deadlines, unmarked lessons, earnings/expected.

### M8.17 — Catalog management
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add catalog management screens`

CRUD and ordering/pagination.

### M8.18 — Owner finance screens
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add owner finance screens`

Finance absent for manager/student navigation and payloads.

### M8.19 — Loading/error/empty/toast states
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: standardize frontend state feedback`

Все перечисленные states из design/frontend guide.

### M8.20 — Telegram Mini App integration
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: integrate telegram mini app context`

BackButton, theme, safe area, initData handoff.

### M8.21 — Frontend unit/component tests
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: add frontend component coverage`

Vitest + Testing Library + MSW.

### M8.22 — Playwright E2E baseline
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: add frontend end to end coverage`

Минимум: login, student schedule, homework submit, owner finance access, forbidden finance for student/manager.

### M8.23 — OpenAPI contract verification
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: verify openapi contract and operation ids`

Пути, operation IDs, response models, error codes.

### M8.24 — Security regression suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: add end to end security regression suite`

Проверить:
- initData;
- session revocation;
- archive;
- RBAC;
- 404 masking;
- CSRF;
- rate limits;
- file limits;
- private S3 URLs;
- no finance in student API.

### M8.25 — Full MVP acceptance suite
**Исполнитель:** **QWEN-CODER**
**Commit:** `test: add full mvp acceptance suite`

Сверить с Definition of Done и критериями MVP из roadmap.

## M1. OpenCode — эксплуатационные проверки после кодовых задач

### OM1.01 — Поднять чистую local toolchain
**Исполнитель:** **OPENCODE**
Python 3.11, uv, Node/pnpm, Docker/Compose; проверить версии.
**Зависит от:** После M1.01
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM1.02 — Проверить install из нуля
**Исполнитель:** **OPENCODE**
`uv sync --frozen`; `pnpm install --frozen-lockfile` после появления frontend.
**Зависит от:** После соответствующих lockfiles
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM1.03 — Поднять PostgreSQL 16/Redis 7 local
**Исполнитель:** **OPENCODE**
Проверить подключения из контейнеров и суть сети без внешних портов.
**Зависит от:** После M1.10
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M2. OpenCode — эксплуатационные проверки после кодовых задач

### OM2.01 — Smoke-test FastAPI + lifespan
**Исполнитель:** **OPENCODE**
Запустить app, `/health`, shutdown/restart.
**Зависит от:** После M2.18
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM2.02 — Проверить Redis session/FSM prerequisites
**Исполнитель:** **OPENCODE**
Redis persistence/TTL и connectivity.
**Зависит от:** После M2.05
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M3. OpenCode — эксплуатационные проверки после кодовых задач

### OM3.01 — Создать чистую PostgreSQL 16 database
**Исполнитель:** **OPENCODE**
Только через Docker/Compose; без ручного изменения схемы.
**Зависит от:** После M3.12
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM3.02 — Применить `alembic upgrade head`
**Исполнитель:** **OPENCODE**
На пустой БД, затем `downgrade` и повторный `upgrade`.
**Зависит от:** После M3.12
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM3.03 — Проверить constraints/indexes
**Исполнитель:** **OPENCODE**
EXCLUDE/UNIQUE/CHECK — через реальный PG.
**Зависит от:** После M3.13
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M4. OpenCode — эксплуатационные проверки после кодовых задач

### OM4.01 — Проверить real Redis session flow
**Исполнитель:** **OPENCODE**
Login → cookie → request → logout → revoke.
**Зависит от:** После M4.21
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM4.02 — Проверить Redis failure behavior
**Исполнитель:** **OPENCODE**
Убедиться, что rate-limit/auth деградируют только по описанному контракту.
**Зависит от:** После M4.21
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M5. OpenCode — эксплуатационные проверки после кодовых задач

### OM5.01 — Сгенерировать OpenAPI и TS types
**Исполнитель:** **OPENCODE**
Запустить backend export + `pnpm gen:api`; сравнить diff.
**Зависит от:** После M5.04
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM5.02 — Проверить CI contract drift
**Исполнитель:** **OPENCODE**
Запустить pipeline locally/CI и убедиться, что изменение schema.d.ts ловится.
**Зависит от:** После M5.07
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M6. OpenCode — эксплуатационные проверки после кодовых задач

### OM6.01 — Выполнить owner bootstrap на clean DB
**Исполнитель:** **OPENCODE**
Передать `OWNER_TELEGRAM_ID` только через environment.
**Зависит от:** После M6.02
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM6.02 — Провести invitation smoke test
**Исполнитель:** **OPENCODE**
Create invite → accept → relink conflict → confirm → revoke/session revoke.
**Зависит от:** После M6.10
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M7. OpenCode — эксплуатационные проверки после кодовых задач

### OM7.01 — Запустить schedule migration на реальном PG
**Исполнитель:** **OPENCODE**
Проверить teacher overlap и concurrent insert.
**Зависит от:** После M7.04
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM7.02 — Проверить генерацию horizon
**Исполнитель:** **OPENCODE**
Несколько недель, повторный запуск без дублей, DST case.
**Зависит от:** После M7.18
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

## M8. OpenCode — эксплуатационные проверки после кодовых задач

### OM8.01 — Поднять frontend dev server и backend proxy
**Исполнитель:** **OPENCODE**
Проверить login/navigation on localhost.
**Зависит от:** После M8.04
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM8.02 — Проверить Student/Admin screens
**Исполнитель:** **OPENCODE**
Chrome mobile widths + desktop 1280.
**Зависит от:** После M8.22
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM8.03 — Провести real-device Telegram test
**Исполнитель:** **OPENCODE**
iOS + Android: Mini App, cookie, BackButton, theme, safe area.
**Зависит от:** После M8.25
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

### OM8.04 — Провести MVP staging rehearsal
**Исполнитель:** **OPENCODE**
Чистый стенд, миграции, seed, full scenario without manual SQL.
**Зависит от:** После M8.25
**DoD:** результат команды/стенда зафиксирован в PR comment/issue; код не исправляется вручную в обход QWEN.

# FULL PROJECT — Stage 8 / Production и эксплуатация

### F1.01 — Nginx same-domain deployment
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add nginx frontend api routing`

React SPA + `/api/v1` + Telegram webhook on one domain.

### F1.02 — Production compose
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add production docker compose`

Target services:
- app;
- worker;
- scheduler;
- postgres;
- redis;
- nginx.

Не публиковать внутренние service ports наружу.

### F1.03 — Healthchecks and graceful lifecycle
**Исполнитель:** **QWEN-CODER**
**Commit:** `feat: add service healthchecks and graceful shutdown`

API, worker/scheduler readiness and proper lifecycle.

### F1.04 — Backup/restore tooling
**Исполнитель:** **QWEN-CODER**
**Commit:** `ops: add postgres backup and restore scripts`

Документировать проверку восстановления.

### F1.05 — JSON logs and Sentry without PII
**Исполнитель:** **QWEN-CODER**
**Commit:** `ops: add structured logging and sentry`

Без secrets и персональных данных в логах.

### F1.06 — CI frontend/backend pipeline
**Исполнитель:** **QWEN-CODER**
**Commit:** `ci: add full backend frontend verification pipeline`

Пайплайн:
1. install;
2. Ruff;
3. MyPy;
4. backend tests;
5. Alembic checks;
6. frontend lint/type/test;
7. OpenAPI/codegen drift;
8. Playwright/E2E where environment allows;
9. build images.

### F1.07 — Deployment documentation
**Исполнитель:** **QWEN-CODER**
**Commit:** `docs: document local staging and production operations`

README + runbooks: local, staging, prod, migrations, backup, rollback, health.

### F1.03 — Завершить automated forbidden-feature scan
**Исполнитель:** **QWEN-CODER**
Проверять отсутствие `balance`, `debtors`, `admin` role, browser JWT/Bearer, Flet, Arq, local upload storage и прямых aiogram imports в services.

### F1.04 — Финальный repository hygiene
**Исполнитель:** **QWEN-CODER**
Проверить secrets, artifacts, generated junk, lockfiles, reproducible install и clean git status.

### F1.05 — Release candidate verification
**Исполнитель:** **QWEN-CODER**
**Commit:** `release: verify mvp release candidate`

Последний прогон всех обязательных проверок на чистом окружении.

---

# 3. Отдельный сводный список ошибок, который QWEN-CODER должен закрыть

## Запуск и база

- Broken Alembic enum creation.
- `password_hash NOT NULL` при no-password product model.
- Некорректный lesson status enum.
- Naive timestamps вместо `TIMESTAMPTZ`.
- Downgrade defects в существующих migration constraints.
- SQLite tests masking PostgreSQL behavior.

## Архитектура и стек

- Poetry/Python 3.10/3.12 вместо uv/Python 3.11.
- Flet вместо React.
- Arq вместо TaskIQ.
- Отдельный bot polling процесс вместо target runtime/webhook model.
- Local filesystem вместо S3/private presigned URLs.
- Нет Nginx same-domain deployment.
- Нет строгих Ruff/MyPy/pre-commit checks.
- Нет structured JSON logs/Sentry.

## Слои

- Router → repository/DB direct access.
- Router-level commits.
- Middleware commits.
- Repository commit violations.
- Services without actor/authorization context.
- Direct aiogram usage from worker/services.
- Missing centralized exceptions/schemas/time/security modules.

## База данных

- Only legacy 5-table model.
- Missing reference, profile, guardian, template, participant, assignment, material, extension, file, result, notification, audit tables.
- Wrong user role model.
- Wrong lesson relation model.
- Missing teacher overlap constraint.
- Missing template occurrence uniqueness.
- Missing lesson participant billing/attendance/snapshot.
- Legacy string scores.
- Missing exam scale metadata.
- Missing archive/timezone/activity fields.

## Auth/RBAC/privacy

- JWT is primary browser auth instead of Redis session.
- Session cookie is not effective browser auth.
- Sessions are not revoked on identity changes.
- Archived users not enforced.
- Invitation issue flow absent.
- `web_login` absent.
- Relink silently overwrites Telegram ID.
- Missing relink confirmation/audit.
- Wrong 403/404 behavior.
- Student financial leakage.
- No proper owner bootstrap.
- Incomplete rate limiting.
- CSRF does not require Origin.
- CORS pattern conflicts with same-domain model.
- Missing security headers.
- Production OpenAPI not closed.

## API

- No `/api/v1`.
- Wrong endpoint layout.
- Standard FastAPI `detail` instead of error envelope.
- Missing pagination.
- Missing operation IDs/tags/summaries.
- Missing reference/admin/student/file endpoints.
- Missing staff/invitation/archive/reschedule/homework review/finance APIs.
- Physical lesson delete where spec expects cancellation.

## Business rules

- Balance/debtors exist although forbidden.
- Earnings use current price instead of snapshot.
- No group lessons.
- No attendance/is_billable.
- No reschedule/cancel reasons and notification contracts.
- No templates/generation/DST logic.
- Homework is single-table legacy model.
- No group assignments.
- No `needs_revision`/`expired`.
- No extension journal/max 2.
- No file count/size/type policy.
- No post-expiry grading behavior.
- Mock exam scales are hardcoded/wrong/incomplete.
- No DB-driven exam scales.
- No EGE scale/geometry/max-primary rules.
- No automatic mock exam result creation.
- Dashboard/reporting is incomplete and uses wrong timezone semantics.
- Catalog is static.

## Notifications/workers

- No notification outbox.
- Redis TTL dedup instead of durable dedup.
- Wrong reminder windows.
- Wrong homework deadline reminder cadence.
- Missing notification types.
- Missing retries/blocked state/quiet hours.
- Only 3/9 target jobs.
- New Bot per message.

## Bot

- No AuthMiddleware.
- Wrong role menus.
- Missing commands.
- Missing `setMyCommands` scopes.
- Missing fallback/error handler.
- Missing `my_chat_member` handling.
- `/app` wrong behavior.
- `/web` absent.
- No proper deep links.
- Catalog hardcoded.
- Text tone/branding mismatch.

## Frontend

- No React frontend at all.
- No generated API types.
- No target navigation/screens.
- No loading/error/empty states.
- No charts according to spec.
- No Mini App integration.
- Legacy Flet contains forbidden password/balance UI.

## Infra/CI/tests

- Incomplete CI.
- No production compose.
- No Nginx.
- No backups.
- No staging runbook.
- Postgres/Redis exposed publicly in compose.
- Hardcoded credentials/debug `print`.
- README inadequate.
- Tests lack required negative/security/business/regression coverage.

---

# 4. Какой порядок зависимостей считать обязательным

`E0.*` → `E1.*` → `E2.*` → `E3.*` → `E4.*` → `E5.*` → `E6.*` → `E7.*` → `E8.*`

Допускается технически подготовить часть следующего этапа раньше, только если это изолированный foundation commit и он не реализует следующий business flow раньше срока. Например, интерфейс `Notifier` можно создать на этапе 1, но реальные notification use cases — только после этапа 5.

### Нельзя делать раньше соответствующих этапов

- React screens раньше стабильного `/api/v1` contract.
- Finance UI раньше owner-only finance API.
- Homework upload UI раньше file/S3 API.
- Bot notifications раньше durable outbox/Notifier.
- Lesson generation worker раньше schedule service.
- Flet removal раньше React replacement.
- JWT removal раньше Redis-session auth.
- Balance cleanup раньше finance snapshot flow.

---

# 5. Критические контрольные точки для владельца

## После E0

Решены неоднозначности; проект реально поднимается; migration/test baseline воспроизводим.

## После E1

Архитектура и схема БД соответствуют целевой модели; legacy schema больше не является основой проекта.

## После E2

Безопасный вход и RBAC работают; student privacy соблюдается.

## После E3

Расписание является полноценным доменом, включая группы, overlap, attendance, billable, snapshots и timezone/DST.

## После E4

ДЗ и файлы полностью соответствуют ТЗ; локальное хранилище больше не используется.

## После E5

Надёжные уведомления и фоновые задачи работают через outbox + TaskIQ.

## После E6

Пробники, отчёты, dashboard и finance соответствуют бизнес-правилам; balance/debtors полностью удалены.

## После E7

Telegram bot является полноценным интерфейсом доступа и уведомлений по ролям.

## После E8

React + Nginx + CI/CD + backups + E2E образуют целевой продукт; legacy-стек удалён.

---

# 6. Definition of Done для каждого commit

Каждый commit считается завершённым только когда:

1. Реализована **только одна** задача этого плана.
2. Изменения соответствуют `/docs`.
3. Нет unrelated changes.
4. Добавлены/обновлены тесты для новой логики.
5. Пройдены релевантные lint/type/test checks.
6. Для DB changes пройдены migration checks.
7. Для API changes проверен OpenAPI contract.
8. Для security changes есть negative test.
9. Нет debug `print`, secrets или runtime artifacts.
10. `git diff --check` проходит.
11. В PR явно указано, что задача завершена и следующая задача **не выполнялась**.

---

# 7. Формат отчёта QWEN-CODER после каждого commit

```text
Task: E?.?? — <task title>

Changed:
- ...

Files:
- ...

Tests:
- command: ...
- result: PASS/FAIL

Migration/API/OpenAPI checks:
- ...

Commit:
- <sha> <message>

Remaining:
- only items outside current task

Next task was not started.
```

---

# 8. Финальный критерий готовности

Проект нельзя считать исправленным по принципу «старый код теперь запускается». Готовность означает соответствие целевой системе из `/docs`: целевая архитектура, PostgreSQL schema, server-side sessions, owner/manager/student RBAC, group lessons, homework assignments, S3, durable notifications, TaskIQ, DB-driven exams, React SPA, Nginx, CI/CD и security/privacy rules.

Критерий завершения — не количество закрытых тикетов, а отсутствие известных legacy-расхождений из аудита и прохождение полного acceptance/security/integration набора.

## FULL PROJECT — OpenCode production sequence

### F2.01 — Provision production VPS in RF
**Исполнитель:** **OPENCODE**
Ubuntu LTS, deploy user, SSH keys, UFW, fail2ban, Docker.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.02 — Configure production DNS and SSL
**Исполнитель:** **OPENCODE**
DNS + Let's Encrypt for staging/prod.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.03 — Create production S3 buckets
**Исполнитель:** **OPENCODE**
Files/backups, private policy, credentials outside repo.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.04 — Configure production secrets
**Исполнитель:** **OPENCODE**
`.env` chmod 600, GitHub environments/secrets.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.05 — Deploy staging via CI
**Исполнитель:** **OPENCODE**
Pull images, start compose, migration step, health.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.06 — Configure production webhook
**Исполнитель:** **OPENCODE**
BotFather + webhook secret header + allowed updates.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.07 — Run production smoke
**Исполнитель:** **OPENCODE**
Owner login, invite, Mini App, homework file, notification.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

### F2.08 — Run backup/restore drill
**Исполнитель:** **OPENCODE**
Create backup, restore staging, verify app.
**DoD:** операция воспроизводима; секреты не попали в Git; результат зафиксирован.

# FULL PROJECT — F3: Родители / guardian role

### F3.01 — Документировать parent role, видимость данных и auth contract до кода.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F1.10
**DoD:** Спека утверждена владельцем.

### F3.02 — Реализовать parent auth/session только после approval.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F3.01
**DoD:** Parent не получает teacher notes/finance.

### F3.03 — Добавить parent API с отдельными DTO.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F3.02
**DoD:** Role isolation покрыта тестами.

### F3.04 — Добавить parent frontend screens.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F3.03
**DoD:** UI mobile-first и privacy-safe.

### F3.05 — Провести parent staging acceptance.
**Исполнитель:** **OPENCODE**
**Зависит от:** F3.04
**DoD:** Нет cross-role leakage.

# FULL PROJECT — F4: Второй мессенджер / MAX adapter

### F4.01 — Убрать Telegram-specific assumptions из notification contracts.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F1.01
**DoD:** Business services channel-neutral.

### F4.02 — Создать messenger adapter interface.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F4.01
**DoD:** Telegram adapter остаётся рабочим.

### F4.03 — Получить sandbox credentials/endpoint approved channel.
**Исполнитель:** **OPENCODE**
**Зависит от:** F4.02
**DoD:** Secrets outside repo.

### F4.04 — Реализовать второй transport adapter.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F4.03
**DoD:** Нет aiogram dependencies.

### F4.05 — Добавить integration/failure tests.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F4.04
**DoD:** Outbox survives channel failure.

# FULL PROJECT — F5: Расширение экзаменов и ежегодное обновление шкал

### F5.01 — Документировать annual scale update procedure.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F1.04
**DoD:** Есть checklist official-source verification.

### F5.02 — После публикации взять официальные данные следующего года.
**Исполнитель:** **OPENCODE**
**Зависит от:** F5.01
**DoD:** Источник сохранён.

### F5.03 — Добавить новые rows/versions в grade_scales.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F5.02
**DoD:** Старые years остаются доступными.

### F5.04 — Добавить regression vectors.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F5.03
**DoD:** Все boundary values покрыты.

### F5.05 — Добавить новый exam type по утверждённой спецификации.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F5.03
**DoD:** No hardcoded exam switch.

### F5.06 — Сделать UI/filters динамическими по exam_types.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F5.05
**DoD:** UI не предполагает ровно 4 типа.

# FULL PROJECT — F6: Multi-teacher isolation

### F6.01 — Зафиксировать teacher-scoping policy до изменения authorization.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** Owner approval
**DoD:** Scope semantics documented.

### F6.02 — Добавить server-side teacher scope в services/repositories.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F6.01
**DoD:** Cross-teacher data blocked.

### F6.03 — Добавить negative cross-teacher tests.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F6.02
**DoD:** All protected resources covered.

### F6.04 — Добавить staff UI scoping/filtering.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F6.03
**DoD:** Frontend not security layer.

# FULL PROJECT — F7: Шаблоны ДЗ / банк заданий

### F7.01 — Спроектировать approved template/bank model.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** Owner approval
**DoD:** Spec before schema.

### F7.02 — Добавить migration/repository/service.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F7.01
**DoD:** Existing issued homework unchanged.

### F7.03 — Реализовать clone/create-from-template snapshot.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F7.02
**DoD:** Editing template doesn't mutate issued homework.

### F7.04 — Добавить admin search/filter UI.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F7.03
**DoD:** Business logic server-side.

### F7.05 — Тесты cloning/versioning.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F7.03
**DoD:** Regression green.

# FULL PROJECT — F8: iCal / календарная выгрузка

### F8.01 — Зафиксировать feed token/privacy model.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** Owner approval
**DoD:** Token lifecycle approved.

### F8.02 — Implement read-only iCal feed.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F8.01
**DoD:** No private notes/finance.

### F8.03 — Implement revoke/rotate feed tokens.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F8.02
**DoD:** Revocation effective immediately.

### F8.04 — Timezone/DST/cancel/reschedule tests.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F8.03
**DoD:** Feed matches app state.

# FULL PROJECT — F9: UX/performance hardening

### F9.01 — Accessibility audit and fixes.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** M8
**DoD:** Touch targets, labels, contrast, keyboard flow.

### F9.02 — Responsive audit 360/390/768/1280.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F9.01
**DoD:** No critical overflow.

### F9.03 — Audit loading/error/empty/offline/submitting states.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F9.02
**DoD:** All major screens uniform.

### F9.04 — Bundle/query optimization and N+1 audit.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F9.03
**DoD:** Student does not receive admin bundle unnecessarily.

### F9.05 — Run periodic staging performance smoke.
**Исполнитель:** **OPENCODE**
**Зависит от:** F9.04
**DoD:** No regressions at target scale.

# FULL PROJECT — F10: Compliance/data lifecycle readiness

### F10.01 — Create technical data inventory and role-visibility matrix.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** M6,M8
**DoD:** Actual API/schema matches inventory.

### F10.02 — Document archive/delete/restore procedures.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F10.01
**DoD:** Operator-ready runbook.

### F10.03 — Apply retention settings to backups/logs/storage.
**Исполнитель:** **OPENCODE**
**Зависит от:** F10.02
**DoD:** Retention verified.

### F10.04 — Add PII leakage regression checks for API/log/Sentry.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F10.01
**DoD:** Forbidden data triggers failures.

### F10.05 — Prepare privacy-policy technical integration points.
**Исполнитель:** **QWEN-CODER**
**Зависит от:** F10.01
**DoD:** No invented legal claims.

### F10.06 — Run owner/legal checklist before wide launch.
**Исполнитель:** **OPENCODE**
**Зависит от:** F10.01
**DoD:** Legal decisions recorded.

# 10. Финальные Gate'ы

## MVP Gate
- [ ] Чистая PostgreSQL 16 поднимается с нуля; `alembic upgrade head` проходит; схема соответствует `04`.
- [ ] Redis используется для server sessions, FSM, TaskIQ broker и rate limits.
- [ ] Invite-only auth, relink, `/web`, logout, archive/session revoke работают.
- [ ] Student/manager DTO не содержат finance/private fields; чужие данные маскируются 404.
- [ ] Group lessons, teacher overlap, templates, DST, attendance, billable и price snapshot работают на реальном PG.
- [ ] Homework lifecycle, files, extensions≤2, expiry и post-expiry manual grade работают.
- [ ] Exam scoring — DB-driven; geometry/max-primary rules покрыты.
- [ ] Outbox/TaskIQ/retries/quiet hours/dedup/block handling работают.
- [ ] React Student/Admin apps работают в браузере и Telegram; generated API types актуальны.
- [ ] CI зелёный; Playwright critical path проходит; staging acceptance проходит без ручного SQL.

## Full Project Gate
- [ ] Production deploy воспроизводим из Git tag и не публикует DB/Redis наружу.
- [ ] Backup/restore drill успешен; rollback/migration runbook проверен.
- [ ] Sentry/uptime/heartbeat работают без PII.
- [ ] Все approved post-MVP функции имеют отдельный контракт, тесты и acceptance.
- [ ] Ежегодное обновление экзаменационных шкал выполняется из официальных источников без hardcoded thresholds.

# 11. Stop conditions
- Конфликт документов или бизнес-правил.
- Изменение стека/зависимостей без approval.
- Деструктивная миграция или риск потери данных.
- Неизвестное падение на real PostgreSQL/Redis/S3/Telegram.
- Незакоммиченные чужие изменения в рабочем дереве.
- Нехватка credentials/access.
- Задача требует несвязанного рефакторинга.

# 12. Финальный принцип
**Не латать legacy — строить target system. Сначала docs/decision → models/migrations → services → API/bot/worker → frontend → real-environment validation → release. После каждой атомарной задачи — проверка, commit, PR, merge, stop.**