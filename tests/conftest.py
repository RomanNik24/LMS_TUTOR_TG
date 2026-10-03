"""Общая фикстура: SQLite in-memory + переопределение get_db_session.

Дополнительно (этап безопасности, docs/09): Redis подменяется in-memory
fakeredis, чтобы серверные сессии, rate limiting и аудит работали без
реального Redis; есть хелпер подписания корректной initData.
"""

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import fakeredis.aioredis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.api.dependencies import get_db_session  # noqa: E402
from src.core import redis as redis_module  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.main import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Подменить пул Redis на fakeredis для всех тестов."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_module, "_client", client)
    # session_service / middleware берут клиент через get_redis() модуля —
    # патчим именно атрибут модуля, все импорты `from ... import get_redis`
    # продолжают резолвиться в эту же функцию, читающую _client.
    yield client
    return client


def sign_init_data(bot_token: str, user_id: int, *, auth_date: int | None = None) -> str:
    """Собрать строку initData с валидной HMAC-подписью (как Telegram).

    По спецификации в data_check_string входят ВСЕ поля кроме hash —
    включая auth_date.
    """
    if auth_date is None:
        auth_date = int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "Test"}, separators=(",", ":"))
    pairs = {
        "user": user_json,
        "auth_date": str(auth_date),
        "query_id": "AAH" + str(user_id),
    }
    check_fields = {k: v for k, v in pairs.items() if k != "hash"}
    check_string = "\n".join(f"{k}={check_fields[k]}" for k in sorted(check_fields))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_ = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = hash_
    return urlencode(pairs)


@pytest_asyncio.fixture
async def make_client():
    """(AsyncClient, session_maker) поверх изолированной in-memory БД."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_maker

    await engine.dispose()
