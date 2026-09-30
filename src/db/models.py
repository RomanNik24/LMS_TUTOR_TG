import enum
from typing import Optional
from datetime import datetime, date

from sqlalchemy import Integer, String, Enum, Text, DateTime, Date, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    student = "student"


class LessonStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class HomeworkStatusEnum(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum))
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    login: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    lesson_price: Mapped[int] = mapped_column(Integer, default=0)

    lessons: Mapped[list["Lesson"]] = relationship(back_populates="student")
    mock_exams: Mapped[list["MockExam"]] = relationship(back_populates="student")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[LessonStatusEnum] = mapped_column(Enum(LessonStatusEnum))

    student: Mapped["User"] = relationship(back_populates="lessons")
    homeworks: Mapped[list["Homework"]] = relationship(back_populates="lesson")


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[HomeworkStatusEnum] = mapped_column(Enum(HomeworkStatusEnum))
    student_file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    lesson: Mapped["Lesson"] = relationship(back_populates="homeworks")


class MockExam(Base):
    __tablename__ = "mock_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    subject: Mapped[str] = mapped_column(String)
    primary_score: Mapped[int] = mapped_column(Integer)
    grade: Mapped[int] = mapped_column(Integer)

    student: Mapped["User"] = relationship(back_populates="mock_exams")
