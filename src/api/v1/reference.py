"""Reference API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.repositories.reference import ExamTypeRepository, SubjectRepository
from src.schemas.user import ExamTypeResponse, SubjectResponse

router = APIRouter()


@router.get("/reference/subjects", response_model=list[SubjectResponse])
async def get_subjects(session: Annotated[AsyncSession, Depends(get_session)]):
    repo = SubjectRepository(session)
    subjects = await repo.list(is_active=True)
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.get("/reference/exam-types", response_model=list[ExamTypeResponse])
async def get_exam_types(session: Annotated[AsyncSession, Depends(get_session)]):
    repo = ExamTypeRepository(session)
    exams = await repo.get_active()
    return [ExamTypeResponse.model_validate(e) for e in exams]


@router.get("/catalog", response_model=list)
async def get_catalog(session: Annotated[AsyncSession, Depends(get_session)]):
    from src.repositories.catalog import CatalogRepository
    repo = CatalogRepository(session)
    items = await repo.get_published()
    return [{"id": i.id, "title": i.title, "description": i.description, "price_text": i.price_text} for i in items]
