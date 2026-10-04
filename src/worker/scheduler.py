"""Scheduler entrypoint."""

from taskiq import TaskiqScheduler

from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa: F403,F401


def get_scheduler() -> TaskiqScheduler:
    """Get configured scheduler."""
    broker = get_broker()
    return TaskiqScheduler(broker=broker)
