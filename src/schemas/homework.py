"""Pydantic schemas for homework."""

from datetime import datetime
from typing: Optional, List
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
    description: Optional[str] = None
    max_score: int = Field(..., gt=0)
    subject_id: int
    exam_type_id: Optional[int] = None
    lesson_id: Optional[int] = None
    due_mode: str = Field(..., pattern="^(next_lesson|fixed)$")
    due_at: Optional[datetime] = None
    student_ids: List[int] = []


class HomeworkResponse(BaseModel):
    id: int
    created_by: int
    lesson_id: Optional[int]
    subject_id: int
    kind: str
    exam_type_id: Optional[int]
    title: str
    description: Optional[str]
    max_score: int
    due_mode: str
    materials: List[HomeworkMaterialResponse] = []

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
    submission_type: Optional[str]
    submitted_at: Optional[datetime]
    score: Optional[int]
    graded_at: Optional[datetime]
    graded_by: Optional[int]
    graded_after_expiry: bool
    teacher_comment: Optional[str]
    student_comment: Optional[str]
    expired_at: Optional[datetime]

    class Config:
        from_attributes = True


class AssignmentSubmitRequest(BaseModel):
    student_comment: Optional[str] = None


class AssignmentGradeRequest(BaseModel):
    score: int = Field(..., ge=0)
    comment: Optional[str] = None


class AssignmentReturnRequest(BaseModel):
    comment: str
    new_due_at: Optional[datetime] = None


class AssignmentExtendRequest(BaseModel):
    due_at: Optional[datetime] = None