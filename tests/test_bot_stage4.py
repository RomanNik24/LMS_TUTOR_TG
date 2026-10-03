"""Тесты Этапа 4: бот на RedisStorage + команды /schedule, /homeworks, /app, каталог.

Проверяют:
1. Redis-совместимость FSM-хранилища бота (реальный redis-server из docker-compose;
   если недоступен — fakeredis) — состояния переживают рестарт процесса.
2. Импорт и сборку диспетчера бота (RedisStorage, key_builder, роутеры base+info).
3. Работу обработчиков info-роутера на in-memory БД (SQLite): расписание, ДЗ,
   права доступа для гостей, клавиатуры с корректным web_app URL.
"""

import os

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from aiogram.fsm.storage.base import StorageKey  # noqa: E402
from aiogram.types import TelegramObject, User as TgUser  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.bot.catalog import CATALOG, render_catalog  # noqa: E402
from src.bot.keyboards import get_guest_keyboard, get_main_keyboard  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.db.models import (  # noqa: E402
    Homework,
    HomeworkStatusEnum,
    Lesson,
    LessonStatusEnum,
    RoleEnum,
    User,
)



# ---------------------------------------------------------------------------
# 1. RedisStorage: состояние реально лежит в Redis
# ---------------------------------------------------------------------------


def _redis_available() -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", 6379), timeout=0.5):
            return True
    except OSError:
        return False


@pytest_asyncio.fixture
async def fsm_storage():
    """RedisStorage бота поверх реального Redis (или fakeredis в CI)."""
    from aiogram.fsm.storage.redis import RedisStorage

    if _redis_available():
        from redis.asyncio import Redis

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        storage = RedisStorage(redis=redis)
        yield storage
        await storage.close()
    else:
        import fakeredis.aioredis

        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        storage = RedisStorage(redis=redis)
        yield storage
        await redis.aclose()


@pytest.mark.asyncio
async def test_fsm_state_persists_in_redis(fsm_storage):
    """set_state пишет ключи в Redis; данные читаются после 'рестарта'."""
    key = StorageKey(bot_id=1, chat_id=555, user_id=555)
    await fsm_storage.set_state(key=key, state="LoginStates:wait_for_login")
    await fsm_storage.update_data(key=key, data={"login": "petrov"})

    current = await fsm_storage.get_state(key=key)
    assert current == "LoginStates:wait_for_login"

    data = await fsm_storage.get_data(key=key)
    assert data["login"] == "petrov"

    # Ключи реально лежат в Redis (значит переживают рестарт процесса бота)
    redis_client = fsm_storage.redis
    keys = await redis_client.keys("fsm:*555*")
    assert keys, "FSM-состояние не найдено в Redis"

    await fsm_storage.set_state(key=key, state=None)
    assert await fsm_storage.get_state(key=key) is None


def test_key_builder_uses_user_id():
    """key_builder из main.py строит ключ по user_id (фикс для ЛС-диалогов)."""
    from src.bot.main import _build_storage  # проверка, что модуль собирается

    assert callable(_build_storage)

    event_context = {
        "from_user": TgUser(id=42, is_bot=False, first_name="T"),
        "chat": type("C", (), {"id": 99})(),
    }
    fake_bot = type("B", (), {"id": 1})()

    # Извлекаем наш key_builder, не подключаясь к Redis: читаем исходник main.py
    import inspect

    from src.bot import main as bot_main

    src = inspect.getsource(bot_main._build_storage)
    assert "user_id=event_context[\"from_user\"].id" in src
    assert "chat_id=event_context[\"chat\"].id" in src

    # Контракт StorageKey: поля соответствуют user_id/chat_id из апдейта
    sk = StorageKey(bot_id=1, user_id=42, chat_id=99)
    assert (sk.bot_id, sk.user_id, sk.chat_id) == (1, 42, 99)


# ---------------------------------------------------------------------------
# 2. Диспетчер бота собирается (RedisStorage + middleware + оба роутера)
# ---------------------------------------------------------------------------


