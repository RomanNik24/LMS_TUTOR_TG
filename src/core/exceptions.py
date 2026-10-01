"""Кастомные исключения приложения (требование docs/06_agent_rules.md, п.3).

Сервисный слой выбрасывает только эти исключения; API-слой транслирует
их в HTTP-коды, бот — в сообщения пользователю.
"""


class AppError(Exception):
    """Базовое исключение приложения."""


class NotFoundError(AppError):
    """Сущность не найдена (транслируется в HTTP 404)."""


class ValidationError(AppError):
    """Ошибка бизнес-валидации (транслируется в HTTP 422/400)."""


class ConflictError(AppError):
    """Конфликт состояния (дубликат логина, пересечение слотов) — HTTP 409."""


class InsufficientBalanceError(AppError):
    """Недостаточно оплаченных занятий для списания — HTTP 402."""
