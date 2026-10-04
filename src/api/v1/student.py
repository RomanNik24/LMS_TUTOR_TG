"""Student API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session

router = APIRouter()


@router.get("/student/lessons")
async def get_student_lessons(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")]):
    """Get student lessons for period."""
    # TODO: Implement with auth
    return {"items": [], "total": 0, "limit": 50, "offset": 0}


@router.get("/student/lessons/{lesson_id}")
async def get_student_lesson(
    lesson_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get lesson details with links."""
    # TODO: Implement
    raise NotImplementedError


@router.get("/student/homework")
async def get_student_homework(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str = "active",
    limit: int = 50,
    offset: int = 0):
    """Get student homework assignments."""
    # TODO: Implement
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/student/homework/{assignment_id}")
async def get_student_assignment(
    assignment_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get assignment details."""
    # TODO: Implement
    raise NotImplementedError


@router.post("/student/homework/{assignment_id}/files")
async def upload_solution_file(
    assignment_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Upload solution file."""
    # TODO: Implement multipart upload
    raise NotImplementedError


@router.delete("/student/homework/{assignment_id}/files/{file_id}")
async def delete_solution_file(
    assignment_id: int,
    file_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete own solution file."""
    raise NotImplementedError


@router.post("/student/homework/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Submit assignment after file upload."""
    raise NotImplementedError


@router.post("/student/homework/{assignment_id}/self-report")
async def self_report_assignment(
    assignment_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Mark assignment as done without files."""
    raise NotImplementedError


@router.get("/student/reports")
async def get_student_reports(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")]):
    """Get report data for charts."""
    raise NotImplementedError
