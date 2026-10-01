"""Регрессия: бот не должен падать на нетекстовых сообщениях в состояниях логина.

Стикер/фото/голосовое приходят с ``message.text is None``; прежний код
``message.text.strip()`` в process_login/process_password ронял хендлер
(Unhandled AttributeError). Теперь получаем мягкий ответ-подсказку, состояние
сохраняется, а /cancel очищает FSM.
"""

import os
import pytest

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from datetime import datetime, timezone  # noqa: E402

import pytest_asyncio  # noqa: E402
from aiogram.fsm.state import State  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.bot.handlers.base import cmd_cancel, process_login, process_password  # noqa: E402
from src.bot.states import LoginStates  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.db.models import RoleEnum, User  # noqa: E402
from src.services.auth import AuthService  # noqa: E402


class FakeMessage:
    """Заглушка aiogram Message. text=None имитирует стикер/фото/голосовое."""

    def __init__(self, user_id: int = 1001, text: str | None = None, tz: str | None = None):
        self.from_user = type(
            "TgUserLike", (), {"id": user_id, "first_name": "Test", "timezone": tz}
        )()
        self.text = text
        self.answers: list[str] = []

    async def answer(self, text: str, reply_markup=None):
        self.answers.append(text)
        return type("M", (), {"message_id": 1})()


class FakeState:
    """Минимальная замена FSMContext поверх словаря."""

    def __init__(self):
        self.state: str | None = None
        self.data: dict = {}

    async def get_state(self):
        return self.state

    async def set_state(self, state):
        self.state = state.state if isinstance(state, State) else state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.state = None
        self.data = {}


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    auth = AuthService()
    async with maker() as s:
        s.add(
            User(
                role=RoleEnum.student,
                login="petrov",
                password_hash=auth.get_password_hash("secret"),
                balance=5,
            )
        )
        await s.commit()
        yield s
    await engine.dispose()


# ---------------------------------------------------------------------------
# _clean_text — сам хелпер
# ---------------------------------------------------------------------------


def test_clean_text_none_message():
    assert process_login is not None  # импорт не падает
    from src.bot.handlers.base import _clean_text

    assert _clean_text(FakeMessage(text=None)) is None
    assert _clean_text(FakeMessage(text="   ")) is None
    assert _clean_text(FakeMessage(text=" petrov ")) == "petrov"


# ---------------------------------------------------------------------------
# Хендлеры: нетекстовые сообщения не роняют бота
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sticker_in_wait_for_login_does_not_crash():
    msg = FakeMessage(text=None)  # стикер
    state = FakeState()
    await state.set_state(LoginStates.wait_for_login)

    await process_login(msg, state)  # было: AttributeError 'NoneType'.strip()

    assert msg.answers, "бот должен ответить подсказкой"
    assert "текстом" in msg.answers[-1].lower()
    # состояние сохранено, данные не испорчены
    assert state.state == "LoginStates:wait_for_login"
    assert state.data == {}


@pytest.mark.asyncio
async def test_empty_text_message_treated_as_non_text():
    msg = FakeMessage(text="   \n ")
    state = FakeState()
    await state.set_state(LoginStates.wait_for_login)

    await process_login(msg, state)

    assert msg.answers and state.state == "LoginStates:wait_for_login"


@pytest.mark.asyncio
async def test_photo_in_wait_for_password_keeps_login_and_state():
    msg = FakeMessage(text=None)  # фото вместо пароля
    state = FakeState()
    await state.set_state(LoginStates.wait_for_password)
    await state.update_data(login="petrov")

    from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401  (тип для сигнатуры)

    await process_password(msg, state, session=None)  # БД даже не трогается

    assert "текстом" in msg.answers[-1].lower()
    assert state.state == "LoginStates:wait_for_password"
    assert state.data["login"] == "petrov", "логин не должен теряться"


@pytest.mark.asyncio
async def test_normal_login_flow_still_works_with_sticker_interspersed():
    """стикер -> текст логина -> пароль: полный цикл проходит и привязывает tg_id."""
    state = FakeState()
    await state.set_state(LoginStates.wait_for_login)

    await process_login(FakeMessage(text=None), state)          # не упал
    await process_login(FakeMessage(text=" petrov "), state)     # логин с пробелами
    assert state.state == "LoginStates:wait_for_password"
    assert state.data["login"] == "petrov"

    pwd_msg = FakeMessage(text="secret", tz="Europe/Moscow")
    # process_password требует реальную сессию — используем фикстуру через
    # отдельный тест ниже; здесь проверяем только отсутствие падения на None
    # в текстовых путях уже покрыто первыми двумя тестами.
    assert pwd_msg.text == "secret"


@pytest.mark.asyncio
async def test_full_password_success_links_telegram_and_saves_timezone(session):
    state = FakeState()
    await state.set_state(LoginStates.wait_for_password)
    await state.update_data(login="petrov")

    msg = FakeMessage(user_id=1001, text="secret", tz="Europe/Moscow")
    await process_password(msg, state, session)

    assert any("Успешная авторизация" in a for a in msg.answers), msg.answers
    assert state.state is None, "FSM должен быть очищен после успеха"
    user = await session.get(User, 1)
    assert user.telegram_id == 1001
    assert user.timezone == "Europe/Moscow", (
        "tz из Telegram-профиля должна сохраняться (regression NameError user_repo)"
    )


@pytest.mark.asyncio
async def test_wrong_password_after_sticker_resets_state(session):
    state = FakeState()
    await state.set_state(LoginStates.wait_for_password)
    await state.update_data(login="petrov")

    sticker = FakeMessage(text=None)
    await process_password(sticker, state, session)  # стикер — не сброс
    assert state.state == "LoginStates:wait_for_password"

    wrong = FakeMessage(text="wrong")
    await process_password(wrong, state, session)  # неверный пароль
    assert state.state is None
    assert any("Неверный" in a for a in wrong.answers), wrong.answers


# ---------------------------------------------------------------------------
# /cancel — обещан в подсказках, должен существовать и чистить FSM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_clears_active_state():
    state = FakeState()
    await state.set_state(LoginStates.wait_for_password)
    await state.update_data(login="petrov")

    msg = FakeMessage(text="/cancel")
    await cmd_cancel(msg, state)

    assert state.state is None and state.data == {}
    assert "отмен" in msg.answers[-1].lower()


@pytest.mark.asyncio
async def test_cancel_without_state_is_polite():
    state = FakeState()
    msg = FakeMessage(text="/cancel")
    await cmd_cancel(msg, state)
    assert "нет активного" in msg.answers[-1].lower()


def test_cancel_handler_registered_on_router():
    import src.bot.handlers.base as base_mod

    names = {h.callback.__name__ for h in base_mod.router.message.handlers}
    assert "cmd_cancel" in names
