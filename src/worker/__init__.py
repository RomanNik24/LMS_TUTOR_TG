"""Worker entrypoint."""

from taskiq import TaskiqWorker
from src.worker.broker import get_broker
from src.worker.tasks import *  # noqa


def get_worker() -> TaskiqWorker:
    """Get configured worker."""
    broker = get_broker()
    return TaskiqWorker(broker=broker)