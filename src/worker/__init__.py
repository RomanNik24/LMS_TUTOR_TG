"""Worker entrypoint."""

from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa: F403,F401  # register tasks with the broker


def get_worker():  # TODO S0.12: worker-запуск через `taskiq worker` CLI (в taskiq 0.13 TaskiqWorker отсутствует)
    """Get configured worker broker."""
    return get_broker()
