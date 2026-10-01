"""Cron-задачи воркера MY_LMS (docs/01, п.5; docs/05, п.4).

Каждая задача: читает БД через единый src/db/session.py, формирует тексты
и доставляет их через aiogram Bot. Функции разделены на чистые «сборщики»
(build_*) — тестируются без сети — и thin-обёртки для Arq (notify_*).

Защита от дублей напоминаний о ДЗ: Redis-ключ hw_remind:{id}:{deadline_ts}
с TTL ~25 часов (дедлайны могут переноситься — ключ привязан к timestamp).
"""

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.timeutil import fmt_local, humanize_until
from src.db.models import Homework, Lesson, RoleEnum, User, utcnow
from src.db.session import async_session_maker
from src.repositories import HomeworkRepository, LessonRepository, UserRepository
from src.services.lesson import LessonService

logger = logging.getLogger(__name__)

# Окна выборок согласованы с cron-расписанием (src/worker/settings.py):
# урок стартует в окне [now+window, now+2*window) при запуске каждые
# `window` минут (:30), дедлайн ДЗ попадает в окно (now, now+24h] при
# суточном запуске в 8:00.
# ВАЖНО: текст напоминания строится по ФАКТИЧЕСКИМ минутам до начала урока
# (humanize_until), а не по константе окна — иначе «через 30 минут»
# приходило бы для уроков, которые начинаются через 59 минут.
LESSON_WINDOW_MINUTES = 30
HW_DEADLINE_WINDOW_HOURS = 24
HW_REMIND_KEY_TTL_SECONDS = 25 * 3600


