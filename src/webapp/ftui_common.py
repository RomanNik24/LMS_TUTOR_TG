"""Общие UI-хелперы Mini App (цвета/иконки статусов, чипы)."""

import flet as ft


def hw_icon(status: str) -> str:
    return {
        "pending": ft.Icons.HOURGLASS_EMPTY,
        "submitted": ft.Icons.UPLOAD_FILE,
        "graded": ft.Icons.CHECK_CIRCLE,
    }.get(status, ft.Icons.HELP_OUTLINE)


def hw_color(status: str):
    return {
        "pending": ft.Colors.ORANGE,
        "submitted": ft.Colors.BLUE,
        "graded": ft.Colors.GREEN,
    }.get(status, ft.Colors.GREY)


def lesson_status_color(status: str):
    return {
        "scheduled": ft.Colors.BLUE,
        "completed": ft.Colors.GREEN,
        "cancelled": ft.Colors.RED,
        # ждёт подтверждения преподавателя — списание ещё не произошло
        "needs_confirmation": ft.Colors.ORANGE,
    }.get(status, ft.Colors.GREY)


def status_chip(status: str) -> ft.Container:
    """Цветной бейдж статуса урока/ДЗ."""
    return ft.Container(
        content=ft.Text(
            (status or "?").upper(),
            size=11,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD,
        ),
        bgcolor=lesson_status_color(status),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def grade_color(grade) -> object:
    """Цвет школьной отметки 2–5 для таблиц/графиков."""
    try:
        g = int(grade)
    except (TypeError, ValueError):
        return ft.Colors.GREY
    return {
        5: ft.Colors.GREEN,
        4: ft.Colors.LIGHT_GREEN_700,
        3: ft.Colors.ORANGE,
        2: ft.Colors.RED,
    }.get(g, ft.Colors.GREY)
