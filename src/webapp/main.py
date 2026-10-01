import json
import os
from datetime import datetime
from types import SimpleNamespace

import flet as ft
import httpx

from src.core.config import settings
from src.db.models import RoleEnum
from src.webapp import ftui_common as ui


# ============================================================
# Точка входа API
# ============================================================
# WebApp НЕ имеет прямого доступа к БД — только через REST API
# (docs/03_architecture.md). В docker-compose адрес передаётся
# переменной окружения API_BASE_URL.

API_BASE_URL = os.getenv("API_BASE_URL", settings.api_base_url)


# ============================================================
# Экран ученика
# ============================================================

"""Мини-приложение ученика (Student Mini App) — Этап 3.

Экраны по docs/01_project_overview.md, п.4.1:
- Расписание: карточки занятий с привязанными ДЗ, ссылками на ВКС и доску;
- Домашние задания: загрузка фото-решений (POST /me/uploads -> submit)
  и кнопка «Сделал» для устных заданий;
- Отчёты: сводка прогресса + динамика оценок ДЗ и баллов пробников.

Доступ к данным — только через REST API от имени текущего пользователя
(эндпоинты /me/* берут id из JWT, без student_id в URL).
"""


def build_student_view(
    page: ft.Page,
    student_id: int,
    api_token: str,
) -> ft.View:
    """Строит экран ученика."""

    headers = {"Authorization": f"Bearer {api_token}"}

    # ------------------------------------------------------------
    # Общие виджеты
    # ------------------------------------------------------------

    loading_indicator = ft.ProgressRing(visible=True, width=30, height=30)

    balance_text = ft.Text(
        "Баланс: —", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE
    )

    def show_snack(msg: str):
        page.show_dialog(ft.SnackBar(content=ft.Text(msg)))

    async def api_get(client: httpx.AsyncClient, path: str, default=None):
        try:
            resp = await client.get(path, timeout=10.0)
            return resp.json() if resp.status_code == 200 else default
        except Exception:
            return default

    # ------------------------------------------------------------
    # Вкладка 1: Расписание (карточки уроков + ДЗ + ссылки)
    # ------------------------------------------------------------

    schedule_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    async def load_schedule():
        async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
            cards = await api_get(client, "/me/lessons?upcoming_only=true", default=[]) or []

        schedule_column.controls.clear()

        if not cards:
            schedule_column.controls.append(
                ft.Text("Нет запланированных уроков", italic=True, color=ft.Colors.GREY_500)
            )

        for card in cards:
            lesson = card.get("lesson", {})
            homeworks = card.get("homeworks", [])

            start = (lesson.get("start_time") or "")[:16].replace("T", " ")
            end = (lesson.get("end_time") or "")[:16].replace("T", " ")

            links_row_children = []
            if lesson.get("video_url"):
                links_row_children.append(
                    ft.IconButton(
                        icon=ft.Icons.VIDEOCAMERA,
                        tooltip="Видеосвязь",
                        on_click=lambda e, u=lesson["video_url"]: page.launch_url(u),
                    )
                )
            if lesson.get("board_url"):
                links_row_children.append(
                    ft.IconButton(
                        icon=ft.Icons.WHITEBOARD,
                        tooltip="Онлайн-доска",
                        on_click=lambda e, u=lesson["board_url"]: page.launch_url(u),
                    )
                )

            hw_children = []
            for hw in homeworks:
                hw_children.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ui.hw_icon(hw.get("status")), size=16,
                                        color=ui.hw_color(hw.get("status"))),
                                ft.Text(
                                    f"ДЗ: {hw.get('description', '')[:70]}",
                                    size=12,
                                    expand=True,
                                ),
                                ft.Text(
                                    f"оценка: {hw['score']}" if hw.get("score") else "не оценено",
                                    size=11,
                                    italic=True,
                                    color=ui.hw_color(hw.get("status")),
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=ft.Padding(8, 4, 8, 4),
                        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE),
                        border_radius=8,
                    )
                )

            schedule_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.BOOK, color=ft.Colors.BLUE_700),
                                        ft.Text(lesson.get("subject", "—"),
                                              size=17, weight=ft.FontWeight.BOLD),
                                        ft.Container(expand=True),
                                        ui.status_chip(lesson.get("status", "")),
                                    ],
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.ACCESS_TIME, size=14,
                                                color=ft.Colors.GREY_600),
                                        ft.Text(f"{start} → {end}", size=13,
                                                color=ft.Colors.GREY_700),
                                        ft.Container(expand=True),
                                        *links_row_children,
                                    ],
                                ),
                                *(hw_children or [
                                    ft.Text("Домашнее задание не задано", size=12,
                                            italic=True, color=ft.Colors.GREY_400)
                                ]),
                            ],
                            spacing=6,
                        ),
                        padding=14,
                    ),
                    elevation=3,
                )
            )

    # ------------------------------------------------------------
    # Вкладка 2: Домашние задания (сдача файлов / «Сделал»)
    # ------------------------------------------------------------

    homeworks_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    picked_state = {"path": None, "name": None, "homework_id": None}

    async def upload_and_submit():
        hw_id = picked_state["homework_id"]
        path = picked_state["path"]
        if not hw_id or not path:
            return
        try:
            async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
                with open(path, "rb") as fh:
                    resp = await client.post(
                        "/me/uploads",
                        files={"file": (os.path.basename(path), fh.read())},
                        timeout=30.0,
                    )
                if resp.status_code != 201:
                    show_snack(f"Ошибка загрузки: {resp.text[:120]}")
                    return
                file_url = resp.json().get("file_url")

                resp = await client.post(
                    f"/homeworks/{hw_id}/submit",
                    json={"file_url": file_url},
                    timeout=10.0,
                )
            if resp.status_code == 200:
                show_snack("Решение отправлено ✅")
                await render_homeworks()
                page.update()
            else:
                show_snack(f"Не удалось сдать: {resp.text[:120]}")
        except Exception as exc:
            show_snack(f"Сбой отправки: {exc}")

    def on_file_picker_result(r: ft.FilePickerResultEvent):
        if r.files:
            picked_state["path"] = r.files[0].path
            picked_state["name"] = r.files[0].name
            page.run_task(upload_and_submit)
        else:
            show_snack("Файл не выбран")

    file_picker.on_result = on_file_picker_result

    def open_file_picker(homework_id: int):
        picked_state["homework_id"] = homework_id
        picked_state["path"] = None
        picked_state["name"] = None
        file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["jpg", "jpeg", "png", "webp", "pdf", "txt", "docx"],
            dialog_title="Выберите файл решения",
        )

    async def mark_done(hw_id: int):
        try:
            async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
                resp = await client.post(
                    f"/homeworks/{hw_id}/submit", json={}, timeout=10.0
                )
            if resp.status_code == 200:
                show_snack("Отмечено как выполненное ✅")
                await render_homeworks()
                page.update()
            else:
                show_snack(f"Ошибка: {resp.text[:120]}")
        except Exception as exc:
            show_snack(f"Сбой: {exc}")

    async def render_homeworks():
        async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
            hws = await api_get(client, "/me/reports/homework-scores", default=[]) or []

        homeworks_column.controls.clear()

        if not hws:
            homeworks_column.controls.append(
                ft.Text("Домашних заданий нет", italic=True, color=ft.Colors.GREY_500)
            )
            return

        for hw in hws:
            status = hw.get("status", "")
            deadline = (hw.get("deadline") or "")[:16].replace("T", " ")
            score_text = f"Оценка: {hw['score']}" if hw.get("score") else "Ещё не оценено"

            actions = []
            if status == "pending":
                actions = [
                    ft.FilledButton(
                        "Загрузить решение",
                        icon=ft.Icons.UPLOAD_FILE,
                        height=36,
                        text_size=12,
                        on_click=lambda e, hid=hw["id"]: open_file_picker(hid),
                    ),
                    ft.OutlinedButton(
                        "Сделал",
                        icon=ft.Icons.CHECK,
                        height=36,
                        text_size=12,
                        on_click=lambda e, hid=hw["id"]: page.run_task(mark_done, hid),
                    ),
                ]
            elif status == "submitted":
                actions = [
                    ft.Text("На проверке у преподавателя", size=12,
                            italic=True, color=ft.Colors.BLUE),
                ]

            submitted_note = (
                ft.Text(f"Файл сдан", size=11, color=ft.Colors.GREY_600)
                if hw.get("student_file_url") and status != "pending"
                else None
            )

            homeworks_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ui.hw_icon(status), color=ui.hw_color(status)),
                                        ft.Text(hw.get("description", "—")[:90],
                                              size=14, weight=ft.FontWeight.W_500,
                                              expand=True),
                                        ft.Text(score_text, size=12, italic=True,
                                              color=ui.hw_color(status)),
                                    ],
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=13,
                                                color=ft.Colors.GREY_600),
                                        ft.Text(f"Дедлайн: {deadline}", size=12,
                                                color=ft.Colors.GREY_700),
                                    ]
                                    + ([submitted_note] if submitted_note else []),
                                ),
                                *([ft.Row(actions, spacing=8)] if actions else []),
                            ],
                            spacing=6,
                        ),
                        padding=12,
                    ),
                    elevation=2,
                )
            )

    # ------------------------------------------------------------
    # Вкладка 3: Отчёты (сводка + динамики)
    # ------------------------------------------------------------

    reports_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    async def load_reports():
        async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
            summary = await api_get(client, "/me/reports", default={}) or {}
            exams = await api_get(client, "/me/reports/mock-exams", default=[]) or []
            hw_scores = await api_get(client, "/me/reports/homework-scores", default=[]) or []

        reports_column.controls.clear()

        def stat_tile(title: str, value, icon: str, color):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icon, size=22, color=color),
                        ft.Text(str(value if value is not None else "—"),
                              size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(title, size=11, color=ft.Colors.GREY_600),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                padding=10,
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.06, color),
                expand=True,
            )

        reports_column.controls.append(
            ft.Row(
                [
                    stat_tile("Уроков проведено", summary.get("lessons_completed"),
                              ft.Icons.EVENT_AVAILABLE, ft.Colors.GREEN),
                    stat_tile("Средний балл ДЗ", summary.get("homeworks_avg_score"),
                              ft.Icons.ASSIGNMENT, ft.Colors.BLUE),
                    stat_tile("Средняя отметка пробников",
                              summary.get("mock_exams_avg_grade"),
                              ft.Icons.SCHOOL, ft.Colors.PURPLE),
                ],
                spacing=8,
            )
        )

        reports_column.controls.append(
            ft.Text(
                f"ДЗ: всего {summary.get('homeworks_total', 0)}, "
                f"оценено {summary.get('homeworks_graded', 0)} · "
                f"пробников: {summary.get('mock_exams_count', 0)}",
                size=12, color=ft.Colors.GREY_700,
            )
        )

        # --- График оценок ДЗ (столбики) ---
        bars = []
        for h in hw_scores:
            if not h.get("score"):
                continue
            try:
                val = float(h["score"])
            except ValueError:
                continue
            bars.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(h["score"], size=10,
                                  weight=ft.FontWeight.BOLD,
                                  color=ft.Colors.BLUE_900),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    height=max(6, min(val, 5) * 18),
                    width=26,
                    bgcolor=ft.Colors.BLUE_200,
                    border_radius=4,
                )
            )
        if bars:
            reports_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Динамика оценок ДЗ", size=14,
                                      weight=ft.FontWeight.BOLD),
                                ft.Row(bars[-15:], alignment=ft.MainAxisAlignment.START,
                                      spacing=6,
                                      scroll=ft.ScrollMode.AUTO),
                            ]
                        ),
                        padding=12,
                    )
                )
            )

        # --- Таблица пробников ---
        if exams:
            reports_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Пробные экзамены", size=14,
                                      weight=ft.FontWeight.BOLD),
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(ft.Text(c), expand=True,
                                                           weight=ft.FontWeight.BOLD,
                                                           size=12)
                                                for c in ("Дата", "Предмет", "Баллы", "Отметка")
                                            ]
                                        ),
                                        *[
                                            ft.Row(
                                                [
                                                    ft.Container(ft.Text(str(ex.get("exam_date", ex.get("date", "")))),
                                                               expand=True, size=12),
                                                    ft.Container(ft.Text(ex.get("subject", "—")),
                                                               expand=True, size=12),
                                                    ft.Container(ft.Text(str(ex.get("primary_score", "—"))),
                                                               expand=True, size=12),
                                                    ft.Container(
                                                        ft.Text(str(ex.get("grade", "—")),
                                                              weight=ft.FontWeight.BOLD,
                                                              color=ui.grade_color(ex.get("grade"))),
                                                        expand=True, size=12),
                                                ]
                                            )
                                            for ex in exams
                                        ],
                                    ],
                                    spacing=4,
                                ),
                            ]
                        ),
                        padding=12,
                    )
                )
            )
        else:
            reports_column.controls.append(
                ft.Text("Пробников пока не было", italic=True,
                       color=ft.Colors.GREY_500)
            )

        page.update()

    # ------------------------------------------------------------
    # Табы
    # ------------------------------------------------------------

    def on_tab_change(e: ft.ControlEvent):
        if e.control.selected_index == 1:
            page.run_task(render_homeworks)
        elif e.control.selected_index == 2:
            page.run_task(load_reports)

    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        expand=True,
        tabs=[
            ft.Tab(
                text="Расписание",
                icon=ft.Icons.EVENT,
                content=ft.Container(
                    content=schedule_column, padding=ft.Padding(12, 8, 12, 8)
                ),
            ),
            ft.Tab(
                text="Домашние задания",
                icon=ft.Icons.ASSIGNMENT,
                content=ft.Container(
                    content=homeworks_column,
                    padding=ft.Padding(12, 8, 12, 8),
                ),
            ),
            ft.Tab(
                text="Отчёты",
                icon=ft.Icons.INSIGHTS,
                content=ft.Container(content=reports_column,
                                     padding=ft.Padding(12, 8, 12, 8)),
            ),
        ],
        on_change=on_tab_change,
    )

    async def load_all(e=None):
        loading_indicator.visible = True
        page.update()

        async with httpx.AsyncClient(base_url=API_BASE_URL, headers=headers) as client:
            me = await api_get(client, "/me", default={}) or {}
        balance_text.value = f"Баланс: {me.get('balance', '—')} занятий"

        await load_schedule()

        loading_indicator.visible = False
        page.update()

    page.run_task(load_all)

    return ft.View(
        "/student",
        [
            ft.AppBar(
                title=ft.Text("Кабинет Ученика"),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
                actions=[
                    ft.Container(content=balance_text,
                                 padding=ft.Padding.only(right=16)),
                ],
            ),
            ft.Container(content=loading_indicator, alignment=ft.Alignment.CENTER),
            tabs,
            ft.FloatingActionButton(
                icon=ft.Icons.REFRESH,
                on_click=load_all,
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
    # Получаем Telegram WebApp пользователя (telegram_id)
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
    # Получаем пользователя через API (без прямого доступа к БД).
    # POST /auth/webapp-identify возвращает профиль + JWT-токен.
    # TODO (Этап безопасности): серверная верификация initData.
    # --------------------------------------------------------

    if user_id:
        try:
            async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
                resp = await client.post(
                    "/auth/webapp-identify",
                    json={"telegram_id": int(user_id)},
                    timeout=10.0,
                )

                if resp.status_code == 200:
                    payload = resp.json()
                    api_token = payload.get("access_token")
                    db_user = SimpleNamespace(
                        id=payload["user"]["id"],
                        login=payload["user"]["login"],
                        role=payload["user"]["role"],
                    )
        except Exception:
            # API недоступно — останемся на странице-заглушке
            pass

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
            and db_user.role == RoleEnum.student.value
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
            and db_user.role == RoleEnum.admin.value
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
        if db_user.role == RoleEnum.student.value:
            await page.push_route("/student")

        elif db_user.role == RoleEnum.admin.value:
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
