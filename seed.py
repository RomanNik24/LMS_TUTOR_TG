"""Наполнение БД тестовыми данными (демонстрационный набор).

ВАЖНО (docs/01, docs/09 §2.4): паролей в системе нет — вход выполняется
только по одноразовому приглашению ``inv_<token>`` (src/services/invites.py).
Поэтому сид не задаёт ``password_hash`` и не печатает учётные данные.

Таблицы создаёт ТОЛЬКО Alembic (``alembic upgrade head``) — см. docs/06_agent_rules.md.
"""

import asyncio
from datetime import datetime, timedelta

from src.db.session import async_session_maker, dispose_engine

from src.db.models import RoleEnum, LessonStatusEnum, HomeworkStatusEnum
from src.repositories import UserRepository, LessonRepository, HomeworkRepository


async def main():
    # Используем единый движок/сессии из src/db/session.py
    async_session = async_session_maker

    # Инициализируем репозитории
    user_repo = UserRepository()
    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()

    async with async_session() as session:
        # 1. Создаём преподавателя (без пароля; telegram_id привязывается
        #    через приглашение или вручную администратором).
        admin = await user_repo.create(
            session=session,
            role=RoleEnum.admin,
            login="TeacherAdmin",
            balance=0,
            lesson_price=0,
        )
        print(f"Создан преподаватель: {admin.login}")

        # 2. Создаём 5 учеников (без паролей).
        for i in range(1, 6):
            student = await user_repo.create(
                session=session,
                role=RoleEnum.student,
                login=f"Student {i}",
                balance=10,
                lesson_price=1000,
            )
            print(
                f"Создан ученик: {student.login} — "
                f"отправьте ему приглашение inv_<token> из панели администратора"
            )

            # 3. Для каждого ученика создаём по 2 урока
            lesson1 = await lesson_repo.create(
                session=session,
                student_id=student.id,
                subject="Математика",
                start_time=datetime.now() + timedelta(days=i),
                end_time=datetime.now() + timedelta(days=i, hours=1),
                status=LessonStatusEnum.scheduled,
            )

            lesson2 = await lesson_repo.create(
                session=session,
                student_id=student.id,
                subject="Информатика",
                start_time=datetime.now() + timedelta(days=i + 1),
                end_time=datetime.now() + timedelta(days=i + 1, hours=1),
                status=LessonStatusEnum.scheduled,
            )

            # 4. Одно домашнее задание, привязанное к первому уроку
            await hw_repo.create(
                session=session,
                lesson_id=lesson1.id,
                description=f"Решить 10 уравнений из учебника (для {student.login})",
                deadline=datetime.now() + timedelta(days=i + 7),
                status=HomeworkStatusEnum.pending,
            )
            print("  -> Добавлено 2 урока и 1 ДЗ.")

        # Фиксируем все изменения в базе
        await session.commit()

    print("\n✅ База данных успешно заполнена тестовыми данными!")
    print("─" * 40)
    print(
        "Вход в систему: преподаватель создаёт приглашение и отправляет\n"
        "ученику ссылку t.me/<bot>?start=inv_<token>. Паролей в системе нет."
    )

    # Единый движок больше не создаётся в seed — диспозим общий пул
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
