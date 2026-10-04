"""SQLAlchemy models for homework."""

import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base
from src.core.enums import HomeworkKind, HomeworkStatus, FileRole


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    kind: Mapped[HomeworkKind] = mapped_column(SQLEnum(HomeworkKind), nullable=False)
    exam_type_id: Mapped[int | None] = mapped_column(ForeignKey("exam_types.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    due_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # next_lesson, fixed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    lesson: Mapped["Lesson | None"] = relationship(back_populates="homeworks")
    materials: Mapped[list["HomeworkMaterial"]] = relationship(back_populates="homework", cascade="all, delete-orphan")
    assignments: Mapped[list["HomeworkAssignment"]] = relationship(back_populates="homework", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("max_score > 0", name="ck_homework_max_score_positive"),
    )


class HomeworkMaterial(Base):
    __tablename__ = "homework_materials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    homework: Mapped["Homework"] = relationship(back_populates="materials")


class HomeworkAssignment(Base):
    __tablename__ = "homework_assignments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[HomeworkStatus] = mapped_column(SQLEnum(HomeworkStatus), default=HomeworkStatus.ASSIGNED, nullable=False)
    original_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extensions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submission_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # files, self_reported
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    graded_after_expiry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    teacher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    homework: Mapped["Homework"] = relationship(back_populates="assignments")
    student: Mapped["User"] = relationship()
    files: Mapped[list["HomeworkFile"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")
    extensions: Mapped[list["HomeworkExtension"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")
    mock_exam_result: Mapped["MockExamResult | None"] = relationship(back_populates="assignment", uselist=False)

    __table_args__ = (
        UniqueConstraint("homework_id", "student_id", name="uq_homework_assignment"),
        CheckConstraint("extensions_count BETWEEN 0 AND 2", name="ck_homework_assignment_extensions"),
        CheckConstraint("score >= 0", name="ck_homework_assignment_score_nonneg"),
        Index("ix_homework_assignment_student_status", "student_id", "status"),
        Index("ix_homework_assignment_status_due", "status", "due_at"),
        Index("ix_homework_assignment_homework", "homework_id"),
    )


class HomeworkExtension(Base):
    __tablename__ = "homework_extensions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("homework_assignments.id", ondelete="CASCADE"), nullable=False)
    old_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assignment: Mapped["HomeworkAssignment"] = relationship(back_populates="extensions")
    creator: Mapped["User"] = relationship()


class HomeworkFile(Base):
    __tablename__ = "homework_files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("homework_assignments.id", ondelete="CASCADE"), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[FileRole] = mapped_column(SQLEnum(FileRole), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assignment: Mapped["HomeworkAssignment"] = relationship(back_populates="files")
    uploader: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_homework_file_assignment", "assignment_id"),
    )