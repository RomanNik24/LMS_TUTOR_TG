"""Worker tasks: notifications, scheduling, cleanup."""

from src.worker.broker import get_broker

broker = get_broker()

# taskiq 0.13: cron-расписания объявляются словарём cron (k8s-style), а не cron_schedule()
EVERY_MINUTE = [{"cron": "* * * * *"}]
EVERY_5_MIN = [{"cron": "*/5 * * * *"}]
EVERY_15_MIN = [{"cron": "*/15 * * * *"}]
EVERY_HOUR = [{"cron": "0 * * * *"}]
DAILY_03 = [{"cron": "0 3 * * *"}]
DAILY_04 = [{"cron": "0 4 * * *"}]


@broker.task(schedule=EVERY_MINUTE)  # Every minute
async def dispatch_due_notifications():
    """Send pending notifications."""
    # TODO: Implement notification dispatch


@broker.task(schedule=EVERY_MINUTE)  # Every minute
async def generate_lesson_reminders():
    """Generate lesson reminders for 30 min before lessons."""


@broker.task(schedule=EVERY_5_MIN)  # Every 5 minutes
async def generate_homework_reminders():
    """Generate homework deadline reminders for 24h before due."""


@broker.task(schedule=EVERY_5_MIN)
async def expire_homework_assignments():
    """Mark overdue assignments as expired."""


@broker.task(schedule=EVERY_15_MIN)
async def notify_unmarked_lessons():
    """Notify staff about lessons without attendance marking."""


@broker.task(schedule=DAILY_03)  # Daily at 03:00
async def generate_scheduled_lessons():
    """Generate lessons from templates for horizon."""


@broker.task(schedule=EVERY_HOUR)  # Every hour
async def send_morning_digest():
    """Send morning digest at 08:00 in each user's timezone."""


@broker.task(schedule=DAILY_04)  # Daily at 04:00
async def cleanup_tokens():
    """Clean up expired tokens and temp files."""


@broker.task(schedule=EVERY_5_MIN)
async def heartbeat():
    """Worker heartbeat for monitoring."""
