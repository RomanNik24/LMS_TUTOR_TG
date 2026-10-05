# LOCAL_ENV — чек-лист локального окружения

> Первоначально — этап **S1.03** (проверка инструментов перед началом разработки).
> Обновлено 2026-10-05 после выполнения этапов **S0.08 – S0.11**: инфраструктура поднята,
> найденные в §6 блокеры закрыты.
>
> Требование ТЗ: установленный dev-инструментарий, рабочий Docker, доступность Docker для `testcontainers`.

- **Дата проверки:** 2026-10-05
- **Хост:** Windows 11 Домашняя (10.0.26300, x64), WSL 2.7.14.0
- **Docker:** Docker Desktop (WSL2 backend), Linux-контейнеры

---

## 1. Таблица инструментов

| # | Инструмент | Версия | ОК | Путь / примечание |
|---|---|---|---|---|
| 1 | `git` | 2.53.0.windows.1 | ДА | `C:\Program Files\Git\cmd\git.exe` |
| 2 | `gh` | 2.102.0 (2026-09-30) | ДА | Авторизован: `Nikolnik24`, scopes `repo`, `admin:public_key`, `gist`, `read:org`. Операции — по SSH |
| 3 | `python3.11` | 3.11.9 | ДА | `C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe`. Вызов: `py -3.11` (см. §4) |
| 4 | `uv` | 0.12.23 (2026-10-03) | ДА | Установлен через `winget` (`astral-sh.uv`) |
| 5 | `node` | v24.15.0 | ДА | Требование ТЗ — `>= 20`, выполнено |
| 6 | `corepack` | 0.34.6 | ДА | Штатный, в составе Node.js |
| 7 | `pnpm` | 12.8.1 | ДА | Установлен через `winget` (`pnpm.pnpm`), см. §4 |
| 8 | `docker` | 29.8.0 (build 88096ef) | ДА | CLI + работающий демон |
| 9 | `docker compose` | v5.5.1 | ДА | Плагин Compose v2 |
| 10 | `psql` | 18.3 | ДА | `C:\Program Files\PostgreSQL\18\bin\psql.exe`, добавлен в User `PATH` |
| 11 | `pg_isready` | 18.3 | ДА | Там же. Отвечает `accepting connections` на `:5432` |
| 12 | `redis-cli` | 7.4.11 | ДА | **Не нативно**, а через Docker: `docker compose exec redis redis-cli ping`. См. §5 |
| 13 | `mc` (MinIO Client) | RELEASE.2025-08-13T08-35-41Z | ДА | `C:\Users\user\AppData\Local\Programs\MinIO\mc.exe`, добавлен в User `PATH`. Используется как S3-клиент к SeaweedFS. См. §4, §6.3 |
| 14 | `curl` | 8.21.0 (Windows, Schannel) | ДА | Встроен в Windows. В PowerShell — псевдоним `curl` → `Invoke-WebRequest`; для CLI-совместимости использовать `curl.exe` |
| 15 | `jq` | 1.8.2 | ДА | Установлен через `winget` (`jqlang.jq`) |

**Итог: 15/15 позиций закрыты.**

---

## 2. Docker и testcontainers

| Проверка | Результат |
|---|---|
| Демон запущен | `docker info` → Server `29.8.0`, OS `linux`, Arch `x86_64` |
| `docker run hello-world` | **ДА** — `Hello from Docker!` (образ `sha256:5e230903…` скачан и запущен) |
| `docker compose version` | `v5.5.1` |
| Контекст по умолчанию | `desktop-linux` → `npipe:////./pipe/dockerDesktopLinuxEngine` |

### Проверка testcontainers

Выполнен реальный запуск контейнера через библиотеку `testcontainers` под Python 3.11.9:

```
python      = 3.11.9
image       = postgres:16-alpine
status      = RUNNING
mapped_port = 58315          # эфемерный порт, конфликтов с хостом нет
elapsed     = 135.1s
RESULT      = TESTCONTAINERS_OK
```

Контейнер после проверки остановлен. Вывод: **Docker доступен для `testcontainers`** — требование ТЗ выполнено.

Скрипт проверки лежит вне репозитория (в `%TEMP%\opencode\tc_check.py`), чтобы не засорять проект. Повторить проверку:

```powershell
uv run --python 3.11 --with testcontainers python tc_check.py
```

> Запускать из каталога вне репозитория — см. §6, п. 3.

---

## 3. Что установлено в этой сессии

Доступно было штатно: `git`, `gh`, `node`/`npm`/`corepack`, Docker Desktop, PostgreSQL 18.3.
Доставлено (все — штатными средствами ОС, winget, без ручной распаковки и без прав администратора):

