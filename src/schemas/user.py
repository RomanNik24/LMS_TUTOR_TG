"""Pydantic schemas for users."""

from datetime import datetime

from pydantic import BaseModel, Field


class SubjectResponse(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class ExamTypeResponse(BaseModel):
    id: int
    code: str
    subject_id: int
    kind: str
    result_kind: str
    max_primary: int
    name: str
    config: dict
    is_active: bool

    class Config:
        from_attributes = True


class StudentProfileBase(BaseModel):
    school_class: int | None = None
    timezone: str = "Europe/Moscow"
    video_url: str | None = None
    board_url: str | None = None
    teacher_notes: str | None = None
    lesson_price: int = 0


class StudentCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=150)
    school_class: int | None = None
    subject_ids: list[int] = []
    timezone: str = "Europe/Moscow"
    video_url: str | None = None
    board_url: str | None = None
    teacher_notes: str | None = None
    lesson_price: int = 0
    parent_contact: str | None = None


class StudentUpdateRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=150)
    school_class: int | None = None
    subject_ids: list[int] | None = None
    timezone: str | None = None
    video_url: str | None = None
    board_url: str | None = None
    teacher_notes: str | None = None
    lesson_price: int | None = None
    parent_contact: str | None = None
    is_active: bool | None = None


class StudentResponse(BaseModel):
    id: int
    display_name: str
    timezone: str
    is_active: bool
    archived_at: datetime | None
    bot_blocked: bool
    last_seen_at: datetime | None
    profile: StudentProfileBase | None = None

    class Config:
        from_attributes = True


class StudentCardOwnerResponse(StudentResponse):
    lesson_price: int
    teacher_notes: str | None = None


class StaffCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=150)
    role: str  # owner, manager
    telegram_id: int | None = None


class StaffUpdateRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None


class StaffResponse(BaseModel):
    id: int
    display_name: str
    role: str
    telegram_id: int | None
    telegram_username: str | None
    is_active: bool

    class Config:
        from_attributes = True
