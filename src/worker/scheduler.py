"""Scheduler entrypoint."""

from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa: F401,F403,F405


def get_scheduler():  # TODO S0.12: scheduler-запуск через `taskiq scheduler` CLI; sources подключатся в S0.12
    """Get configured scheduler broker."""
    return get_broker()
