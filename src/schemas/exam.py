"""Pydantic schemas for exams."""

from datetime import date
from typing: Optional
from pydantic import BaseModel, Field


class MockExamResultCreateRequest(BaseModel):
    student_id: int
    exam_type_id: int
    exam_date: date
    primary_score: int = Field(..., ge=0)
    max_primary: int = Field(..., gt=0)
    geometry_score: Optional[int] = None
    comment: Optional[str] = None


class MockExamResultUpdateRequest(BaseModel):
    primary_score: Optional[int] = Field(None, ge=0)
    max_primary: Optional[int] = Field(None, gt=0)
    geometry_score: Optional[int] = None
    comment: Optional[str] = None


class MockExamResultResponse(BaseModel):
    id: int
    student_id: int
    exam_type_id: int
    exam_date: date
    primary_score: int
    max_primary: int
    geometry_score: Optional[int]
    converted_value: Optional[int]
    scale_year: Optional[int]
    assignment_id: Optional[int]
    comment: Optional[str]

    class Config:
        from_attributes = True