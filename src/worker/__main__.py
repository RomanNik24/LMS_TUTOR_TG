"""Точка входа воркера фоновых задач: `python -m src.worker`.

Запускает Arq-воркер с настройками из ``src.worker.settings.WorkerSettings``.
Используется командой в docker-compose (service ``worker``) и для локального
запуска. Запуск через CLI-хелпер arq корректно поднимает cron-планировщик
и обработчик функций; сам процесс блокируется до сигнала остановки.

Важно: ``arq.cron(...)`` — это только описание задачи, воркер запускается
исключительно через ``run_worker`` (или CLI ``arq src.worker.settings``).
"""

from arq.cli import run_worker

from src.worker.settings import WorkerSettings


def main() -> None:
    """Синхронная точка входа: создаёт и запускает воркер (внутри — asyncio.run)."""
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
