"""Logging configuration."""

import logging
import sys

from pythonjsonlogger import jsonlogger

from src.core.config import settings


def setup_logging() -> None:
    """Configure JSON logging to stdout."""
    log_level = logging.DEBUG if settings.APP_ENV == "local" else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        timestamp=True,
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Reduce noise from libraries
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
