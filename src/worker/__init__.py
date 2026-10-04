"""Worker entrypoint."""

from taskiq import TaskiqWorker

from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa: F403,F401


def get_worker() -> TaskiqWorker:
    """Get configured worker."""
    broker = get_broker()
    return TaskiqWorker(broker=broker)
