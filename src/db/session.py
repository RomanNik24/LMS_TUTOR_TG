from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncSessionLocal = async_session_maker


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def dispose_engine() -> None:
    await engine.dispose()


@asynccontextmanager
async def lifespan(app):
    yield
    await dispose_engine()