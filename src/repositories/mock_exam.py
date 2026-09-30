from src.db.models import MockExam
from .base import BaseRepository

class MockExamRepository(BaseRepository[MockExam]):
    def __init__(self):
        super().__init__(MockExam)
