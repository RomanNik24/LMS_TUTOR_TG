from datetime import datetime
from typing import Optional

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

    model_config = ConfigDict(from_attributes=True)


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
