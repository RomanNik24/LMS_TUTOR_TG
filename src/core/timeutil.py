"""Единая работа с часовыми поясами (время в БД хранится в UTC, naive).

Проблема, которую решает модуль (docs/01 п.5, docs/05 п.4):
- все datetime в БД — naive UTC (см. utcnow() в src/db/models.py);
- сообщения пользователю раньше печатались в UTC без пересчёта и без
  учёта его локального времени;
- текст напоминания об уроке обещал «через 30 минут», хотя фактическое
  время до начала могло быть любым в пределах окна [30, 60) минут.

Решение: у каждого пользователя есть поле timezone (IANA name, например
Europe/Moscow), которое бот подставляет автоматически из Telegram-профиля.
Все показываемые человеку времена форматируются через fmt_local() в его
зону; тексты напоминаний содержат точную фразу «через N мин».
"""

from datetime import datetime, timezone as dt_timezone
from typing import Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Формат отображения: дата + время + явная метка зоны, чтобы не было
# неоднозначности между UTC и локальным временем.
DEFAULT_FMT = "%d.%m %H:%M"


def get_user_tz(tz_name: Optional[str]) -> dt_timezone:
    """ZoneInfo по IANA-имени пользователя; при ошибке/пустоте — системная зона.

    Системная зона берётся из tzname() локального времени процесса
    (в Docker это обычно UTC, если не задан TZ), поэтому поведение
    детерминированно и безопасно.
    """
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    # fallback: системная зона процесса
    from time import tzname
    import time

    name = time.tzname[time.localtime().tm_isdst and 1 or 0]
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return dt_timezone.utc


def to_local(dt: datetime, tz: Union[str, dt_timezone, None]) -> datetime:
    """Перевести naive-UTC (или aware) datetime в локальную зону."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    if isinstance(tz, str) or tz is None:
        tz = get_user_tz(tz if isinstance(tz, str) else None)
    return dt.astimezone(tz)


def tz_abbr(dt_local: datetime) -> str:
    """Короткая подписи зоны для текста сообщения (MSK / UTC / EKT ...)."""
    tz = dt_local.tzinfo
    if tz is None:
        return ""
    try:
        abbr = tz.key.split("/")[-1].replace("_", " ")
        # Человекочитаемые частые случаи
        nice = {
            "Moscow": "МСК",
            "Kaliningrad": "КЛГ",
            "Ekaterinburg": "ЕКБ",
            "Novosibirsk": "НСК",
            "Vladivostok": "ВЛА",
            "Kyiv": "КИЕ",
            "London": "LON",
            "Berlin": "BER",
        }
        return nice.get(abbr, abbr[:3].upper())
    except AttributeError:
        off = dt_local.utcoffset()
        if off is None:
            return "UTC"
        total_min = int(off.total_seconds() // 60)
        sign = "+" if total_min >= 0 else "-"
        h, m = divmod(abs(total_min), 60)
        return f"UTC{sign}{h}" + (f":{m:02d}" if m else "")


def fmt_local(
    dt: datetime,
    tz_name: Optional[str] = None,
    fmt: str = DEFAULT_FMT,
    with_zone: bool = True,
) -> str:
    """Отформатировать UTC-datetime в локальное время пользователя с меткой зоны.

    Пример: fmt_local(datetime(2026,10,1,15,30), 'Europe/Moscow')
             -> '01.10 18:30 МСК'
    """
    local = to_local(dt, get_user_tz(tz_name))
    text = local.strftime(fmt)
    if with_zone:
        abbr = tz_abbr(local)
        if abbr:
            text = f"{text} {abbr}"
    return text


def humanize_until(delta_minutes: int) -> str:
    """Понятная фраза «через …» для количества минут (для текстов пушей)."""
    delta_minutes = max(int(delta_minutes), 0)
    if delta_minutes < 60:
        return f"через {delta_minutes} мин"
    hours, minutes = divmod(delta_minutes, 60)
    if not minutes:
        unit = _plural(hours, ("час", "часа", "часов"))
        return f"через {hours} {unit}"
    h_unit = _plural(hours, ("час", "часа", "часов"))
    m_unit = _plural(minutes, ("минуту", "минуты", "минут"))
    return f"через {hours} {h_unit} {minutes} {m_unit}"


def _plural(n: int, forms: tuple[str, str, str]) -> str:
    """Русская плюрализация: 1 час / 2 часа / 5 часов."""
    n10, n100 = n % 10, n % 100
    if n100 in range(11, 15):
        return forms[2]
    if n10 == 1:
        return forms[0]
    if n10 in range(2, 5):
        return forms[1]
    return forms[2]