| Пакет | Команда |
|---|---|
| uv 0.12.23 | `winget install --id astral-sh.uv --exact` |
| Python 3.11.9 | `winget install --id Python.Python.3.11 --exact` |
| jq 1.8.2 | `winget install --id jqlang.jq --exact` |
| pnpm 12.8.1 | `winget install --id pnpm.pnpm --exact` |

Изменения в системе:

- `C:\Program Files\PostgreSQL\18\bin` добавлен в **User** `PATH` (чтобы работали `psql`, `pg_isready`).
- `C:\Users\user\AppData\Local\Programs\MinIO` добавлен в **User** `PATH` (чтобы работал `mc`).
- Менеджер `winget` сам обновил User `PATH` для `uv`, `jq`, `pnpm`.

---

## 4. Особенности Windows

1. **PATH не подхватывается в открытой сессии.** `winget` и `SetEnvironmentVariable` пишут в реестр, а PowerShell 5.1 читает `PATH` при старте. В уже открытом терминале новые команды не появятся — нужен новый терминал, либо перечитать переменную:
   ```powershell
   $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
   ```

2. **`python3.11` не существует как команда.** Установщик Python для Windows создаёт только `python.exe` и регистрирует лаунчер `py`. Проверка версии: `py -3.11 --version`. Установлены две версии: `3.11.9` (нужна по ТЗ) и `3.13.13` (была в системе). Активна по умолчанию **3.13.13** — для проекта всегда указывать 3.11 явно.

3. **`pnpm` поставлен через winget, а не через `corepack enable`.** Штатный `corepack enable pnpm` падает с `EPERM` — запись шимов требует прав администратора в `C:\Program Files\nodejs`. `winget` обходит это сам. `corepack` при этом остаётся доступен и может управлять версиями pnpm по `packageManager` в `package.json` после появления фронтенда.

4. **`mc` пришлось ставить вручную** — winget-пакет `MinIO.Client` не работает: MinIO убрал прямую раздачу бинарей, upstream-URL отдаёт `HTTP 410 Gone`. Клиент взят из **официального GitHub-релиза** `minio/mc` (та же версия `RELEASE.2025-08-13T08-35-41Z`, которую пытался поставить winget), контрольная сумма сверена с приложенным `.sha256sum`:
   ```
   c8db13ebeda31497f354c0e950809db0ae9b2a2a69b8afee68c128c37300c157  mc.RELEASE.2025-08-13T08-35-41Z
   ```
   Это единственное отступление от «только штатные средства ОС» — пакетный менеджер ОС физически не может поставить этот инструмент.

---

## 5. Решения по составу

- **`redis-cli` не ставится нативно.** В `winget` пакет `Redis.Redis` — это сборка **3.0.504 от 2016 года**, а ТЗ требует **Redis 7**. Инструмент доступен из контейнера той же версии, что и сервис: `docker compose exec redis redis-cli ping`. Проверено: `redis-cli 7.4.11`.
- **`aws-cli` не ставится.** ТЗ формулирует пункт как «`mc` (MinIO client) **или** `aws-cli`» — требование закрыто вариантом `mc`.
- **PostgreSQL 18.3 вместо 16.** ТЗ требует «PostgreSQL 16+», поэтому 18 подходит. Хостовый PG 18 конфликтовал с контейнером `postgres:16` по порту 5432; служба `postgresql-x64-18` остановлена и переведена в режим запуска «Вручную» (см. §6, п. 1).

---

## 6. Блокеры и находки: статус

### 6.1. Закрыто в S0.08 – S0.11

1. **Конфликт портов 5432 (хостовый PostgreSQL 18).** Служба `postgresql-x64-18` остановлена, тип запуска изменён на «Вручную». Порт 5432 освобождён и занят контейнером `postgres:16`.
   Возврат к хостовому PG при необходимости:
   ```powershell
   Set-Service postgresql-x64-18 -StartupType Automatic; Start-Service postgresql-x64-18
   ```
   Посторонний стек `lms_tutor`, ранее занимавший 6379, к моменту S0.11 уже был удалён — том `lms_tutor_postgres_data` сохранён.

2. **`docker-compose.yml` содержал устаревший атрибут `version: "3.8"`.** Удалён из `docker-compose.yml` и `docker-compose.prod.yml`. Compose больше не печатает `the attribute 'version' is obsolete`.

3. **`pyproject.toml` не собирался как пакет.** Устранено через `[tool.uv] package = false` (приложение запускается из исходников, сборка дистрибутива не требуется). Дополнительно: единый `[dependency-groups].dev`, настройки Ruff перенесены в `[tool.ruff.lint]`. `uv sync --frozen` и `uv run` работают.

4. **Отсутствовал `Dockerfile` в корне.** Создан multi-stage образ бэкенда на `python:3.11-slim` + `uv 0.12.23`, непривилегированный пользователь `app` (uid 1001), `HEALTHCHECK` на `/health`, запуск `uvicorn src.manifest:app`. Добавлен `.dockerignore`.

