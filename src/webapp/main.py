import json
from datetime import datetime

import flet as ft
import httpx
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.db.models import RoleEnum
from src.repositories import UserRepository
from src.services.auth import AuthService


# ============================================================
# Подключение к БД
# ============================================================

engine = create_async_engine(
    settings.database_url,
    echo=False,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

API_BASE_URL = "http://127.0.0.1:8000"


# ============================================================
# Экран ученика
# ============================================================


def build_student_view(
    page: ft.Page,
    student_id: int,
    api_token: str,
) -> ft.View:
    """Строит экран ученика."""

    lessons_column = ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    hw_column = ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    balance_text = ft.Text(
        "Баланс: —",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE,
    )

    loading_indicator = ft.ProgressRing(
        visible=True,
        width=30,
        height=30,
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    async def load_data(e=None):
        loading_indicator.visible = True
        page.update()

        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers=headers,
        ) as client:
            # ------------------------------------------------
            # Расписание
            # ------------------------------------------------

            try:
                resp = await client.get(f"/students/{student_id}/schedule")

                lessons = resp.json() if resp.status_code == 200 else []

            except Exception:
                lessons = []

            # ------------------------------------------------
            # Домашние задания
            # ------------------------------------------------

            try:
                resp = await client.get(f"/students/{student_id}/homeworks")

                homeworks = resp.json() if resp.status_code == 200 else []

            except Exception:
                homeworks = []

            # ------------------------------------------------
            # Баланс
            # ------------------------------------------------

            try:
                resp = await client.get(f"/students/{student_id}/balance")

                bal = (
                    resp.json().get("balance", "—") if resp.status_code == 200 else "—"
                )

            except Exception:
                bal = "—"

        balance_text.value = f"Баланс: {bal} ₽"

        # ----------------------------------------------------
        # Уроки
        # ----------------------------------------------------

        lessons_column.controls.clear()

        if not lessons:
            lessons_column.controls.append(
                ft.Text(
                    "Нет запланированных уроков",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            )

        for lesson in lessons:
            status = lesson.get(
                "status",
                "",
            )

            status_color = {
                "scheduled": ft.Colors.BLUE,
                "completed": ft.Colors.GREEN,
                "cancelled": ft.Colors.RED,
            }.get(
                status,
                ft.Colors.GREY,
            )

            start = lesson.get(
                "start_time",
                "",
            )[:16].replace("T", "  ")

            end = lesson.get(
                "end_time",
                "",
            )[:16].replace("T", "  ")

            lessons_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.BOOK,
                                            color=ft.Colors.BLUE_700,
                                        ),
                                        ft.Text(
                                            lesson.get(
                                                "subject",
                                                "—",
                                            ),
                                            size=18,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Container(
                                            expand=True,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                status.upper(),
                                                size=11,
                                                color=ft.Colors.WHITE,
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            bgcolor=status_color,
                                            border_radius=12,
                                            padding=ft.Padding.symmetric(
                                                horizontal=10,
                                                vertical=4,
                                            ),
                                        ),
                                    ],
                                ),
                                ft.Divider(
                                    height=1,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.ACCESS_TIME,
                                            size=14,
                                            color=ft.Colors.GREY_600,
                                        ),
                                        ft.Text(
                                            f"{start}  →  {end}",
                                            size=13,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        padding=14,
                    ),
                    elevation=3,
                )
            )

        # ----------------------------------------------------
        # Домашние задания
        # ----------------------------------------------------

        hw_column.controls.clear()

        if not homeworks:
            hw_column.controls.append(
                ft.Text(
                    "Нет домашних заданий",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            )

        for hw in homeworks:
            hw_status = hw.get(
                "status",
                "",
            )

            hw_icon = {
                "pending": ft.Icons.HOURGLASS_EMPTY,
                "submitted": ft.Icons.UPLOAD_FILE,
                "graded": ft.Icons.CHECK_CIRCLE,
            }.get(
                hw_status,
                ft.Icons.HELP_OUTLINE,
            )

            hw_color = {
                "pending": ft.Colors.ORANGE,
                "submitted": ft.Colors.BLUE,
                "graded": ft.Colors.GREEN,
            }.get(
                hw_status,
                ft.Colors.GREY,
            )

            deadline = hw.get(
                "deadline",
                "",
            )[:16].replace("T", "  ")

            if hw.get("score"):
                score_text = f"Оценка: {hw['score']}"
            else:
                score_text = "Ещё не оценено"

            hw_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            hw_icon,
                                            color=hw_color,
                                        ),
                                        ft.Text(
                                            hw.get(
                                                "description",
                                                "—",
                                            )[:60],
                                            size=15,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                    ],
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.CALENDAR_TODAY,
                                            size=13,
                                            color=ft.Colors.GREY_600,
                                        ),
                                        ft.Text(
                                            f"Дедлайн: {deadline}",
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                        ft.Container(
                                            expand=True,
                                        ),
                                        ft.Text(
                                            score_text,
                                            size=12,
                                            italic=True,
                                            color=hw_color,
                                        ),
                                    ],
                                ),
                            ]
                        ),
                        padding=12,
                    ),
                    elevation=2,
                )
            )

        loading_indicator.visible = False
        page.update()

    page.run_task(load_data)

    return ft.View(
        "/student",
        [
            ft.AppBar(
                title=ft.Text("Кабинет Ученика"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                actions=[
                    ft.Container(
                        content=balance_text,
                        padding=ft.Padding.only(right=16),
                    ),
                ],
            ),
            ft.Container(
                content=ft.Column(
                    [
                        loading_indicator,
                        ft.Text(
                            "📚 Мои уроки",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        lessons_column,
                        ft.Divider(height=20),
                        ft.Text(
                            "📝 Мои домашние задания",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        hw_column,
                    ],
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=16,
                expand=True,
            ),
            ft.FloatingActionButton(
                icon=ft.Icons.REFRESH,
                on_click=load_data,
                tooltip="Обновить",
            ),
        ],
    )


# ============================================================
# Экран администратора
# ============================================================


def build_admin_view(
    page: ft.Page,
    api_token: str,
) -> ft.View:
    """Строит экран администратора."""

    students_list = ft.Column(
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
    )

    student_dropdown = ft.Dropdown(
        label="Ученик",
        width=300,
    )

    login_field = ft.TextField(
        label="Логин",
        width=280,
    )

    password_field = ft.TextField(
        label="Пароль",
        password=True,
        can_reveal_password=True,
        width=280,
    )

    balance_field = ft.TextField(
        label="Баланс",
        value="0",
        width=130,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    price_field = ft.TextField(
        label="Цена урока",
        value="1000",
        width=130,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    subject_field = ft.TextField(
        label="Предмет",
        width=280,
    )

    date_field = ft.TextField(
        label="Дата (ГГГГ-ММ-ДД)",
        width=200,
    )

    start_time_field = ft.TextField(
        label="Начало (ЧЧ:ММ)",
        value="10:00",
        width=130,
    )

    end_time_field = ft.TextField(
        label="Конец (ЧЧ:ММ)",
        value="11:00",
        width=130,
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    def show_snack(msg: str):
        page.show_dialog(ft.SnackBar(content=ft.Text(msg)))

    # ========================================================
    # Загрузка учеников
    # ========================================================

    async def load_students(e=None):

        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers=headers,
        ) as client:
            try:
                resp = await client.get("/students/")

                students = resp.json() if resp.status_code == 200 else []

            except Exception:
                students = []

        students_list.controls.clear()
        student_dropdown.options.clear()

        if not students:
            students_list.controls.append(
                ft.Text(
                    "Нет учеников",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            )

        for student in students:
            students_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.PERSON,
                                    color=ft.Colors.BLUE_700,
                                ),
                                ft.Text(
                                    student["login"],
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Container(expand=True),
                                ft.Text(
                                    f"Баланс: {student['balance']} ₽",
                                    size=13,
                                    color=ft.Colors.GREY_700,
                                ),
                            ]
                        ),
                        padding=12,
                    ),
                    elevation=2,
                )
            )

            student_dropdown.options.append(
                ft.DropdownOption(
                    key=str(student["id"]),
                    text=student["login"],
                )
            )

        page.update()

    # ========================================================
    # Создание ученика
    # ========================================================

    async def on_add_student(e):

        login = (login_field.value or "").strip()

        pwd = (password_field.value or "").strip()

        if not login or not pwd:
            show_snack("⚠️ Заполните логин и пароль")

            return

        try:
            balance = int(balance_field.value or 0)

            lesson_price = int(price_field.value or 1000)

        except ValueError:
            show_snack("⚠️ Баланс и цена урока должны быть числами")

            return

        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers=headers,
        ) as client:
            resp = await client.post(
                "/students/",
                json={
                    "login": login,
                    "password": pwd,
                    "balance": balance,
                    "lesson_price": lesson_price,
                },
            )

        if resp.status_code == 201:
            show_snack(f"✅ Ученик «{login}» создан!")

            login_field.value = ""
            password_field.value = ""

            await load_students()

        elif resp.status_code == 409:
            show_snack("❌ Логин уже занят")

        elif resp.status_code == 401:
            show_snack("❌ Токен авторизации недействителен")

        elif resp.status_code == 403:
            show_snack("❌ Недостаточно прав")

        else:
            show_snack(f"❌ Ошибка: {resp.text}")

    # ========================================================
    # Создание урока
    # ========================================================

    async def on_add_lesson(e):

        sid = student_dropdown.value

        subj = (subject_field.value or "").strip()

        date_value = (date_field.value or "").strip()

        start_time = (start_time_field.value or "").strip()

        end_time = (end_time_field.value or "").strip()

        if not all(
            [
                sid,
                subj,
                date_value,
                start_time,
                end_time,
            ]
        ):
            show_snack("⚠️ Заполните все поля урока")

            return

        try:
            start_dt = datetime.strptime(
                f"{date_value} {start_time}",
                "%Y-%m-%d %H:%M",
            ).isoformat()

            end_dt = datetime.strptime(
                f"{date_value} {end_time}",
                "%Y-%m-%d %H:%M",
            ).isoformat()

        except ValueError:
            show_snack("⚠️ Неверный формат даты/времени")

            return

        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers=headers,
        ) as client:
            resp = await client.post(
                f"/students/{sid}/lessons",
                json={
                    "subject": subj,
                    "start_time": start_dt,
                    "end_time": end_dt,
                },
            )

        if resp.status_code == 201:
            show_snack(f"✅ Урок «{subj}» добавлен!")

            subject_field.value = ""
            date_field.value = ""

            page.update()

        elif resp.status_code == 401:
            show_snack("❌ Токен авторизации недействителен")

        elif resp.status_code == 403:
            show_snack("❌ Недостаточно прав администратора")

        else:
            show_snack(f"❌ Ошибка: {resp.text}")

    page.run_task(load_students)

    return ft.View(
        "/admin",
        [
            ft.AppBar(
                title=ft.Text("Панель Администратора"),
                bgcolor=ft.Colors.RED_700,
                color=ft.Colors.WHITE,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        # ------------------------------------------------
                        # Список учеников
                        # ------------------------------------------------
                        ft.Text(
                            "👥 Ученики",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        students_list,
                        ft.Divider(height=24),
                        # ------------------------------------------------
                        # Добавление ученика
                        # ------------------------------------------------
                        ft.Text(
                            "➕ Добавить ученика",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Row(
                            [
                                login_field,
                                password_field,
                            ],
                            wrap=True,
                        ),
                        ft.Row(
                            [
                                balance_field,
                                price_field,
                            ],
                            wrap=True,
                        ),
                        ft.Button(
                            content="Создать ученика",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=on_add_student,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.Divider(height=24),
                        # ------------------------------------------------
                        # Назначение урока
                        # ------------------------------------------------
                        ft.Text(
                            "📅 Назначить урок",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        student_dropdown,
                        ft.Row(
                            [
                                subject_field,
                            ],
                            wrap=True,
                        ),
                        ft.Row(
                            [
                                date_field,
                                start_time_field,
                                end_time_field,
                            ],
                            wrap=True,
                        ),
                        ft.Button(
                            content="Создать урок",
                            icon=ft.Icons.ADD_CIRCLE,
                            on_click=on_add_lesson,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                padding=16,
                expand=True,
            ),
            ft.FloatingActionButton(
                icon=ft.Icons.REFRESH,
                on_click=load_students,
                tooltip="Обновить",
            ),
        ],
    )


# ============================================================
# Главная точка входа Flet
# ============================================================


async def main(page: ft.Page):

    page.title = "MY_LMS WebApp"
    page.theme_mode = ft.ThemeMode.LIGHT

    user_id = None
    db_user = None
    api_token = None

    # --------------------------------------------------------
    # Получаем Telegram WebApp пользователя
    # --------------------------------------------------------

    try:
        tg_data_str = await page.evaluate_js_async(
            "JSON.stringify(window.Telegram?.WebApp?.initDataUnsafe || {})"
        )

        if tg_data_str and tg_data_str != "{}":
            tg_data = json.loads(tg_data_str)

            if "user" in tg_data:
                user_id = tg_data["user"].get("id")

    except Exception:
        pass

    # --------------------------------------------------------
    # Получаем пользователя из БД
    # --------------------------------------------------------

    if user_id:
        async with async_session_maker() as session:
            user_repo = UserRepository()

            db_user = await user_repo.get_by_telegram_id(
                session,
                user_id,
            )

            if db_user:
                auth_service = AuthService()

                api_token = auth_service.create_access_token(db_user)

    # --------------------------------------------------------
    # Создание экранов
    # --------------------------------------------------------

    def route_change(route=None):

        page.views.clear()

        # ----------------------------------------------------
        # Кабинет ученика
        # ----------------------------------------------------

        if (
            page.route == "/student"
            and db_user
            and api_token
            and db_user.role == RoleEnum.student
        ):
            page.views.append(
                build_student_view(
                    page,
                    db_user.id,
                    api_token,
                )
            )

        # ----------------------------------------------------
        # Панель администратора
        # ----------------------------------------------------

        elif (
            page.route == "/admin"
            and db_user
            and api_token
            and db_user.role == RoleEnum.admin
        ):
            page.views.append(
                build_admin_view(
                    page,
                    api_token,
                )
            )

        # ----------------------------------------------------
        # Главная страница
        # ----------------------------------------------------

        else:
            page.views.append(
                ft.View(
                    "/",
                    [
                        ft.AppBar(
                            title=ft.Text("MY_LMS"),
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Icon(
                                        ft.Icons.WARNING_AMBER_ROUNDED,
                                        size=50,
                                        color=ft.Colors.ORANGE,
                                    ),
                                    ft.Text(
                                        "Пожалуйста, откройте приложение\n"
                                        "через Telegram бота.",
                                        size=20,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=(ft.CrossAxisAlignment.CENTER),
                            ),
                            alignment=ft.Alignment.CENTER,
                            expand=True,
                        ),
                    ],
                )
            )

        page.update()

    # --------------------------------------------------------
    # Обработка "Назад"
    # --------------------------------------------------------

    def view_pop(view):

        if page.views:
            page.views.pop()

        if page.views:
            top_view = page.views[-1]

            page.navigate(top_view.route)

        else:
            page.navigate("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # --------------------------------------------------------
    # ВАЖНО:
    # Flet не обязательно вызовет route_change
    # сразу после регистрации обработчика.
    # Поэтому сначала отрисовываем текущий маршрут.
    # --------------------------------------------------------

    route_change()

    # --------------------------------------------------------
    # Начальный маршрут
    # --------------------------------------------------------

    if db_user and api_token:
        if db_user.role == RoleEnum.student:
            await page.push_route("/student")

        elif db_user.role == RoleEnum.admin:
            await page.push_route("/admin")

        else:
            await page.push_route("/")

    else:
        await page.push_route("/")


# ============================================================
# Запуск Flet Web
# ============================================================

if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
        port=8550,
    )
