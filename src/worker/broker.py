"""TaskIQ broker configuration."""

from taskiq import TaskiqScheduler
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from src.core.config import settings


def get_broker() -> RedisStreamBroker:
    """Create Redis stream broker."""
    return RedisStreamBroker(
        url=settings.REDIS_URL,
    ).with_result_backend(
        RedisAsyncResultBackend(redis_url=settings.REDIS_URL)
    )


def get_scheduler(broker: RedisStreamBroker) -> TaskiqScheduler:
    """Create TaskIQ scheduler."""
    return TaskiqScheduler(broker=broker)
