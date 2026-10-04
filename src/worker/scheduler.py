"""Scheduler entrypoint."""

from taskiq import TaskiqScheduler
from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa


def get_scheduler() -> TaskiqScheduler:
    """Get configured scheduler."""
    broker = get_broker()
    return TaskiqScheduler(broker=broker)