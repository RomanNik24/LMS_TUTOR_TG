"""Scheduler entrypoint."""

from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa: F403,F401  # register tasks with the broker


def get_scheduler():  # TODO S0.12: scheduler-запуск через `taskiq scheduler` CLI; sources подключатся в S0.12
    """Get configured scheduler broker."""
    return get_broker()
