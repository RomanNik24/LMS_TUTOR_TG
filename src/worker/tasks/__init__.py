"""Worker tasks: notifications, scheduling, cleanup."""

from taskiq import TaskiqTask
from taskiq.schedule import cron_schedule

from src.worker.broker import get_broker
from src.core.config import settings


broker = get_broker()


@broker.task(schedule=[cron_schedule("* * * * *")])  # Every minute
async def dispatch_due_notifications():
    """Send pending notifications."""
    # TODO: Implement notification dispatch
    pass


@broker.task(schedule=[cron_schedule("* * * * *")])  # Every minute
async def generate_lesson_reminders():
    """Generate lesson reminders for 30 min before lessons."""
    pass


@broker.task(schedule=[cron_schedule("*/5 * * * *")])  # Every 5 minutes
async def generate_homework_reminders():
    """Generate homework deadline reminders for 24h before due."""
    pass


@broker.task(schedule=[cron_schedule("*/5 * * * *")])
async def expire_homework_assignments():
    """Mark overdue assignments as expired."""
    pass


@broker.task(schedule=[cron_schedule("*/15 * * * *")])
async def notify_unmarked_lessons():
    """Notify staff about lessons without attendance marking."""
    pass


@broker.task(schedule=[cron_schedule("0 3 * * *")])  # Daily at 03:00
async def generate_scheduled_lessons():
    """Generate lessons from templates for horizon."""
    pass


@broker.task(schedule=[cron_schedule("0 * * * *")])  # Every hour
async def send_morning_digest():
    """Send morning digest at 08:00 in each user's timezone."""
    pass


@broker.task(schedule=[cron_schedule("0 4 * * *")])  # Daily at 04:00
async def cleanup_tokens():
    """Clean up expired tokens and temp files."""
    pass


@broker.task(schedule=[cron_schedule("*/5 * * * *")])
async def heartbeat():
    """Worker heartbeat for monitoring."""
    pass