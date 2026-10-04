"""Time utilities: UTC handling, timezone conversions."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from src.core.config import settings


def utc_now() -> datetime:
    """Current UTC time with timezone info."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_user_timezone(dt: datetime, tz_name: str | None = None) -> datetime:
    """Convert UTC datetime to user's timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    tz = ZoneInfo(tz_name or settings.DEFAULT_TIMEZONE)
    return dt.astimezone(tz)


def local_date_str(dt: datetime, tz_name: str | None = None) -> str:
    """Get date string (YYYY-MM-DD) in user's timezone."""
    return to_user_timezone(dt, tz_name).date().isoformat()


def iso_week(dt: datetime, tz_name: str | None = None) -> tuple[int, int]:
    """Get (year, week_number) in user's timezone (ISO week)."""
    user_dt = to_user_timezone(dt, tz_name)
    return user_dt.isocalendar()[:2]


def start_of_day(dt: datetime, tz_name: str | None = None) -> datetime:
    """Start of day (00:00) in user's timezone, returned as UTC."""
    user_dt = to_user_timezone(dt, tz_name)
    start = user_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC)


def end_of_day(dt: datetime, tz_name: str | None = None) -> datetime:
    """End of day (23:59:59.999) in user's timezone, returned as UTC."""
    user_dt = to_user_timezone(dt, tz_name)
    end = user_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return end.astimezone(UTC)
