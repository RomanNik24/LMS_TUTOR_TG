"""Единая точка создания движка БД и сессий (паттерн из docs/03_architecture.md).

Единственный модуль, который создаёт AsyncEngine / sessionmaker.
Все слои (API, бот, воркер) берут сессии только отсюда —
это устраняет дублирование движков в api/dependencies, bot/middlewares, webapp.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

# Один движок на процесс
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Фабрика асинхронных сессий
async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI / общий источник сессий.

    Коммит при успехе, откат при исключении — вызывающий код
    может явно вызывать commit()/flush(), двойной commit безопасен.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Корректное закрытие пула соединений (для lifespan и тестов)."""
    await engine.dispose()
