"""Базовые команды бота (docs/05_bot_logic_and_fsm.md, docs/09 §2.4).

Вход в систему — ТОЛЬКО по одноразовому приглашению ``/start inv_<token>``:
преподаватель создаёт профиль ученика и отправляет ссылку
``t.me/<bot>?start=inv_<token>``. Парольный FSM (/login → логин+пароль)
удалён: ТЗ прямо запрещает пароли (docs/01, docs/09 §2.4).

Токен проверяется src/services/invites.py: в БД лежит SHA-256, TTL 7 дней,
использование однократное; повторный вход уже привязанного аккаунта — просто
главное меню.
"""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import get_main_keyboard
from src.repositories import UserRepository
from src.services.invites import TOKEN_PREFIX, invite_service

router = Router()

user_repo = UserRepository()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    command: CommandStart,
):
    """/start [payload]: payload вида inv_<token> гасит приглашение.

    CommandStart() без параметров совпадает и с «/start», и с deep-link
    «/start inv_...»; сам payload доступен в внедрённом объекте команды.
    """
    payload = (command.payload or "").strip() if command is not None else ""

    # ── Вход по приглашению ────────────────────────────────────────────
    if payload.startswith(TOKEN_PREFIX):
        raw_token = payload[len(TOKEN_PREFIX):]
        user, status = await invite_service.redeem(
            session, raw_token, message.from_user.id
        )
        if status in ("ok", "already_linked") and user is not None:
            await message.answer(
                f"✅ Приглашение принято. Добро пожаловать, {user.login}!\n"
                "Главное меню 👇",
                reply_markup=get_main_keyboard(),
            )
            return
        if status == "conflict":
            await message.answer(
                "❌ Этот Telegram-аккаунт уже привязан к другому профилю. "
                "Обратитесь к преподавателю."
            )
            return
        await message.answer(
            "❌ Приглашение недействительно: оно уже использовано, "
            "просрочено (срок — 7 дней) или отозвано. "
            "Попросите преподавателя отправить новое."
        )
        return

    # ── Обычный /start ─────────────────────────────────────────────────
    user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    if user:
        await message.answer(
            f"Привет, {user.login}! Добро пожаловать в главное меню.",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            "Добро пожаловать в MY_LMS!\n\n"
            "Аккаунт ещё не создан — попросите преподавателя прислать "
            "приглашение (ссылка вида t.me/bot?start=inv_XXXX) и откройте "
            "её в этом чате.\n\n"
            "Ознакомиться с услугами можно в Каталоге 👇",
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start — главное меню (или вход по приглашению inv_...)\n"
        "/schedule — расписание на неделю\n"
        "/homeworks — статус домашних заданий\n"
        "/app — открыть Mini App\n"
        "/catalog — каталог курсов и услуг\n\n"
        "Паролей в системе нет: вход выполняется преподавателем через "
        "одноразовое приглашение."
    )
