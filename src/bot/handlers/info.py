"""Информационные команды и кнопки пользователя (docs/05_bot_logic_and_fsm.md).

/schedule  — ближайшие уроки из БД (урок хранит student_id, фильтруем напрямую)
/homeworks — статус домашних заданий (HomeworkService.get_student_homeworks, без N+1)
/app       — запуск Mini App; URL формируется из settings.webapp_url (не захардкожен)
/catalog   — каталог услуг (для гостей — до авторизации, docs/05 п.3)
Reply-кнопки «📅 Расписание», «📝 Мои ДЗ», «📚 Каталог курсов» дублируют команды.
"""

from datetime import datetime, timedelta, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.catalog import render_catalog
from src.bot.keyboards import get_guest_keyboard, get_main_keyboard
from src.core.timeutil import fmt_local
from src.db.models import HomeworkStatusEnum, RoleEnum
from src.repositories import LessonRepository, UserRepository
from src.services.homework import HomeworkService

router = Router()

lesson_repo = LessonRepository()
user_repo = UserRepository()
hw_service = HomeworkService()


def _utcnow_naive() -> datetime:
    """Модели хранят naive UTC (см. utcnow в src/db/models.py)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fmt_dt(dt: datetime, tz_name: str | None = None) -> str:
    """Время в локальной зоне пользователя (с меткой зоны), а не голое UTC."""
    return fmt_local(dt, tz_name)


async def _get_user(message: Message, session: AsyncSession):
    return await user_repo.get_by_telegram_id(session, message.from_user.id)


@router.message(Command("schedule"))
@router.message(lambda m: bool(m.text) and m.text == "📅 Расписание")
async def cmd_schedule(message: Message, session: AsyncSession):
    user = await _get_user(message, session)
    if not user:
        await message.answer(
            "Вы не авторизованы. Авторизуйтесь командой /login.",
            reply_markup=get_guest_keyboard(),
        )
        return

    now = _utcnow_naive()
    # фильтрация по ученику — на уровне SQL (индекс ix_lessons_student_id),
    # а не выборкой уроков всех учеников с фильтром в Python
    my_lessons = await lesson_repo.get_for_student_in_period(
        session, user.id, now, now + timedelta(days=7)
    )

    if not my_lessons:
        await message.answer("📅 На ближайшую неделю уроков нет.")
        return

    lines = ["<b>📅 Ближайшие уроки (7 дней):</b>", ""]
    for lesson in my_lessons[:10]:
        lines.append(f"• {_fmt_dt(lesson.start_time, user.timezone)} — {lesson.subject}")
    await message.answer("\n".join(lines), reply_markup=get_main_keyboard())


@router.message(Command("homeworks"))
@router.message(lambda m: bool(m.text) and m.text == "📝 Мои ДЗ")
async def cmd_homeworks(message: Message, session: AsyncSession):
    user = await _get_user(message, session)
    if not user:
        await message.answer(
            "Вы не авторизованы. Авторизуйтесь командой /login.",
            reply_markup=get_guest_keyboard(),
        )
        return

    homeworks = await hw_service.get_student_homeworks(session, user.id)
    if not homeworks:
        await message.answer("📝 У вас пока нет домашних заданий.")
        return

    marks = {
        HomeworkStatusEnum.pending: "⏳ не сдано",
        HomeworkStatusEnum.submitted: "📤 сдано, ждёт проверки",
        HomeworkStatusEnum.graded: "✅ проверено",
    }
    counters = {"pending": 0, "submitted": 0, "graded": 0}
    lines = ["<b>📝 Домашние задания:</b>", ""]
    for hw in sorted(homeworks, key=lambda h: h.deadline, reverse=True)[:10]:
        counters[hw.status.value] += 1
        suffix = f", оценка: {hw.score}" if hw.status == HomeworkStatusEnum.graded else ""
        topic = hw.description.splitlines()[0][:60] if hw.description else "—"
        lines.append(
            f"• до {_fmt_dt(hw.deadline, user.timezone)}: {marks[hw.status]}{suffix}\n  <i>{topic}</i>"
        )

    lines.append(
        f"\nИтого: ⏳ {counters['pending']} · 📤 {counters['submitted']} · "
        f"✅ {counters['graded']}"
    )
    await message.answer("\n".join(lines), reply_markup=get_main_keyboard())


@router.message(Command("app"))
async def cmd_app(message: Message, session: AsyncSession):
    """Запуск Mini App (docs/05, п.1: ссылка зависит от роли пользователя)."""
    user = await _get_user(message, session)
    if not user:
        await message.answer(
            "Вы не авторизованы. Авторизуйтесь командой /login.",
            reply_markup=get_guest_keyboard(),
        )
        return
    role_note = (
        "приложение преподавателя"
        if user.role == RoleEnum.admin
        else "личное расписание, ДЗ и отчёты"
    )
    await message.answer(
        f"Откройте приложение кнопкой ниже 👇 ({role_note})",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("catalog"))
@router.message(lambda m: bool(m.text) and m.text == "📚 Каталог курсов")
async def cmd_catalog(message: Message, session: AsyncSession):
    user = await _get_user(message, session)
    markup = get_main_keyboard() if user else get_guest_keyboard()
    await message.answer(render_catalog(), reply_markup=markup)
