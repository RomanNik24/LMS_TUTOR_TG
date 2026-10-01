from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    login: str
    balance: int
    lesson_price: int

    model_config = ConfigDict(from_attributes=True)


class LessonResponse(BaseModel):
    id: int
    student_id: int
    subject: str
    start_time: datetime
    end_time: datetime
    status: str
    video_url: Optional[str] = None
    board_url: Optional[str] = None
    # Роль владельца урока — заполняется на уровне API (для UI ученика)
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LessonCardItem(BaseModel):
    """Карточка урока для ученика: урок + привязанные ДЗ (docs/01, п.4.1)."""

    lesson: LessonResponse
    homeworks: List["HomeworkDetailResponse"] = []


class ReportSummaryResponse(BaseModel):
    """Сводка прогресса ученика для модуля «Отчёты»."""

    lessons_completed: int
    homeworks_total: int
    homeworks_graded: int
    homeworks_avg_score: Optional[float] = None
    mock_exams_count: int
    mock_exams_avg_grade: Optional[float] = None


class MePasswordRequest(BaseModel):
    new_password: str


class HomeworkResponse(BaseModel):
    id: int
    lesson_id: int
    description: str
    deadline: datetime
    status: str
    score: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BalanceResponse(BaseModel):
    balance: int


class CreateStudentRequest(BaseModel):
    login: str
    password: str
    balance: int = 0
    lesson_price: int = 1000


class CreateLessonRequest(BaseModel):
    subject: str
    start_time: datetime
    end_time: datetime
    video_url: Optional[str] = None
    board_url: Optional[str] = None

class WebAppIdentifyRequest(BaseModel):
    telegram_id: int


class WebAppUserBrief(BaseModel):
    id: int
    login: str
    role: str


class WebAppIdentifyResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: WebAppUserBrief


# ─────────────── Этап 1: уроки / ДЗ / пробники / статистика ───────────────


class UpdateLessonRequest(BaseModel):
    subject: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    video_url: Optional[str] = None
    board_url: Optional[str] = None


class CreateHomeworkRequest(BaseModel):
    lesson_id: int
    description: str
    deadline: datetime


class SubmitHomeworkRequest(BaseModel):
    file_url: Optional[str] = None


class GradeHomeworkRequest(BaseModel):
    score: str


class HomeworkDetailResponse(BaseModel):
    id: int
    lesson_id: int
    student_id: int
    description: str
    deadline: datetime
    status: str
    student_file_url: Optional[str] = None
    score: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CreateMockExamRequest(BaseModel):
    subject: str
    primary_score: int
    date: Optional[date] = None
    grade: Optional[int] = None


class MockExamResponse(BaseModel):
    id: int
    student_id: int
    date: date
    subject: str
    primary_score: int
    grade: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class BalanceUpdateRequest(BaseModel):
    delta: int


class LessonPriceRequest(BaseModel):
    lesson_price: int


class StudentProgressResponse(BaseModel):
    student_id: int
    login: str
    balance: int
    lessons_completed: int
    homeworks_total: int
    homeworks_pending: int
    mock_exams_avg_grade: Optional[float] = None
    debtors_flag: bool


class DashboardResponse(BaseModel):
    date: str
    today_lessons: List[LessonResponse]
    students_without_homework: List[int]
    debtors: List[int]
    cancelled_count: int


class EarningsResponse(BaseModel):
    start: datetime
    end: datetime
    earned: int