def _aware(dt: datetime) -> datetime:
    """naive-UTC из БД -> aware UTC для корректных вычитаний и astimezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt


def format_lesson_time(start: datetime, tz_name: Optional[str] = None) -> str:
    """Время урока/дедлайна в локальной зоне пользователя (с меткой зоны).

    Обратная совместимость: параметр tz_name опционален; без него — системная
    зона процесса (в Docker обычно UTC, что честно подписывается «UTC»).
    """
    return fmt_local(start, tz_name)


def build_lesson_reminders(
    lessons: list[Lesson], now: Optional[datetime] = None
) -> list[tuple[int, str]]:
    """Список (telegram_id, текст) для напоминаний об уроках. Пропускает
    учеников без привязанного Telegram. Время — в зоне получателя, фраза
    «через …» — точная (по фактическому start_time)."""
    now = _aware(now or utcnow())
    out: list[tuple[int, str]] = []
    for lesson in lessons:
        student = lesson.student
        if not student or not student.telegram_id:
            continue
        tz_name = getattr(student, "timezone", None)
        minutes_left = int(
            (_aware(lesson.start_time) - now).total_seconds() // 60
        )
        text = (
            f"⏰ Напоминание: урок «{lesson.subject}» начнётся "
            f"{humanize_until(minutes_left)} "
            f"({format_lesson_time(lesson.start_time, tz_name)})."
        )
        if lesson.video_url:
            text += f"\n🎥 Ссылка: {lesson.video_url}"
        out.append((student.telegram_id, text))
    return out


def build_homework_reminders(
    homeworks: list[Homework], now: Optional[datetime] = None
) -> list[tuple[int, str]]:
    """Список (telegram_id, текст) по несданным ДЗ с дедлайном в пределах 24ч.

    Точный остаток времени до дедлайна + срок в локальной зоне ученика.
    """
    out: list[tuple[int, str]] = []
    for hw in homeworks:
        lesson = hw.lesson
        student = lesson.student if lesson else None
        if not student or not student.telegram_id:
            continue
        out.append((student.telegram_id, _hw_text(hw, now=now)))
    return out


async def collect_lesson_reminders(
    session: AsyncSession,
    now: Optional[datetime] = None,
    window_minutes: int = LESSON_WINDOW_MINUTES,
) -> list[tuple[int, str]]:
    """Достать из БД уроки, требующие напоминания, и собрать тексты.

    Окно: [now+window, now+2*window) — при запуске cron каждые `window`
    минут каждый урок попадает ровно в одно окно (без дублей).
    Параметр `now` пробрасывается в сборщик текстов, чтобы фраза
    «через N мин» считалась от того же момента, что и окно выборки
    (важно для тестов с фиксированным временем).
    """
    now = now or utcnow()
    repo = LessonRepository()
    lessons = await repo.get_upcoming_starting_between(
        session,
        from_dt=now + timedelta(minutes=window_minutes),
        to_dt=now + timedelta(minutes=window_minutes * 2),
    )
    # student подгружаем отдельным запросом (lazy-load в async запрещён)
    user_repo = UserRepository()
    for lesson in lessons:
        lesson.student = await user_repo.get_by_id(session, lesson.student_id)
    return build_lesson_reminders(lessons, now=now)


async def collect_homework_reminders(
    session: AsyncSession,
    redis=None,
    now: Optional[datetime] = None,
) -> list[tuple[int, str]]:
    """Несданные ДЗ с дедлайном в пределах 24ч; уже отправленные пропускаем
    по Redis-ключу (если redis передан)."""
    now = now or utcnow()
    until = now + timedelta(hours=HW_DEADLINE_WINDOW_HOURS)
    hw_repo = HomeworkRepository()
    lesson_repo = LessonRepository()
    user_repo = UserRepository()

    homeworks = await hw_repo.get_due_before(
        session, deadline_until=until, after=None
    )
    # get_due_before возвращает pending (не submitted/graded) — требование docs/01
    enriched: list[Homework] = []
    for hw in homeworks:
        if hw.deadline <= now:  # просроченные не напоминаем — только будущие
            continue
        hw.lesson = await lesson_repo.get_by_id(session, hw.lesson_id)
        if hw.lesson is not None:
            hw.lesson.student = await user_repo.get_by_id(session, hw.lesson.student_id)
        enriched.append(hw)

    reminders = build_homework_reminders(enriched, now=now)

    if redis is not None:
        fresh: list[tuple[int, str]] = []
        for hw in enriched:
            key = f"hw_remind:{hw.id}:{int(hw.deadline.timestamp())}"
            # set(nx=True) — атомарная метка «уже напомнили»
            was_set = await redis.set(key, "1", ex=HW_REMIND_KEY_TTL_SECONDS, nx=True)
            if was_set:
                student = hw.lesson.student if hw.lesson else None
                if student and student.telegram_id:
                    pair = (student.telegram_id, _hw_text(hw, now=now))
                    fresh.append(pair)
        reminders = fresh
    return reminders


def _hw_text(hw: Homework, now: Optional[datetime] = None) -> str:
    """Текст напоминания о дедлайне ДЗ: точный остаток времени и срок в
    локальной зоне ученика (вместо неточного «через 24 часа» и UTC)."""
    student = hw.lesson.student if hw.lesson else None
    tz_name = getattr(student, "timezone", None) if student else None
    minutes_left = int(
        (_aware(hw.deadline) - _aware(now or utcnow())).total_seconds() // 60
    )
    return (
        f"📌 Дедлайн ДЗ {humanize_until(minutes_left)}: "
        f"«{hw.description[:80]}» "
        f"(срок до {format_lesson_time(hw.deadline, tz_name)}). "
        f"Статус: не сдано."
    )


async def build_close_requests(lessons: list[Lesson]) -> list[tuple[int, str]]:
    """Сообщения ученикам о переводе урока в «ждёт подтверждения».

    Деньги ещё НЕ списаны: преподаватель подтвердит проведение (или отменит
    урок, если занятие не состоялось) — только тогда спишется занятие.
    Время урока — в локальной зоне ученика.
    """
    out: list[tuple[int, str]] = []
    for lesson in lessons:
        student = lesson.student
        if not student or not student.telegram_id:
            continue
        tz_name = getattr(student, "timezone", None)
        text = (
            f"⏳ Урок «{lesson.subject}» "
            f"({format_lesson_time(lesson.start_time, tz_name)}) завершён и переведён "
            f"в статус «ждёт подтверждения». Преподаватель подтвердит проведение, "
            f"после чего будет списано занятие."
        )
        out.append((student.telegram_id, text))
    return out


# ------------------------- Arq job wrappers -------------------------


async def notify_lesson_starts(ctx: dict) -> int:
    """Arq cron: push-напоминания об уроках за 30 минут."""
    sent = 0
    async with async_session_maker() as session:
        reminders = await collect_lesson_reminders(session)
    if reminders:
        bot = Bot(token=settings.bot_token.get_secret_value())
        try:
            for chat_id, text in reminders:
                try:
                    await bot.send_message(chat_id, text)
                    sent += 1
                except Exception as exc:  # пользователь заблокировал бота и т.п.
                    logger.warning("Не удалось отправить урок-напомину %s: %s", chat_id, exc)
        finally:
            await bot.session.close()
    logger.info("notify_lesson_starts: sent=%d", sent)
    return sent


async def notify_homework_deadlines(ctx: dict) -> int:
    """Arq cron: напоминания о дедлайне ДЗ за 24 часа (однократно)."""
    redis = ctx.get("redis")
    sent = 0
    async with async_session_maker() as session:
        reminders = await collect_homework_reminders(session, redis=redis)
    if reminders:
        bot = Bot(token=settings.bot_token.get_secret_value())
        try:
            for chat_id, text in reminders:
                try:
                    await bot.send_message(chat_id, text)
                    sent += 1
                except Exception as exc:
                    logger.warning("Не удалось отправить ДЗ-напомину %s: %s", chat_id, exc)
        finally:
            await bot.session.close()
    logger.info("notify_homework_deadlines: sent=%d", sent)
    return sent


async def close_lesson_cycle(ctx: dict) -> int:
    """Arq cron: автозакрытие завершившихся уроков БЕЗ списания баланса.

    Урок переводится scheduled -> needs_confirmation; ученику приходит
    уведомление «ждёт подтверждения», админу — сводка уроков, требующих
    решения (подтвердить POST /lessons/{id}/complete со списанием занятия
    или отменить /cancel без списания). Списание происходит только после
    явного подтверждения преподавателем — если урок не состоялся, деньги
    не спишутся. Уведомления дедуплицируются Redis-ключом lesson_close:{id}
    (TTL 3 дня) — иначе каждые 15 минут приходило бы повторное сообщение.
    """
    redis = ctx.get("redis")
    service = LessonService()
    user_repo = UserRepository()
    messages: list[tuple[int, str]] = []
    async with async_session_maker() as session:
        closed = await service.process_finished_lessons(session)
        fresh: list[Lesson] = []
        for lesson in closed:
            if redis is not None:
                key = f"lesson_close:{lesson.id}"
                already = await redis.set(key, "1", ex=3 * 24 * 3600, nx=True)
                if not already:
                    continue  # уведомление уже отправлялось
            student = await user_repo.get_by_id(session, lesson.student_id)
            if not student:
                continue
            lesson.student = student
            fresh.append(lesson)
        messages.extend(build_close_requests(fresh))
        # одна сводка каждому админу: какие уроки ждут подтверждения.
        # Время урока — в ЧАСОВОЙ ЗОНЕ АДМИНА (у всех админов может быть
        # разная зона), а не дефолтная/UTC.
        if fresh:
            admins = await user_repo.get_by_role(session, RoleEnum.admin)
            for admin in admins:
                if not admin.telegram_id:
                    continue
                lines = "\n".join(
                    f"— #{l.id} {l.subject} "
                    f"({format_lesson_time(l.start_time, admin.timezone)}) "
                    f"ученик {l.student.login if getattr(l, 'student', None) else l.student_id}"
                    for l in fresh
                )
                summary = (
                    "🔔 Ждут подтверждения проведения (баланс ещё не списан):\n"
                    + lines
                    + "\nПодтвердите POST /lessons/{id}/complete (списание) "
                    "или отмените /cancel (без списания)."
                )
                messages.append((admin.telegram_id, summary))
        await session.commit()

    if messages:
        bot = Bot(token=settings.bot_token.get_secret_value())
        try:
            for chat_id, text in messages:
                try:
                    await bot.send_message(chat_id, text)
                except Exception as exc:
                    logger.warning("Не удалось отправить подтверждение %s: %s", chat_id, exc)
        finally:
            await bot.session.close()
    logger.info("close_lesson_cycle: marked_needs_confirmation=%d", len(closed))
    return len(closed)
