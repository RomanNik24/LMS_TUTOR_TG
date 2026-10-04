"""Bot handlers."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import (
    get_catalog_keyboard,
    get_confirm_keyboard,
    get_guest_keyboard,
    get_staff_keyboard,
    get_student_keyboard,
)
from src.bot.states import LogoutState
from src.core.texts import (
    BOT_COMMANDS_GUEST,
    BOT_COMMANDS_STAFF,
    BOT_COMMANDS_STUDENT,
    CATALOG_EMPTY,
    GUEST_WELCOME,
    student_welcome,
)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start and /start inv_<token>"""
    # TODO: Extract invite token and handle invitation
    user = message.conf.get("current_user")
    if not user:
        await message.answer(GUEST_WELCOME, reply_markup=get_guest_keyboard())
    elif user.role == "student":
        await message.answer(student_welcome(user.display_name), reply_markup=get_student_keyboard())
    else:
        await message.answer("Привет! Меню персонала ниже.", reply_markup=get_staff_keyboard())


@router.message(F.text == "Каталог услуг")
async def show_catalog(message: Message):
    """Show catalog to guest."""
    # TODO: Fetch catalog items from DB
    await message.answer(CATALOG_EMPTY, reply_markup=get_catalog_keyboard(0, 0))


@router.callback_query(F.data.startswith("catalog_"))
async def catalog_page(callback: CallbackQuery):
    """Handle catalog pagination."""
    page = int(callback.data.split("_")[1])  # noqa: F841  # TODO: использовать на этапе каталога
    # TODO: Fetch and show catalog page
    await callback.answer()


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open Mini App."""
    user = message.conf.get("current_user")
    if not user:
        return
    # Keyboard with WebApp button is already in reply markup


@router.message(Command("web"))
async def cmd_web(message: Message):
    """Generate one-time web login link."""
    # TODO: Generate link via AuthService
    await message.answer("Ссылка для входа в браузере будет здесь (10 минут, одноразовая).")


@router.message(Command("today"))
async def cmd_today(message: Message):
    """Show today's schedule."""
    user = message.conf.get("current_user")
    if not user:
        return
    # TODO: Fetch and show today's lessons
    await message.answer("Расписание на сегодня будет здесь.")


@router.message(Command("hw"))
async def cmd_hw(message: Message):
    """Show homework (student) or review queue (staff)."""
    user = message.conf.get("current_user")
    if not user:
        return
    await message.answer("Список ДЗ / Очередь на проверку будет здесь.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help."""
    user = message.conf.get("current_user")
    if not user:
        cmds = BOT_COMMANDS_GUEST
    elif user.role == "student":
        cmds = BOT_COMMANDS_STUDENT
    else:
        cmds = BOT_COMMANDS_STAFF
    text = "Доступные команды:\n" + "\n".join(f"/{k} — {v}" for k, v in cmds.items())
    await message.answer(text)


@router.message(Command("logout"))
async def cmd_logout(message: Message, state: FSMContext):
    """Start logout confirmation."""
    await message.answer(
        "Вы уверены? Чтобы войти снова, понадобится новая ссылка от преподавателя.",
        reply_markup=get_confirm_keyboard("logout_confirm", "logout_cancel"),
    )
    await state.set_state(LogoutState.waiting_confirm)


@router.callback_query(F.data == "logout_confirm", LogoutState.waiting_confirm)
async def logout_confirm(callback: CallbackQuery, state: FSMContext):
    """Confirm logout."""
    # TODO: Unlink telegram_id via AuthService
    await callback.message.edit_text("Аккаунт отвязан. Для входа нужна новая ссылка.")
    await state.clear()


@router.callback_query(F.data == "logout_cancel", LogoutState.waiting_confirm)
async def logout_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel logout."""
    await callback.message.edit_text("Отвязка отменена.")
    await state.clear()
