"""Files API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session

router = APIRouter()


@router.get("/files/{file_id}/url")
async def get_file_url(file_id: int, session: AsyncSession = Depends(get_session)):
    """Get presigned URL for file access."""
    # TODO: Check permissions, generate presigned URL
    return {"url": "https://s3.example.com/presigned-url", "expires_in": 600}