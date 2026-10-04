"""Pydantic schemas for schedule."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ScheduleTemplateCreateRequest(BaseModel):
    teacher_id: int
    subject_id: int
    weekday: int = Field(..., ge=1, le=7)
    start_local_time: str  # HH:MM
    duration_minutes: int = Field(60, gt=0)
    timezone: str
    starts_on: date
    ends_on: date | None = None
    student_ids: list[int] = []


class ScheduleTemplateUpdateRequest(BaseModel):
    weekday: int | None = Field(None, ge=1, le=7)
    start_local_time: str | None = None
    duration_minutes: int | None = Field(None, gt=0)
    timezone: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool | None = None
    student_ids: list[int] | None = None


class ScheduleTemplateResponse(BaseModel):
    id: int
    teacher_id: int
    subject_id: int
    weekday: int
    start_local_time: str
    duration_minutes: int
    timezone: str
    starts_on: date
    ends_on: date | None
    is_active: bool
    generated_until: date | None

    class Config:
        from_attributes = True


class LessonCreateRequest(BaseModel):
    subject_id: int
    teacher_id: int
    start_at: datetime
    end_at: datetime
    student_ids: list[int]
    video_url_override: str | None = None
    board_url_override: str | None = None
    topic: str | None = None


class LessonRescheduleRequest(BaseModel):
    start_at: datetime
    end_at: datetime


class LessonCancelRequest(BaseModel):
    reason: str
    billable_student_ids: list[int] = []


class LessonCompleteRequest(BaseModel):
    attendances: list[dict]  # [{"student_id": int, "attendance": str, "is_billable": bool}]


class LessonParticipantResponse(BaseModel):
    student_id: int
    attendance: str
    is_billable: bool
    price_snapshot: int | None = None

    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    teacher_id: int
    subject_id: int
    start_at: datetime
    end_at: datetime
    status: str
    template_id: int | None
    is_detached: bool
    video_url_override: str | None
    board_url_override: str | None
    topic: str | None
    teacher_note: str | None
    participants: list[LessonParticipantResponse] = []

    class Config:
        from_attributes = True
