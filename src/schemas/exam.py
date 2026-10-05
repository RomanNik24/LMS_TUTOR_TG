"""Pydantic schemas for exams."""

from datetime import date

from pydantic import BaseModel, Field


class MockExamResultCreateRequest(BaseModel):
    student_id: int
    exam_type_id: int
    exam_date: date
    primary_score: int = Field(..., ge=0)
    max_primary: int = Field(..., gt=0)
    geometry_score: int | None = None
    comment: str | None = None


class MockExamResultUpdateRequest(BaseModel):
    primary_score: int | None = Field(None, ge=0)
    max_primary: int | None = Field(None, gt=0)
    geometry_score: int | None = None
    comment: str | None = None


class MockExamResultResponse(BaseModel):
    id: int
    student_id: int
    exam_type_id: int
    exam_date: date
    primary_score: int
    max_primary: int
    geometry_score: int | None
    converted_value: int | None
    scale_year: int | None
    assignment_id: int | None
    comment: str | None

    class Config:
        from_attributes = True
