# LOCAL_ENV — чек-лист локального окружения

> Этап **S1.03** (проверка инструментов перед началом разработки).
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
| 13 | `mc` (MinIO Client) | RELEASE.2025-08-13T08-35-41Z | ДА | `C:\Users\user\AppData\Local\Programs\MinIO\mc.exe`, добавлен в User `PATH`. См. §4 |
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
- **PostgreSQL 18.3 вместо 16.** ТЗ требует «PostgreSQL 16+», поэтому 18 подходит. Обратите внимание: хостовый PG 18 и контейнер `postgres:16` из `docker-compose.yml` конфликтуют по порту 5432 — см. §6, п. 1.

---

## 6. Известные блокеры и находки

Всё из этого списка **не входило** в объём S1.03 и намеренно не исправлялось здесь — требует отдельных задач.

1. **Конфликт портов: 5432 занят хостовым PostgreSQL 18, 6379 — контейнером чужого стека.** На машине уже работает посторонний стек `lms_tutor` (`lms_api`, `lms_bot`, `lms_worker`, `lms_webapp`, `lms_postgres` на **15432**, `lms_redis` на **6379**, проект запущен ~3 недели назад). `docker compose up -d postgres redis minio` из этого репозитория упадёт на биндинге 5432 и 6379.
   Перед S3.03 нужно решить: либо остановить хостовый PG 18 и стек `lms_tutor`, либо убрать из `docker-compose.yml` `ports:` у `postgres` (внутри compose-сети имя сервиса уже работает без публикации порта).

2. **`docker-compose.yml` содержит устаревший атрибут `version: "3.8"`.** Compose v5 печатает предупреждение:
   `the attribute 'version' is obsolete, it will be ignored`. Поле можно удалить.

3. **`pyproject.toml` не собирается как пакет.** Нет секции `[tool.hatch.build.targets.wheel]` с `packages`, поэтому `hatchling` не может определить состав дистрибутива:
   ```
   ValueError: Unable to determine which files to ship inside the wheel
   ```
   Из-за этого не работает `uv run` / `uv sync` внутри репозитория. Нужно добавить `packages = ["src"]`.

4. **`docker-compose.yml` ссылается на `Dockerfile` в корне, которого нет** (`app`, `worker`, `scheduler` используют `build: dockerfile: Dockerfile`). На `docker compose up` для сервисов приложения сборка упадёт.

5. **Аутентификация Docker-контекста.** `docker context ls` показывает активный `desktop-linux`. Если демон перезапущен или WSL выключен, `docker` вернёт `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine` — это признак незапущенного Docker Desktop, а не поломки установки.

---

## 7. Повторная проверка

```powershell
git --version; gh auth status; py -3.11 --version; uv --version
node --version; corepack --version; pnpm --version
docker version; docker compose version; docker info
psql --version; pg_isready; jq --version; mc --version; curl.exe --version
docker run --rm hello-world
docker compose exec redis redis-cli ping
```

---

## 8. Связанные документы

- `docs/02_tech_stack.md` — целевые версии стека.
- `docs/10_deployment_and_ops.md` — эксплуатация и запуск.
- `docs/MY_LMS_BUILD_PLAN_QWEN_OPENCODE.md` — этап S1.03 (источник требований), этап S3.03 — развёртывание инфраструктуры.