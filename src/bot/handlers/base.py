from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states import LoginStates
from src.bot.keyboards import get_guest_keyboard, get_main_keyboard
from src.services.auth import AuthService
from src.repositories import UserRepository

router = Router()
auth_service = AuthService()


def _clean_text(message: Message) -> str | None:
    """Безопасно достаёт текст сообщения.

    Нетекстовые сообщения (стикер, фото, голосовое, документ) приходят с
    ``message.text is None`` — прямое ``message.text.strip()`` роняло хендлер
    в состояниях логина. Возвращаем очищенный текст или None.
    """
    if not message.text:
        return None
    text = message.text.strip()
    return text or None

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    user_repo = UserRepository()
    user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    
    if user:
        await message.answer(
            f"Привет, {user.login}! Добро пожаловать в главное меню.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "Добро пожаловать в MY_LMS!\n\n"
            "Пожалуйста, авторизуйтесь с помощью команды /login или посмотрите список курсов (Каталог).",
            reply_markup=get_guest_keyboard(),
        )

@router.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext, session: AsyncSession):
    user_repo = UserRepository()
    user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    if user:
        await message.answer("Вы уже авторизованы в системе!")
        return

    await message.answer("Введите ваш логин:")
    await state.set_state(LoginStates.wait_for_login)

@router.message(LoginStates.wait_for_login)
async def process_login(message: Message, state: FSMContext):
    login = _clean_text(message)
    if not login:
        # Нетекстовое сообщение (стикер/фото/голосовое) — не роняем хендлер,
        # просим ввести логин текстом; состояние сохраняем.
        await message.answer(
            "Пожалуйста, введите логин текстом (без стикеров и файлов).\n"
            "Отмена — /cancel."
        )
        return
    await state.update_data(login=login)
    await message.answer("Теперь введите ваш пароль:")
    await state.set_state(LoginStates.wait_for_password)

@router.message(LoginStates.wait_for_password)
async def process_password(message: Message, state: FSMContext, session: AsyncSession):
    password = _clean_text(message)
    if not password:
        # Пароль нельзя «прикрепить файлом» — просим текст, состояние не сбрасываем
        # (логин уже сохранён в FSM-данных).
        await message.answer(
            "Пароль нужно ввести текстом (без стикеров и файлов).\n"
            "Отмена — /cancel."
        )
        return
    data = await state.get_data()
    login = data.get("login")
    
    user = await auth_service.authenticate_user(session, login, password)
    if not user:
        await message.answer("❌ Неверный логин или пароль. Попробуйте снова через команду /login.")
        await state.clear()
        return
        
    try:
        await auth_service.link_telegram_id(session, user.id, message.from_user.id)
        # Запоминаем часовую зону пользователя из Telegram-профиля — по ней
        # воркер и бот будут показывать времена уроков/дедлайнов в локальном
        # времени (src/core/timeutil.py). zone_id может отсутствовать у
        # старых аккаунтов — тогда оставляем как есть.
        tg_zone = getattr(message.from_user, "timezone", None) or None
        if tg_zone and tg_zone != user.timezone:
            # локальный репозиторий вместо глобального: в этом модуле нет
            # переменной уровня файла user_repo, прежний код падал с NameError
            # при каждой успешной авторизации пользователя с tz в профиле
            await UserRepository().update(session, user.id, timezone=tg_zone)
        await session.commit()
        await message.answer(
            f"✅ Успешная авторизация!\nДобро пожаловать, {user.login}.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    except ValueError as e:
        await message.answer(f"❌ {e}")
        await state.clear()

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущего сценария (например, пошагового логина)."""
    if await state.get_state() is None:
        await message.answer("Сейчас нет активного действия для отмены.")
        return
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard(),
    )

@router.message(Command("logout"))
async def cmd_logout(message: Message, session: AsyncSession):
    user_repo = UserRepository()
    user = await user_repo.get_by_telegram_id(session, message.from_user.id)
    if user:
        await user_repo.update(session, user.id, telegram_id=None)
        await session.commit()
        await message.answer(
            "Вы успешно вышли из системы. Вы переведены в статус гостя.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("Вы не авторизованы.")
