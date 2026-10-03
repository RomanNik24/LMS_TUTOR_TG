"""Общий Redis-клиент (сессии Mini App, rate limiting).

Единый пул соединений на процесс: API и Flet-приложение работают в разных
процессах, но используют один и тот же Redis (docs/02_tech_stack.md).
Клиент создаётся лениво; тесты переопределяют get_redis().
"""

from typing import Optional

from redis.asyncio import Redis

from src.core.config import settings

_client: Optional[Redis] = None


def get_redis() -> Redis:
    """Ленивый синглтон асинхронного клиента Redis."""
    global _client
    if _client is None:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """Закрытие пула (lifespan/shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
