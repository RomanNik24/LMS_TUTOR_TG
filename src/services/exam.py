"""Exam service: mock exams, score conversion."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.db.models.exam import MockExamResult
from src.db.models.homework import Homework, HomeworkAssignment
from src.db.models.reference import ExamType
from src.db.models.users import User
from src.repositories.exam import ExamTypeRepository, GradeScaleRepository, MockExamResultRepository
from src.repositories.homework import HomeworkAssignmentRepository
from src.repositories.service import AuditLogRepository


class ExamService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.results = MockExamResultRepository(session)
        self.exam_types = ExamTypeRepository(session)
        self.scales = GradeScaleRepository(session)
        self.assignments = HomeworkAssignmentRepository(session)
        self.audit = AuditLogRepository(session)

    def convert_score(self, exam_type: ExamType, primary_score: int, max_primary: int, geometry_score: int | None = None) -> tuple[int | None, int | None]:
        """
        Convert primary score to result value.
        Returns (converted_value, scale_year) or (None, None) if not applicable.
        """
        if max_primary != exam_type.max_primary:
            return None, None  # Non-standard max, no conversion

        # Get latest applicable scale
        scales = self.scales.get_scale_for_exam(exam_type.id, date.today().year)
        if not scales:
            return None, None

        # Find matching primary score
        for scale in scales:
            if scale.primary_score == primary_score:
                converted = scale.result_value
                scale_year = scale.valid_year

                # OGE Math geometry rule
                if exam_type.code == "oge_math" and geometry_score is not None:
                    min_geometry = exam_type.config.get("min_geometry", 2)
                    if geometry_score < min_geometry and primary_score >= 8:
                        converted = 2  # Force grade 2

                return converted, scale_year

        return None, None

    async def record_mock_result(
        self,
        actor: User,
        student_id: int,
        exam_type_id: int,
        exam_date: date,
        primary_score: int,
        max_primary: int,
        geometry_score: int | None = None,
        assignment_id: int | None = None,
        comment: str | None = None,
    ) -> MockExamResult:
        exam_type = await self.exam_types.get(exam_type_id)
        if not exam_type:
            raise NotFoundError("ExamType", exam_type_id)

        converted, scale_year = self.convert_score(exam_type, primary_score, max_primary, geometry_score)

        result = await self.results.create(
            student_id=student_id,
            exam_type_id=exam_type_id,
            exam_date=exam_date,
            primary_score=primary_score,
            max_primary=max_primary,
            geometry_score=geometry_score,
            converted_value=converted,
            scale_year=scale_year,
            assignment_id=assignment_id,
            comment=comment,
            created_by=actor.id,
        )

        await self.audit.log(
            action="mock_exam.recorded",
            entity_type="mock_exam_result",
            entity_id=result.id,
            data={
                "student_id": student_id,
                "exam_type_id": exam_type_id,
                "primary_score": primary_score,
                "converted": converted,
            },
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return result

    async def create_from_homework(self, homework: "Homework", assignment: HomeworkAssignment) -> MockExamResult:
        """Create exam result from graded mock exam homework."""
        if homework.kind != "mock_exam" or not homework.exam_type_id:
            return None

        if assignment.score is None:
            return None

        exam_type = await self.exam_types.get(homework.exam_type_id)
        if not exam_type:
            return None

        converted, scale_year = self.convert_score(exam_type, assignment.score, homework.max_primary)

        return await self.results.create(
            student_id=assignment.student_id,
            exam_type_id=homework.exam_type_id,
            exam_date=assignment.graded_at.date() if assignment.graded_at else date.today(),
            primary_score=assignment.score,
            max_primary=homework.max_primary,
            converted_value=converted,
            scale_year=scale_year,
            assignment_id=assignment.id,
            created_by=assignment.graded_by or 0,
        )
