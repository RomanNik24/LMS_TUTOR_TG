"""Общая фикстура: SQLite in-memory + переопределение get_db_session."""

import os

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.api.dependencies import get_db_session  # noqa: E402
from src.db.base import Base  # noqa: E402
from src.main import create_app  # noqa: E402


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
