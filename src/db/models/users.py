"""SQLAlchemy models for users and authentication."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import AuthTokenPurpose, UserRole
from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.reference import Subject


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student_profile: Mapped["StudentProfile | None"] = relationship(back_populates="user", uselist=False)
    guardians: Mapped[list["Guardian"]] = relationship(back_populates="student", foreign_keys="Guardian.student_id")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user", foreign_keys="AuthToken.user_id")
    created_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="created_by_user", foreign_keys="AuthToken.created_by")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    school_class: Mapped[int | None] = mapped_column(nullable=True)
    lesson_price: Mapped[int] = mapped_column(default=0, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    board_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    teacher_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    teacher: Mapped["User"] = relationship(foreign_keys=[teacher_id])
    subjects: Mapped[list["StudentSubject"]] = relationship(back_populates="student")


class StudentSubject(Base):
    __tablename__ = "student_subjects"

    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)

    student: Mapped["User"] = relationship(back_populates="subjects")
    subject: Mapped["Subject"] = relationship()


class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    relation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    student: Mapped["User"] = relationship(back_populates="guardians", foreign_keys=[student_id])
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    purpose: Mapped[AuthTokenPurpose] = mapped_column(SQLEnum(AuthTokenPurpose), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="auth_tokens", foreign_keys=[user_id])
    created_by_user: Mapped["User | None"] = relationship(back_populates="created_tokens", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_auth_tokens_user_purpose", "user_id", "purpose"),
    )
