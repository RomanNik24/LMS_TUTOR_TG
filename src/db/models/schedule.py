"""SQLAlchemy models for schedule."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import LessonStatus
from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.homework import Homework
    from src.db.models.users import User


class ScheduleTemplate(Base):
    __tablename__ = "schedule_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-7 (ISO)
    start_local_time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    starts_on: Mapped[datetime] = mapped_column(Date, nullable=False)
    ends_on: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generated_until: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    participants: Mapped[list["ScheduleTemplateParticipant"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="template")

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 7", name="ck_schedule_template_weekday"),
        CheckConstraint("duration_minutes > 0", name="ck_schedule_template_duration"),
    )


class ScheduleTemplateParticipant(Base):
    __tablename__ = "schedule_template_participants"

    template_id: Mapped[int] = mapped_column(ForeignKey("schedule_templates.id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    template: Mapped["ScheduleTemplate"] = relationship(back_populates="participants")
    student: Mapped["User"] = relationship()


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[LessonStatus] = mapped_column(SQLEnum(LessonStatus), default=LessonStatus.SCHEDULED, nullable=False)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("schedule_templates.id", ondelete="SET NULL"), nullable=True)
    is_detached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    video_url_override: Mapped[str | None] = mapped_column(String(500), nullable=True)
    board_url_override: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teacher_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    template: Mapped["ScheduleTemplate | None"] = relationship(back_populates="lessons")
    participants: Mapped[list["LessonParticipant"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    homeworks: Mapped[list["Homework"]] = relationship(back_populates="lesson")

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_lesson_end_after_start"),
        UniqueConstraint("template_id", "start_at", name="uq_lesson_template_start"),
        Index("ix_lesson_start_at", "start_at"),
        Index("ix_lesson_teacher_start", "teacher_id", "start_at"),
        Index("ix_lesson_status_start", "status", "start_at"),
        # Exclusion constraint for teacher overlap (requires btree_gist extension):
        # EXCLUDE USING gist (teacher_id WITH =, tstzrange(start_at, end_at) WITH &&) WHERE (status <> 'cancelled')
    )


class LessonParticipant(Base):
    __tablename__ = "lesson_participants"

    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    attendance: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # AttendanceStatus
    is_billable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price_snapshot: Mapped[int | None] = mapped_column(nullable=True)

    lesson: Mapped["Lesson"] = relationship(back_populates="participants")
    student: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_lesson_participant_student", "student_id", "lesson_id"),
    )