def test_dispatcher_build_imports_cleanly():
    """main.py импортируется; handlers.info зарегистрирован вместе с base."""
    import src.bot.handlers.base as base_mod
    import src.bot.handlers.info as info_mod
    import src.bot.main as bot_main

    assert hasattr(bot_main, "main")
    # В base есть start/login/logout; в info — schedule/homeworks/app/catalog
    base_handlers = {h.callback.__name__ for h in base_mod.router.message.handlers}
    info_handlers = {h.callback.__name__ for h in info_mod.router.message.handlers}
    assert {"cmd_start", "cmd_login", "cmd_logout"} <= base_handlers
    assert {"cmd_schedule", "cmd_homeworks", "cmd_app", "cmd_catalog"} <= info_handlers


# ---------------------------------------------------------------------------
# 3. Клавиатуры и конфиг Mini App URL
# ---------------------------------------------------------------------------


def test_webapp_url_from_settings_not_hardcoded():
    url = settings.webapp_url
    assert url.endswith("/app")
    assert "google.com" not in url
    assert settings.api_base_url.rstrip("/") in url or (
        settings.webapp_public_url and settings.webapp_public_url.rstrip("/") in url
    )


def test_main_keyboard_has_miniapp_and_nav_buttons():
    kb = get_main_keyboard()
    texts = [b.text for row in kb.keyboard for b in row]
    app_btn = next(b for row in kb.keyboard for b in row if b.web_app)
    assert app_btn.web_app.url == settings.webapp_url
    assert "📅 Расписание" in texts
    assert "📝 Мои ДЗ" in texts
    assert "📚 Каталог курсов" in texts


def test_guest_keyboard_no_miniapp_button():
    kb = get_guest_keyboard()
    texts = [b.text for row in kb.keyboard for b in row]
    assert "📚 Каталог курсов" in texts
    assert all(b.web_app is None for row in kb.keyboard for b in row)


def test_catalog_renders():
    text = render_catalog()
    assert "Каталог" in text and len(CATALOG) >= 2
    for item in CATALOG:
        assert item.title in text


# ---------------------------------------------------------------------------
# 4. Обработчики info-роутера на реальной (in-memory) БД
# ---------------------------------------------------------------------------


class FakeMessage:
    """Минимальная заглушка aiogram Message: answer пишет ответы в список."""

    def __init__(self, user_id: int, text: str | None = None):
        self.from_user = TgUser(id=user_id, is_bot=False, first_name="Test")
        self.text = text
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None):
        self.answers.append((text, reply_markup))
        return type("M", (), {"message_id": 1})()


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with maker() as session:
        student = User(
            role=RoleEnum.student,
            telegram_id=1001,
            login="petrov",
            balance=10,
        )
        other_student = User(
            role=RoleEnum.student,
            telegram_id=1002,
            login="sidorov",
        )
        admin = User(
            role=RoleEnum.admin,
            telegram_id=9000,
            login="teacher",
        )
        session.add_all([student, other_student, admin])
        await session.flush()

        lesson = Lesson(
            student_id=student.id,
            subject="Информатика · ЕГЭ",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            status=LessonStatusEnum.scheduled,
        )
        past_lesson = Lesson(
            student_id=student.id,
            subject="Разбор пробника",
            start_time=now - timedelta(days=3),
            end_time=now - timedelta(days=3, hours=1),
            status=LessonStatusEnum.completed,
        )
        foreign_lesson = Lesson(
            student_id=other_student.id,
            subject="Чужой урок",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            status=LessonStatusEnum.scheduled,
        )
        session.add_all([lesson, past_lesson, foreign_lesson])
        await session.flush()

        hw_pending = Homework(
            lesson_id=lesson.id,
            description="Решить вариант 12\nзадания 13-18",
            deadline=now + timedelta(days=2),
            status=HomeworkStatusEnum.pending,
        )
        hw_graded = Homework(
            lesson_id=past_lesson.id,
            description="Конспект по алгоритмам",
            deadline=now - timedelta(days=1),
            status=HomeworkStatusEnum.graded,
            score="5",
        )
        session.add_all([hw_pending, hw_graded])
        await session.commit()
        ids = {
            "student_id": student.id,
            "admin_id": admin.id,
            "lesson_id": lesson.id,
        }
    yield maker, ids
    await engine.dispose()


