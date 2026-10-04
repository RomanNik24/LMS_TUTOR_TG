"""Pydantic schemas for schedule."""

from datetime import datetime, date, time
from typing: Optional, List
from pydantic import BaseModel, Field


class ScheduleTemplateCreateRequest(BaseModel):
    teacher_id: int
    subject_id: int
    weekday: int = Field(..., ge=1, le=7)
    start_local_time: str  # HH:MM
    duration_minutes: int = Field(60, gt=0)
    timezone: str
    starts_on: date
    ends_on: Optional[date] = None
    student_ids: List[int] = []


class ScheduleTemplateUpdateRequest(BaseModel):
    weekday: Optional[int] = Field(None, ge=1, le=7)
    start_local_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    timezone: Optional[str] = None
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    is_active: Optional[bool] = None
    student_ids: Optional[List[int]] = None


class ScheduleTemplateResponse(BaseModel):
    id: int
    teacher_id: int
    subject_id: int
    weekday: int
    start_local_time: str
    duration_minutes: int
    timezone: str
    starts_on: date
    ends_on: Optional[date]
    is_active: bool
    generated_until: Optional[date]

    class Config:
        from_attributes = True


class LessonCreateRequest(BaseModel):
    subject_id: int
    teacher_id: int
    start_at: datetime
    end_at: datetime
    student_ids: List[int]
    video_url_override: Optional[str] = None
    board_url_override: Optional[str] = None
    topic: Optional[str] = None


class LessonRescheduleRequest(BaseModel):
    start_at: datetime
    end_at: datetime


class LessonCancelRequest(BaseModel):
    reason: str
    billable_student_ids: List[int] = []


class LessonCompleteRequest(BaseModel):
    attendances: List[dict]  # [{"student_id": int, "attendance": str, "is_billable": bool}]


class LessonParticipantResponse(BaseModel):
    student_id: int
    attendance: str
    is_billable: bool
    price_snapshot: Optional[int] = None

    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    teacher_id: int
    subject_id: int
    start_at: datetime
    end_at: datetime
    status: str
    template_id: Optional[int]
    is_detached: bool
    video_url_override: Optional[str]
    board_url_override: Optional[str]
    topic: Optional[str]
    teacher_note: Optional[str]
    participants: List[LessonParticipantResponse] = []

    class Config:
        from_attributes = True