"""Admin API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session

router = APIRouter()


@router.get("/admin/dashboard/today")
async def get_dashboard_today(session: Annotated[AsyncSession, Depends(get_session)]):
    """Get today's dashboard for staff."""
    return {
        "lessons_today": [],
        "review_queue": [],
        "review_queue_total": 0,
        "not_submitted": [],
        "unmarked_lessons": [],
        "upcoming_deadlines": [],
        "earned_month": 0,
        "expected_month": 0,
    }


@router.get("/admin/students")
async def list_students(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str = "active",
    q: str = "",
    limit: int = 50,
    offset: int = 0):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/admin/students")
async def create_student(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/students/{student_id}")
async def get_student(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/students/{student_id}")
async def update_student(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/students/{student_id}/archive")
async def archive_student(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/students/{student_id}/restore")
async def restore_student(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/students/{student_id}/invitations")
async def create_invitation(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.delete("/admin/invitations/{invitation_id}")
async def revoke_invitation(invitation_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/students/{student_id}/unlink-telegram")
async def unlink_telegram(student_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/students/{student_id}/report")
async def get_student_report(
    student_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")]):
    raise NotImplementedError


@router.get("/admin/staff")
async def list_staff(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/staff")
async def create_staff(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/staff/{staff_id}")
async def update_staff(staff_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/staff/{staff_id}/invitations")
async def create_staff_invitation(staff_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/staff/{staff_id}/archive")
async def archive_staff(staff_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/lessons")
async def list_lessons(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")],
    student_id: int | None = None,
    teacher_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/admin/lessons")
async def create_lesson(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/lessons/{lesson_id}")
async def get_lesson(lesson_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/lessons/{lesson_id}")
async def update_lesson(lesson_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/lessons/{lesson_id}/reschedule")
async def reschedule_lesson(lesson_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/lessons/{lesson_id}/cancel")
async def cancel_lesson(lesson_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/schedule-templates")
async def list_templates(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/schedule-templates")
async def create_template(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/schedule-templates/{template_id}")
async def update_template(template_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/schedule-templates/{template_id}/deactivate")
async def deactivate_template(template_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/schedule-templates/generate")
async def generate_lessons(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/homework")
async def list_homework(session: Annotated[AsyncSession, Depends(get_session)], limit: int = 50, offset: int = 0):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.post("/admin/homework")
async def create_homework(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/homework/{homework_id}")
async def get_homework(homework_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/homework/{homework_id}/assignees")
async def add_assignees(homework_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/homework/{homework_id}/materials")
async def upload_material(homework_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/assignments")
async def list_assignments(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: str | None = None,
    student_id: int | None = None,
    overdue: bool | None = None,
    limit: int = 50,
    offset: int = 0):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/admin/assignments/review-queue")
async def get_review_queue(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/assignments/{assignment_id}")
async def get_assignment(assignment_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/assignments/{assignment_id}/grade")
async def grade_assignment(assignment_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/assignments/{assignment_id}/return")
async def return_for_revision(assignment_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/assignments/{assignment_id}/extend")
async def extend_deadline(assignment_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/assignments/{assignment_id}/review-files")
async def upload_review_file(assignment_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/mock-exams")
async def list_mock_exams(
    session: Annotated[AsyncSession, Depends(get_session)],
    student_id: int | None = None,
    exam_type_id: int | None = None):
    raise NotImplementedError


@router.post("/admin/mock-exams")
async def create_mock_exam(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/mock-exams/{exam_id}")
async def update_mock_exam(exam_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.delete("/admin/mock-exams/{exam_id}")
async def delete_mock_exam(exam_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/catalog")
async def list_catalog_admin(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.post("/admin/catalog")
async def create_catalog_item(session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.patch("/admin/catalog/{item_id}")
async def update_catalog_item(item_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.delete("/admin/catalog/{item_id}")
async def delete_catalog_item(item_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    raise NotImplementedError


@router.get("/admin/finance/earnings")
async def get_earnings(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")],
    group_by: str = "week"):
    raise NotImplementedError


@router.get("/admin/finance/export.csv")
async def export_finance_csv(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")]):
    raise NotImplementedError


@router.get("/admin/stats/cancellations")
async def get_cancellations(
    session: Annotated[AsyncSession, Depends(get_session)],
    from_date: Annotated[str, Query(..., alias="from")],
    to_date: Annotated[str, Query(..., alias="to")]):
    raise NotImplementedError


@router.get("/admin/audit")
async def get_audit_log(session: Annotated[AsyncSession, Depends(get_session)], limit: int = 50, offset: int = 0):
    raise NotImplementedError
