"""Homework service: assignments, grading, extensions."""

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.homework import HomeworkRepository, HomeworkAssignmentRepository, HomeworkFileRepository
from src.repositories.user import UserRepository
from src.repositories.service import AuditLogRepository
from src.services.schedule import ScheduleService
from src.core.exceptions import NotFoundError, PermissionDeniedError, BusinessRuleError
from src.core.enums import UserRole, HomeworkKind, HomeworkStatus, FileRole
from src.db.models.homework import Homework, HomeworkAssignment, HomeworkFile, HomeworkExtension
from src.db.models.users import User
from src.core.timeutils import utc_now


class HomeworkService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.homeworks = HomeworkRepository(session)
        self.assignments = HomeworkAssignmentRepository(session)
        self.files = HomeworkFileRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditLogRepository(session)

    async def create_homework(
        self,
        actor: User,
        kind: HomeworkKind,
        title: str,
        description: Optional[str],
        max_score: int,
        subject_id: int,
        exam_type_id: Optional[int],
        lesson_id: Optional[int],
        due_mode: str,  # next_lesson, fixed
        due_at: Optional[datetime],
        student_ids: list[int],
    ) -> Homework:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_homework")

        if kind == HomeworkKind.MOCK_EXAM and not exam_type_id:
            raise BusinessRuleError("exam_type_required", "Для пробника нужен тип экзамена")

        hw = await self.homeworks.create(
            created_by=actor.id,
            kind=kind,
            title=title,
            description=description,
            max_score=max_score,
            subject_id=subject_id,
            exam_type_id=exam_type_id,
            lesson_id=lesson_id,
            due_mode=due_mode,
        )

        for student_id in student_ids:
            student = await self.users.get(student_id)
            if not student or student.role != UserRole.STUDENT:
                raise NotFoundError("Student", student_id)

            # Calculate due_at if next_lesson
            actual_due = due_at
            if due_mode == "next_lesson":
                # Find next scheduled lesson for this student
                from src.repositories.schedule import LessonRepository
                lessons_repo = LessonRepository(self.session)
                next_lesson = await lessons_repo.get_next_for_student(student_id, utc_now())
                if next_lesson:
                    actual_due = next_lesson.start_at
                else:
                    actual_due = utc_now() + timedelta(days=7)

            await self.assignments.create(
                homework_id=hw.id,
                student_id=student_id,
                original_due_at=actual_due,
                due_at=actual_due,
                status=HomeworkStatus.ASSIGNED,
            )

        await self.audit.log(
            action="homework.created",
            entity_type="homework",
            entity_id=hw.id,
            data={"kind": kind.value, "title": title, "student_count": len(student_ids)},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return hw

    async def submit_files(
        self,
        student: User,
        assignment_id: int,
        file_keys: list[str],  # S3 keys
        student_comment: Optional[str],
    ) -> HomeworkAssignment:
        assignment = await self.assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        if assignment.student_id != student.id:
            raise PermissionDeniedError("submit_files")

        if assignment.status not in (HomeworkStatus.ASSIGNED, HomeworkStatus.NEEDS_REVISION):
            raise BusinessRuleError("invalid_status", "Нельзя сдать в текущем статусе")

        if assignment.status == HomeworkStatus.EXPIRED:
            raise BusinessRuleError("expired", "Срок сдачи истёк, сдать нельзя")

        # Check file count limit
        current_count = await self.files.count_student_files(assignment_id)
        if current_count + len(file_keys) > 10:
            raise BusinessRuleError("file_limit", "Можно загрузить до 10 файлов")

        for key in file_keys:
            # File metadata should be stored separately after upload
            pass  # Files are uploaded via separate endpoint

        assignment.status = HomeworkStatus.SUBMITTED
        assignment.submitted_at = utc_now()
        assignment.submission_type = "files"
        assignment.student_comment = student_comment

        await self.audit.log(
            action="homework.submitted",
            entity_type="homework_assignment",
            entity_id=assignment_id,
            data={"files_count": len(file_keys)},
            actor_user_id=student.id,
        )
        await self.session.commit()
        return assignment

    async def submit_self_reported(
        self,
        student: User,
        assignment_id: int,
        student_comment: Optional[str],
    ) -> HomeworkAssignment:
        assignment = await self.assignments.get(assignment_id)
        if not assignment or assignment.student_id != student.id:
            raise NotFoundError("Assignment", assignment_id)

        if assignment.status not in (HomeworkStatus.ASSIGNED, HomeworkStatus.NEEDS_REVISION):
            raise BusinessRuleError("invalid_status", "Нельзя сдать в текущем статусе")

        if assignment.status == HomeworkStatus.EXPIRED:
            raise BusinessRuleError("expired", "Срок сдачи истёк, сдать нельзя")

        assignment.status = HomeworkStatus.SUBMITTED
        assignment.submitted_at = utc_now()
        assignment.submission_type = "self_reported"
        assignment.student_comment = student_comment

        await self.session.commit()
        return assignment

    async def grade_assignment(
        self,
        actor: User,
        assignment_id: int,
        score: int,
        comment: Optional[str],
        review_file_keys: list[str],
    ) -> HomeworkAssignment:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("grade_assignment")

        assignment = await self.assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        hw = await self.homeworks.get(assignment.homework_id)
        if not hw:
            raise NotFoundError("Homework", assignment.homework_id)

        if score < 0 or score > hw.max_score:
            raise BusinessRuleError("score_out_of_range", f"Балл должен быть от 0 до {hw.max_score}")

        assignment.score = score
        assignment.status = HomeworkStatus.GRADED
        assignment.graded_at = utc_now()
        assignment.graded_by = actor.id
        assignment.teacher_comment = comment

        # If mock exam, create/update exam result
        if hw.kind == HomeworkKind.MOCK_EXAM and hw.exam_type_id:
            from src.services.exam import ExamService
            exam_service = ExamService(self.session)
            await exam_service.create_from_homework(hw, assignment)

        await self.audit.log(
            action="homework.graded",
            entity_type="homework_assignment",
            entity_id=assignment_id,
            data={"score": score, "max_score": hw.max_score},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return assignment

    async def return_for_revision(
        self,
        actor: User,
        assignment_id: int,
        comment: str,
        new_due_at: Optional[datetime] = None,
    ) -> HomeworkAssignment:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("return_for_revision")

        assignment = await self.assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        assignment.status = HomeworkStatus.NEEDS_REVISION
        assignment.teacher_comment = comment
        if new_due_at:
            assignment.due_at = new_due_at

        await self.session.commit()
        return assignment

    async def extend_deadline(
        self,
        actor: User,
        assignment_id: int,
        new_due_at: Optional[datetime] = None,
    ) -> HomeworkAssignment:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("extend_deadline")

        assignment = await self.assignments.get(assignment_id)
        if not assignment:
            raise NotFoundError("Assignment", assignment_id)

        if assignment.extensions_count >= 2:
            raise BusinessRuleError("homework_extension_limit", "Дедлайн уже переносили 2 раза")

        if assignment.status not in (HomeworkStatus.ASSIGNED, HomeworkStatus.NEEDS_REVISION):
            raise BusinessRuleError("invalid_status", "Нельзя перенести в текущем статусе")

        old_due = assignment.due_at
        if new_due_at:
            assignment.due_at = new_due_at
        else:
            # Find next lesson for this student
            from src.repositories.schedule import LessonRepository
            lessons = LessonRepository(self.session)
            next_lesson = await lessons.get_next_for_student(assignment.student_id, old_due)
            if next_lesson:
                assignment.due_at = next_lesson.start_at
            else:
                assignment.due_at = old_due + timedelta(days=7)

        assignment.extensions_count += 1

        await self.session.execute(
            HomeworkExtension.__table__.insert().values(
                assignment_id=assignment_id,
                old_due_at=old_due,
                new_due_at=assignment.due_at,
                created_by=actor.id,
            )
        )

        await self.audit.log(
            action="homework.extended",
            entity_type="homework_assignment",
            entity_id=assignment_id,
            data={
                "old_due_at": old_due.isoformat(),
                "new_due_at": assignment.due_at.isoformat(),
                "extensions_count": assignment.extensions_count,
            },
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return assignment

    async def expire_assignments(self) -> int:
        """Mark overdue assignments as expired. Returns count."""
        expired = await self.assignments.get_expired_candidates()
        count = 0
        for assignment in expired:
            assignment.status = HomeworkStatus.EXPIRED
            assignment.expired_at = utc_now()
            count += 1
        if count:
            await self.session.commit()
        return count