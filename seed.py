import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.core.config import settings
from src.db.base import Base
from src.db.models import RoleEnum, LessonStatusEnum, HomeworkStatusEnum
from src.repositories import UserRepository, LessonRepository, HomeworkRepository
from src.services.auth import AuthService

async def main():
    # Создаем асинхронный движок и фабрику сессий
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Принудительно создаем таблицы, чтобы скрипт сработал даже если миграции не применены
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Инициализируем репозитории и сервис авторизации
    user_repo = UserRepository()
    lesson_repo = LessonRepository()
    hw_repo = HomeworkRepository()
    auth = AuthService()

    async with async_session() as session:
        # 1. Создаем преподавателя (пароль: admin123)
        admin = await user_repo.create(
            session=session,
            role=RoleEnum.admin,
            login="TeacherAdmin",
            password_hash=auth.get_password_hash("admin123"),
            balance=0,
            lesson_price=0
        )
        print(f"Создан преподаватель: {admin.login} (пароль: admin123)")

        # 2. Создаем 5 анонимных учеников (пароль: student{i})
        for i in range(1, 6):
            password = f"student{i}"
            student = await user_repo.create(
                session=session,
                role=RoleEnum.student,
                login=f"Student {i}",
                password_hash=auth.get_password_hash(password),
                balance=10,
                lesson_price=1000
            )
            print(f"Создан ученик: {student.login} (пароль: {password})")

            # 3. Для каждого ученика создаем по 2 урока
            lesson1 = await lesson_repo.create(
                session=session,
                student_id=student.id,
                subject="Математика",
                start_time=datetime.now() + timedelta(days=i),
                end_time=datetime.now() + timedelta(days=i, hours=1),
                status=LessonStatusEnum.scheduled
            )

            lesson2 = await lesson_repo.create(
                session=session,
                student_id=student.id,
                subject="Информатика",
                start_time=datetime.now() + timedelta(days=i+1),
                end_time=datetime.now() + timedelta(days=i+1, hours=1),
                status=LessonStatusEnum.scheduled
            )

            # 4. Одно домашнее задание, привязанное к первому уроку
            hw = await hw_repo.create(
                session=session,
                lesson_id=lesson1.id,
                description=f"Решить 10 уравнений из учебника (для {student.login})",
                deadline=datetime.now() + timedelta(days=i+7),
                status=HomeworkStatusEnum.pending
            )
            print(f"  -> Добавлено 2 урока и 1 ДЗ.")

        # Фиксируем все изменения в базе
        await session.commit()

    print("\n✅ База данных успешно заполнена тестовыми данными!")
    print("─" * 40)
    print("Учётные данные для входа через /login:")
    print("  Админ:    TeacherAdmin / admin123")
    print("  Ученик 1: Student 1    / student1")
    print("  Ученик 2: Student 2    / student2")
    print("  Ученик 3: Student 3    / student3")
    print("  Ученик 4: Student 4    / student4")
    print("  Ученик 5: Student 5    / student5")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
