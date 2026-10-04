"""Pydantic schemas for users."""

from datetime import datetime
from typing: Optional, List
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
    school_class: Optional[int] = None
    timezone: str = "Europe/Moscow"
    video_url: Optional[str] = None
    board_url: Optional[str] = None
    teacher_notes: Optional[str] = None
    lesson_price: int = 0


class StudentCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=150)
    school_class: Optional[int] = None
    subject_ids: List[int] = []
    timezone: str = "Europe/Moscow"
    video_url: Optional[str] = None
    board_url: Optional[str] = None
    teacher_notes: Optional[str] = None
    lesson_price: int = 0
    parent_contact: Optional[str] = None


class StudentUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=150)
    school_class: Optional[int] = None
    subject_ids: Optional[List[int]] = None
    timezone: Optional[str] = None
    video_url: Optional[str] = None
    board_url: Optional[str] = None
    teacher_notes: Optional[str] = None
    lesson_price: Optional[int] = None
    parent_contact: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    id: int
    display_name: str
    timezone: str
    is_active: bool
    archived_at: Optional[datetime]
    bot_blocked: bool
    last_seen_at: Optional[datetime]
    profile: Optional[StudentProfileBase] = None

    class Config:
        from_attributes = True


class StudentCardOwnerResponse(StudentResponse):
    lesson_price: int
    teacher_notes: Optional[str] = None


class StaffCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=150)
    role: str  # owner, manager
    telegram_id: Optional[int] = None


class StaffUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None


class StaffResponse(BaseModel):
    id: int
    display_name: str
    role: str
    telegram_id: Optional[int]
    telegram_username: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True