@pytest.mark.asyncio
async def test_cmd_schedule_shows_only_own_future_lessons(db):
    from src.bot.handlers.info import cmd_schedule

    maker, ids = db
    msg = FakeMessage(user_id=1001, text="/schedule")
    async with maker() as session:
        await cmd_schedule(msg, session)

    assert msg.answers, "Бот ничего не ответил"
    text, markup = msg.answers[-1]
    assert "Информатика · ЕГЭ" in text
    assert "Чужой урок" not in text          # чужие уроки не видны
    assert "Разбор пробника" not in text      # прошедшие не показываются
    assert markup is not None                 # авторизованному — главное меню


@pytest.mark.asyncio
async def test_cmd_schedule_requires_login_for_guest(db):
    from src.bot.handlers.info import cmd_schedule

    maker, _ = db
    msg = FakeMessage(user_id=77777, text="/schedule")
    async with maker() as session:
        await cmd_schedule(msg, session)
    text, markup = msg.answers[-1]
    assert "/login" in text
    # Гостю — гостевая клавиатура (без Mini App кнопки)
    assert all(b.web_app is None for row in markup.keyboard for b in row)


@pytest.mark.asyncio
async def test_cmd_homeworks_lists_statuses(db):
    from src.bot.handlers.info import cmd_homeworks

    maker, ids = db
    msg = FakeMessage(user_id=1001, text="/homeworks")
    async with maker() as session:
        await cmd_homeworks(msg, session)

    text, _ = msg.answers[-1]
    assert "не сдано" in text
    assert "оценка: 5" in text
    assert "Итого:" in text


@pytest.mark.asyncio
async def test_cmd_app_returns_miniapp_keyboard(db):
    from src.bot.handlers.info import cmd_app

    maker, ids = db
    msg = FakeMessage(user_id=1001, text="/app")
    async with maker() as session:
        await cmd_app(msg, session)

    text, markup = msg.answers[-1]
    assert "расписание" in text.lower()
    urls = [b.web_app.url for row in markup.keyboard for b in row if b.web_app]
    assert urls == [settings.webapp_url]


@pytest.mark.asyncio
async def test_cmd_app_guest_gets_login_hint(db):
    from src.bot.handlers.info import cmd_app

    maker, _ = db
    msg = FakeMessage(user_id=88888, text="/app")
    async with maker() as session:
        await cmd_app(msg, session)
    text, _ = msg.answers[-1]
    assert "/login" in text


@pytest.mark.asyncio
async def test_cmd_catalog_button_matches_handler(db):
    """Кнопка «📚 Каталог курсов» рендерит каталог и гостевую клавиатуру."""
    from src.bot.handlers.info import cmd_catalog

    maker, _ = db
    btn_text = "📚 Каталог курсов"
    msg = FakeMessage(user_id=77777, text=btn_text)
    async with maker() as session:
        await cmd_catalog(msg, session)
    text, markup = msg.answers[-1]
    assert "Каталог курсов и услуг" in text
    guest_texts = [b.text for row in markup.keyboard for b in row]
    assert btn_text in guest_texts


@pytest.mark.asyncio
async def test_reply_button_matchers_exact(db):
    """Лямбда-матчеры кнопок сравнивают точный текст кнопки."""
    from src.bot.handlers.info import router

    # Извлекаем лямбда-фильтры зарегистрированных обработчиков
    lambdas = []
    for h in router.message.handlers:
        for f in h.filters:
            callback = getattr(f, "callback", None)
            if callable(callback) and getattr(callback, "__name__", "") == "<lambda>":
                lambdas.append(callback)
    assert lambdas, "Не найдено ни одного текстового матчера кнопок"

    class M:
        def __init__(self, t):
            self.text = t

    matched = {
        t
        for t in ["📅 Расписание", "📝 Мои ДЗ", "📚 Каталог курсов", "Привет", None]
        for fn in lambdas
        if fn(M(t))
    }
    assert matched == {"📅 Расписание", "📝 Мои ДЗ", "📚 Каталог курсов"}
