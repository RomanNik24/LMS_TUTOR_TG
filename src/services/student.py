"""Student service: profiles, invitations."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.db.models.users import StudentSubject, User
from src.repositories.reference import SubjectRepository
from src.repositories.service import AuditLogRepository
from src.repositories.user import StudentProfileRepository, UserRepository
from src.services.auth import AuthService


class StudentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.profiles = StudentProfileRepository(session)
        self.subjects = SubjectRepository(session)
        self.auth = AuthService(session)
        self.audit = AuditLogRepository(session)

    async def create_student(
        self,
        actor: User,
        display_name: str,
        school_class: int | None,
        subject_ids: list[int],
        timezone: str,
        video_url: str | None,
        board_url: str | None,
        teacher_notes: str | None,
        lesson_price: int,
        parent_contact: str | None,
    ) -> User:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_student")

        # Validate subjects
        for sid in subject_ids:
            subj = await self.subjects.get(sid)
            if not subj:
                raise NotFoundError("Subject", sid)

        user = await self.users.create(
            role=UserRole.STUDENT,
            display_name=display_name,
            timezone=timezone,
            is_active=True,
        )
        profile = await self.profiles.create(  # noqa: F841  # TODO: профиль используется далее на этапе auth
            user_id=user.id,
            teacher_id=actor.id,
            school_class=school_class,
            lesson_price=lesson_price,
            video_url=video_url,
            board_url=board_url,
            teacher_notes=teacher_notes,
        )
        for sid in subject_ids:
            await self.session.execute(
                StudentSubject.__table__.insert().values(student_id=user.id, subject_id=sid)
            )

        await self.audit.log(
            action="student.created",
            entity_type="user",
            entity_id=user.id,
            data={"display_name": display_name, "teacher_id": actor.id},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return user

    async def update_student(
        self,
        actor: User,
        student_id: int,
        **fields,
    ) -> User:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("update_student")

        student = await self.users.get(student_id)
        if not student or student.role != UserRole.STUDENT:
            raise NotFoundError("Student", student_id)

        # Only owner can change price
        if "lesson_price" in fields and actor.role != UserRole.OWNER:
            raise PermissionDeniedError("change_lesson_price")

        # Update user fields
        user_fields = {k: v for k, v in fields.items() if k in ("display_name", "timezone", "is_active")}
        for k, v in user_fields.items():
            setattr(student, k, v)

        # Update profile fields
        profile = await self.profiles.get(student_id)
        if profile:
            profile_fields = {k: v for k, v in fields.items() if k in (
                "school_class", "lesson_price", "video_url", "board_url", "teacher_notes"
            )}
            for k, v in profile_fields.items():
                setattr(profile, k, v)

            if "subject_ids" in fields:
                await self.session.execute(
                    StudentSubject.__table__.delete().where(StudentSubject.student_id == student_id)
                )
                for sid in fields["subject_ids"]:
                    await self.session.execute(
                        StudentSubject.__table__.insert().values(student_id=student_id, subject_id=sid)
                    )

        await self.audit.log(
            action="student.updated",
            entity_type="user",
            entity_id=student_id,
            data=fields,
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return student

    async def archive_student(self, actor: User, student_id: int) -> User:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("archive_student")

        student = await self.users.get(student_id)
        if not student:
            raise NotFoundError("Student", student_id)

        student.is_active = False
        student.archived_at = datetime.now()
        # Revoke sessions
        await self.auth.revoke_all_sessions(student_id)

        await self.audit.log(
            action="student.archived",
            entity_type="user",
            entity_id=student_id,
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return student

    async def restore_student(self, actor: User, student_id: int) -> User:
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("restore_student")

        student = await self.users.get(student_id)
        if not student:
            raise NotFoundError("Student", student_id)

        student.is_active = True
        student.archived_at = None

        await self.audit.log(
            action="student.restored",
            entity_type="user",
            entity_id=student_id,
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return student

    async def create_invitation(self, actor: User, student_id: int) -> tuple[str, str]:
        """Create invitation. Returns (url, expires_at_iso)."""
        if actor.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("create_invitation")

        student = await self.users.get(student_id)
        if not student or student.role != UserRole.STUDENT:
            raise NotFoundError("Student", student_id)

        raw_token, token = await self.auth.create_invite(actor, student_id)
        # Build URL
        from src.core.config import settings
        url = f"https://t.me/{settings.BOT_USERNAME}?start=inv_{raw_token}"
        return url, token.expires_at.isoformat()

    async def get_student_card(self, actor: User, student_id: int) -> dict:
        """Get student card data (different fields per role)."""
        student = await self.users.get(student_id)
        if not student:
            raise NotFoundError("Student", student_id)

        profile = await self.profiles.get(student_id)

        base = {
            "id": student.id,
            "display_name": student.display_name,
            "school_class": profile.school_class if profile else None,
            "timezone": student.timezone,
            "is_active": student.is_active,
            "bot_blocked": student.bot_blocked,
            "last_seen_at": student.last_seen_at.isoformat() if student.last_seen_at else None,
        }

        if actor.role == UserRole.OWNER and profile:
            base["lesson_price"] = profile.lesson_price
            base["teacher_notes"] = profile.teacher_notes

        return base
