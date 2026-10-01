"""Cron-задачи воркера MY_LMS (docs/01, п.5; docs/05, п.4).

Каждая задача: читает БД через единый src/db/session.py, формирует тексты
и доставляет их через aiogram Bot. Функции разделены на чистые «сборщики»
(build_*) — тестируются без сети — и thin-обёртки для Arq (notify_*).

Защита от дублей напоминаний о ДЗ: Redis-ключ hw_remind:{id}:{deadline_ts}
с TTL ~25 часов (дедлайны могут переноситься — ключ привязан к timestamp).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import Homework, Lesson, RoleEnum, User, utcnow
from src.db.session import async_session_maker
from src.repositories import HomeworkRepository, LessonRepository, UserRepository
from src.services.lesson import LessonService

logger = logging.getLogger(__name__)

# Окна выборок согласованы с cron-расписанием (src/worker/settings.py):
# урок стартует в окне [now+30m, now+60m) при запуске каждые 60 мин (:30),
# дедлайн ДЗ попадает в окно (now, now+24h] при суточном запуске в 8:00.
LESSON_WINDOW_MINUTES = 30
HW_DEADLINE_WINDOW_HOURS = 24
HW_REMIND_KEY_TTL_SECONDS = 25 * 3600


def format_lesson_time(start: datetime) -> str:
    return start.strftime("%d.%m %H:%M")


def build_lesson_reminders(lessons: list[Lesson]) -> list[tuple[int, str]]:
    """Список (telegram_id, текст) для напоминаний об уроках. Пропускает
    учеников без привязанного Telegram."""
    out: list[tuple[int, str]] = []
    for lesson in lessons:
        student = lesson.student
        if not student or not student.telegram_id:
            continue
        text = (
            f"⏰ Напоминание: урок «{lesson.subject}» начнётся через "
            f"{LESSON_WINDOW_MINUTES} минут ({format_lesson_time(lesson.start_time)})."
        )
        if lesson.video_url:
            text += f"\n🎥 Ссылка: {lesson.video_url}"
        out.append((student.telegram_id, text))
    return out


def build_homework_reminders(homeworks: list[Homework]) -> list[tuple[int, str]]:
    """Список (telegram_id, текст) по несданным ДЗ с дедлайном в пределах 24ч."""
    out: list[tuple[int, str]] = []
    for hw in homeworks:
        lesson = hw.lesson
        student = lesson.student if lesson else None
        if not student or not student.telegram_id:
            continue
        text = (
            f"📌 Дедлайн ДЗ через 24 часа: «{hw.description[:80]}» "
            f"(срок до {format_lesson_time(hw.deadline)}). Статус: не сдано."
        )
        out.append((student.telegram_id, text))
    return out


async def collect_lesson_reminders(
    session: AsyncSession,
    now: Optional[datetime] = None,
    window_minutes: int = LESSON_WINDOW_MINUTES,
) -> list[tuple[int, str]]:
    """Достать из БД уроки, требующие напоминания, и собрать тексты.

    Окно: [now+window, now+2*window) — при запуске cron каждые `window`
    минут каждый урок попадает ровно в одно окно (без дублей).
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
    return build_lesson_reminders(lessons)


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

    reminders = build_homework_reminders(enriched)

    if redis is not None:
        fresh: list[tuple[int, str]] = []
        for hw in enriched:
            key = f"hw_remind:{hw.id}:{int(hw.deadline.timestamp())}"
            # set(nx=True) — атомарная метка «уже напомнили»
            was_set = await redis.set(key, "1", ex=HW_REMIND_KEY_TTL_SECONDS, nx=True)
            if was_set:
                student = hw.lesson.student if hw.lesson else None
                if student and student.telegram_id:
                    pair = (student.telegram_id, _hw_text(hw))
                    fresh.append(pair)
        reminders = fresh
    return reminders


def _hw_text(hw: Homework) -> str:
    return (
        f"📌 Дедлайн ДЗ через 24 часа: «{hw.description[:80]}» "
        f"(срок до {format_lesson_time(hw.deadline)}). Статус: не сдано."
    )


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
    """Arq cron: автозакрытие завершившихся уроков (completed + списание баланса).

    Ученикам и админу приходит подтверждение со статусом баланса
    (docs/01, п.4.2: баланс занятия списывается после проведения).
    Подтверждения дедуплицируются по Redis-ключу lesson_close:{id}
    (TTL 3 дня) — иначе каждые 15 минут приходило бы повторное сообщение.
    """
    redis = ctx.get("redis")
    service = LessonService()
    user_repo = UserRepository()
    async with async_session_maker() as session:
        closed = await service.process_finished_lessons(session)
        # Собрать данные для пушей по завершённым за последние 90 минут урокам
        now = utcnow()
        repo = LessonRepository()
        finished = await repo.get_finished_completed_since(session, now - timedelta(minutes=90))
        messages: list[tuple[int, str]] = []
        for lesson in finished:
            if redis is not None:
                key = f"lesson_close:{lesson.id}"
                already = await redis.set(key, "1", ex=3 * 24 * 3600, nx=True)
                if not already:
                    continue  # подтверждение уже отправлялось
            student = await user_repo.get_by_id(session, lesson.student_id)
            if not student:
                continue
            text = (
                f"✅ Урок «{lesson.subject}» проведён и закрыт."
                f"\n💸 Списано занятие. Остаток: {student.balance}"
            )
            if student.telegram_id:
                messages.append((student.telegram_id, text))
            admins = await user_repo.get_by_role(session, RoleEnum.admin)
            for admin in admins:
                if admin.telegram_id:
                    messages.append(
                        (admin.telegram_id,
                         f"✅ Автозакрытие: урок «{lesson.subject}» "
                         f"({format_lesson_time(lesson.start_time)}) у {student.login} проведён.")
                    )
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
    logger.info("close_lesson_cycle: closed=%d", closed)
    return closed
