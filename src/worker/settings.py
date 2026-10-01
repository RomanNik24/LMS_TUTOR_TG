"""Конфигурация и точка входа воркера фоновых задач (Arq, docs/02_tech_stack.md).

Воркер — единственный источник времени в системе push-уведомлений:
бот не ставит таймеры сам (docs/05_bot_logic_and_fsm.md, п.4), он лишь
получает готовые тексты от cron-задач воркера и доставляет их по telegram_id.

Задачи (docs/01_project_overview.md, п.5):
- Напоминание об уроке за 30 минут до начала;
- Напоминание о дедлайне ДЗ за 24 часа (только если статус != сдано);
- Автозакрытие завершившихся уроков со списанием баланса.
"""

from arq import cron
from arq.connections import RedisSettings

from src.core.config import settings
from src.worker.tasks import close_lesson_cycle, notify_homework_deadlines, notify_lesson_starts


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [notify_lesson_starts, notify_homework_deadlines, close_lesson_cycle]
    # Интервалы выбраны так, чтобы окно выборки == интервалу запуска:
    # каждый урок/дедлайн попадает ровно в одно окно -> без дублей.
    cron_jobs = [
        # Урок начинается через 30..60 минут -> напомнить сейчас
        cron(notify_lesson_starts, minute={30}),
        # Дедлайн ДЗ в пределах следующих 24 часов -> напомнить раз в сутки
        cron(notify_homework_deadlines, hour={8}, minute={0}),
        # Завершившиеся scheduled-уроки -> completed + списание баланса
        cron(close_lesson_cycle, minute={0, 15, 30, 45}),
    ]
    max_jobs = 10
    job_timeout = 60