### 6.2. Отклонение от ТЗ: MinIO заменён на SeaweedFS

ТЗ предписывает MinIO для локального S3. Образы `minio/minio` и `minio/mc` **удалены из Docker Hub в сентябре 2026**, а анонимный pull с `quay.io/minio` больше не работает:

```
Error response from daemon: pull access denied for minio/minio, repository does not exist or may require 'docker login'
Error response from daemon: failed to resolve reference "quay.io/minio/minio:latest":
  unexpected status from HEAD request to https://quay.io/v2/minio/minio/manifests/latest: 401 Unauthorized
```

Дополнительно: репозиторий MinIO CE архивирован (апрель 2026), образ заморожен на `RELEASE.2025-09-07` и содержит неисправленную CVE-2025-62506 (CVSS 8.1).

**Решение:** в локальной разработке используется **SeaweedFS** (`chrislusf/seaweedfs:latest`, лицензия Apache-2.0) — S3-совместимый сервер в одном контейнере. Это не влияет на код приложения: он работает через S3 API, а в проде по ТЗ используется реальное хранилище (Timeweb/Selectel, см. `S3_ENDPOINT_URL` в `.env.example`).

| Было | Стало |
|---|---|
| `minio/minio:latest`, S3 на `:9000`, UI на `:9001` | `chrislusf/seaweedfs:latest`, S3 на `:8333`, UI на `:8888` |
| сервис `minio-init` на образе `minio/mc` | бакет создаётся локальным `mc` вручную (см. §6.3) |
| `S3_ENDPOINT_URL=http://minio:9000` | `S3_ENDPOINT_URL=http://s3:8333` |

Локальные креды остались `minioadmin` / `minioadmin` (значение по умолчанию, совпадает с `.env.local`); в проде они не используются.

### 6.3. Создание бакета `lms-files`

Одноразовый init-сервис на `minio/mc` больше невозможен, поэтому бакет создаётся локальным клиентом `mc`:

```powershell
mc alias set local-s3 http://localhost:8333 minioadmin minioadmin
mc mb --ignore-existing local-s3/lms-files
mc ls local-s3
```

### 6.4. Остаётся на будущее

5. **Аутентификация Docker-контекста.** `docker context ls` показывает активный `desktop-linux`. Если демон перезапущен или WSL выключен, `docker` вернёт `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` — это признак незапущенного Docker Desktop, а не поломки установки.

6. **Сервис `migrate` не запустится до S1.02.** В репозитории ещё нет `alembic.ini` и каталога `scripts`, поэтому команда `alembic upgrade head` завершится ошибкой. На S0.11 это не проверялось.

7. **`frontend/package.json` фиксирует `pnpm@8.10.0`, установлен `pnpm 12.8.1`.** Расхождение закроется на S0.16 вместе с `pnpm-lock.yaml`.

8. **`ruff format --check .` сообщает `30 files would be reformatted`.** Форматирование намеренно не смешивалось с инфраструктурными коммитами.

---

## 7. Текущее состояние стека

`docker compose up -d postgres redis s3` — все три сервиса `healthy`:

| Контейнер | Состояние | Проверка |
|---|---|---|
| `lms_tutor_tg-postgres-1` | `healthy` | `pg_isready -U postgres` → `accepting connections` |
| `lms_tutor_tg-redis-1` | `healthy` | `redis-cli ping` → `PONG` |
| `lms_tutor_tg-s3-1` | `healthy` | `mc ls local-s3` → `lms-files/` |

Версия PostgreSQL в контейнере: `16.15 (Debian 16.15-1.pgdg13+2)`.
Расширение `btree_gist` создано: `docker exec lms_tutor_tg-postgres-1 psql -U postgres -d lms -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"`.

Сервисы `app`, `worker`, `scheduler` и `migrate` намеренно не поднимаются: `migrate` требует `alembic.ini` (S1.02).

---

## 8. Повторная проверка

```powershell
git --version; gh auth status; py -3.11 --version; uv --version
node --version; corepack --version; pnpm --version
docker version; docker compose version; docker info
psql --version; jq --version; mc --version; curl.exe --version
docker run --rm hello-world
Get-Service postgresql-x64-18
docker compose ps
docker compose exec redis redis-cli ping
docker exec lms_tutor_tg-postgres-1 pg_isready -U postgres
mc ls local-s3
```

---

## 9. Связанные документы

- `docs/02_tech_stack.md` — целевые версии стека.
- `docs/10_deployment_and_ops.md` — эксплуатация и запуск.
- `docs/MY_LMS_BUILD_PLAN_QWEN_OPENCODE.md` — этапы S0.08 – S0.11 и S1.03 (источник требований), S3.03 — развёртывание инфраструктуры.