"""Pydantic schemas for homework."""

from datetime import datetime

from pydantic import BaseModel, Field


class HomeworkMaterialResponse(BaseModel):
    id: int
    s3_key: str
    original_name: str
    content_type: str
    size_bytes: int

    class Config:
        from_attributes = True


class HomeworkCreateRequest(BaseModel):
    kind: str  # regular, mock_exam
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    max_score: int = Field(..., gt=0)
    subject_id: int
    exam_type_id: int | None = None
    lesson_id: int | None = None
    due_mode: str = Field(..., pattern="^(next_lesson|fixed)$")
    due_at: datetime | None = None
    student_ids: list[int] = []


class HomeworkResponse(BaseModel):
    id: int
    created_by: int
    lesson_id: int | None
    subject_id: int
    kind: str
    exam_type_id: int | None
    title: str
    description: str | None
    max_score: int
    due_mode: str
    materials: list[HomeworkMaterialResponse] = []

    class Config:
        from_attributes = True


class HomeworkAssignmentResponse(BaseModel):
    id: int
    homework_id: int
    student_id: int
    status: str
    original_due_at: datetime
    due_at: datetime
    extensions_count: int
    submission_type: str | None
    submitted_at: datetime | None
    score: int | None
    graded_at: datetime | None
    graded_by: int | None
    graded_after_expiry: bool
    teacher_comment: str | None
    student_comment: str | None
    expired_at: datetime | None

    class Config:
        from_attributes = True


class AssignmentSubmitRequest(BaseModel):
    student_comment: str | None = None


class AssignmentGradeRequest(BaseModel):
    score: int = Field(..., ge=0)
    comment: str | None = None


class AssignmentReturnRequest(BaseModel):
    comment: str
    new_due_at: datetime | None = None


class AssignmentExtendRequest(BaseModel):
    due_at: datetime | None = None
