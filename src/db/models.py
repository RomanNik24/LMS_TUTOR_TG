import enum
from typing import Optional
from datetime import datetime, date, timezone

from sqlalchemy import (
    Integer,
    String,
    Enum,
    Text,
    DateTime,
    Date,
    ForeignKey,
    BigInteger,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def utcnow() -> datetime:
    """Текущее время в UTC (для timestamp-колонок и дефолтов)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RoleEnum(str, enum.Enum):
    admin = "admin"
    student = "student"


class LessonStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    # Автозакрытие воркера не списывает баланс: урок попадает сюда,
    # пока преподаватель не подтвердит факт проведения (или не отменит).
    needs_confirmation = "needs_confirmation"


class HomeworkStatusEnum(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum))
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, unique=True
    )
    login: Mapped[str] = mapped_column(String, unique=True)
    # Пароли не используются (docs/09 §2.4): вход только по приглашениям и
    # верифицированной initData. Колонка оставлена nullable для совместимости
    # с существующей БД; новый код её не читает и не пишет.
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    lesson_price: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now()
    )

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="student")
    mock_exams: Mapped[list["MockExam"]] = relationship(back_populates="student")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        # Индексы для частых выборок: расписание ученика и лента по времени
        Index("ix_lessons_student_id", "student_id"),
        Index("ix_lessons_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[LessonStatusEnum] = mapped_column(Enum(LessonStatusEnum))
    # Ссылки на материалы занятия (docs/01: видеоконференция, онлайн-доска)
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    board_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now()
    )

    student: Mapped["User"] = relationship(back_populates="lessons")
    homeworks: Mapped[list["Homework"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )


class Homework(Base):
    __tablename__ = "homeworks"
    __table_args__ = (Index("ix_homeworks_lesson_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[HomeworkStatusEnum] = mapped_column(Enum(HomeworkStatusEnum))
    student_file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now()
    )

    lesson: Mapped["Lesson"] = relationship(back_populates="homeworks")


class AuthTokenPurposeEnum(str, enum.Enum):
    invite = "invite"


class AuthToken(Base):
    """Одноразовые токены приглашений (docs/04 §auth_tokens, docs/09 §2.4).

    В БД хранится ТОЛЬКО SHA-256 хэш токена — сырое значение известно лишь
    моменту выдачи (ссылка t.me/<bot>?start=inv_<token>). TTL — 7 дней,
    использование — однократное (used_at), отзыв — revoked_at.
    """

    __tablename__ = "auth_tokens"
    __table_args__ = (Index("ix_auth_tokens_user_purpose", "user_id", "purpose"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[AuthTokenPurposeEnum] = mapped_column(
        Enum(AuthTokenPurposeEnum, name="authtokenpurpose"),
        default=AuthTokenPurposeEnum.invite,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now()
    )


class MockExam(Base):
    __tablename__ = "mock_exams"
    __table_args__ = (Index("ix_mock_exams_student_id", "student_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    subject: Mapped[str] = mapped_column(String)
    primary_score: Mapped[int] = mapped_column(Integer)
    grade: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now()
    )

    student: Mapped["User"] = relationship(back_populates="mock_exams")
