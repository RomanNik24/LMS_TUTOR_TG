"""Main API router."""

from fastapi import APIRouter

from src.api.v1 import auth, reference, student, admin, files

router = APIRouter()

router.include_router(auth.router, tags=["auth"])
router.include_router(reference.router, tags=["reference"])
router.include_router(student.router, prefix="/student", tags=["student"])
router.include_router(admin.router, tags=["admin"])
router.include_router(files.router, tags=["files"])