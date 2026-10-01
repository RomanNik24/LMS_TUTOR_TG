"""timezone + needs_confirmation status

Revision ID: a1b2c3d4e5f6
Revises: f37475523ce0
Create Date: 2026-10-02 10:00:00.000000

Миграция для двух изменений схемы (этапы «напоминания» и «подтверждение уроков»):

1. users.timezone — IANA-имя часовой зоны пользователя (Europe/Moscow и т.п.).
   Заполняется ботом автоматически из Telegram-профиля
   (src/bot/handlers/base.py), используется src/core/timeutil.fmt_local
   для показа времени в локальной зоне (docs/01 п.5, docs/05 п.4).

2. lessons.status — добавлено значение 'needs_confirmation' (Enum в Postgres).
   Автозакрытие воркера теперь переводит завершившийся scheduled-урок в
   needs_confirmation БЕЗ списания баланса; списание происходит только после
   явного подтверждения преподавателем (POST /lessons/{id}/complete).
   В SQLite Enum — это VARCHAR с CHECK, поэтому ветка sqlite просто ничего
   не меняет (CHECK безымянный и SQLAlchemy его не генерирует повторно).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f37475523ce0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("timezone", sa.String(), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Расширяем существующий PostgreSQL ENUM-тип lessonstatusenum новым
        # значением. ADD VALUE IF NOT EXISTS идемпотентен; тип создан в
        # initial-миграции, поэтому create() здесь не нужен.
        # ВАЖНО: ALTER TYPE ... ADD VALUE нельзя выполнять внутри транзакции
        # с последующим использованием нового значения — Alembic по умолчанию
        # оборачивает миграцию в транзакцию, но для Postgres autocommit для
        # ALTER TYPE обеспечивается exec_driver_sql вне SQLAlchemy-транзакции
        # только если изоляция позволяет. Безопасный вариант — выполнить DDL
        # напрямую через connect().execution_options(isolation_level=...).
        bind.exec_driver_sql(
            "ALTER TYPE lessonstatusenum ADD VALUE IF NOT EXISTS 'needs_confirmation'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "timezone")
    # Значение 'needs_confirmation' из PostgreSQL ENUM удалить нельзя
    # (ALTER TYPE ... RENAME VALUE требуется для миграции строк); при откате
    # оно остаётся в типе — это безопасно: код ниже версии не использует его.
