"""SQLAlchemy models for mock exams."""

from datetime import datetime
from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class MockExamResult(Base):
    __tablename__ = "mock_exam_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    exam_type_id: Mapped[int] = mapped_column(ForeignKey("exam_types.id"), nullable=False)
    exam_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    primary_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_primary: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    converted_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scale_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("homework_assignments.id", ondelete="SET NULL"), unique=True, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student: Mapped["User"] = relationship(foreign_keys=[student_id])
    exam_type: Mapped["ExamType"] = relationship()
    assignment: Mapped["HomeworkAssignment | None"] = relationship(back_populates="mock_exam_result")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])

    __table_args__ = (
        CheckConstraint("primary_score >= 0", name="ck_mock_exam_primary_nonneg"),
        CheckConstraint("max_primary > 0", name="ck_mock_exam_max_primary_positive"),
        Index("ix_mock_exam_student_type_date", "student_id", "exam_type_id", "exam_date"),
    )