from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states import LoginStates
from src.bot.keyboards import get_main_keyboard
from src.services.auth import AuthService
from src.repositories import UserRepository

router = Router()
auth_service = AuthService()

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
            "Пожалуйста, авторизуйтесь с помощью команды /login или посмотрите список курсов (Каталог)."
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
    await state.update_data(login=message.text.strip())
    await message.answer("Теперь введите ваш пароль:")
    await state.set_state(LoginStates.wait_for_password)

@router.message(LoginStates.wait_for_password)
async def process_password(message: Message, state: FSMContext, session: AsyncSession):
    password = message.text.strip()
    data = await state.get_data()
    login = data.get("login")
    
    user = await auth_service.authenticate_user(session, login, password)
    if not user:
        await message.answer("❌ Неверный логин или пароль. Попробуйте снова через команду /login.")
        await state.clear()
        return
        
    try:
        await auth_service.link_telegram_id(session, user.id, message.from_user.id)
        await session.commit()
        await message.answer(
            f"✅ Успешная авторизация!\nДобро пожаловать, {user.login}.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    except ValueError as e:
        await message.answer(f"❌ {e}")
        await state.clear()

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
