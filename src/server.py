"""Единая точка входа MY_LMS API (docs/03_architecture.md, раздел 4).

Запуск:
    python -m src.server
или:
    uvicorn src.server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import sys

import uvicorn

from src.main import app  # noqa: F401  (экспортируется для uvicorn)


def run() -> None:
    """Синхронный запуск Uvicorn (исправляет event-loop для asyncpg на Windows)."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()
