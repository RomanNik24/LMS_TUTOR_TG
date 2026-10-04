"""SQLAlchemy models for reference tables."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ExamType(Base):
    __tablename__ = "exam_types"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # oge, ege
    result_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # grade_2_5, test_100
    max_primary: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default={}, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subject: Mapped["Subject"] = relationship()


class GradeScale(Base):
    __tablename__ = "grade_scales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    exam_type_id: Mapped[int] = mapped_column(
        ForeignKey("exam_types.id", ondelete="CASCADE"), nullable=False
    )
    valid_year: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_score: Mapped[int] = mapped_column(Integer, nullable=False)
    result_value: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_type_id", "valid_year", "primary_score", name="uq_grade_scale"),
        CheckConstraint("primary_score >= 0", name="ck_grade_scale_primary_nonneg"),
    )

    exam_type: Mapped["ExamType"] = relationship()


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
