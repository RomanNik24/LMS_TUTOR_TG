"""Staff service: manage employees."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import UserRole
from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.db.models.users import User
from src.repositories.service import AuditLogRepository
from src.repositories.user import UserRepository
from src.services.auth import AuthService


class StaffService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.auth = AuthService(session)
        self.audit = AuditLogRepository(session)

    async def create_staff(self, actor: User, display_name: str, role: UserRole, telegram_id: int | None = None) -> User:
        if actor.role != UserRole.OWNER:
            raise PermissionDeniedError("create_staff")
        if role not in (UserRole.OWNER, UserRole.MANAGER):
            raise PermissionDeniedError("invalid_role")

        user = await self.users.create(
            role=role,
            display_name=display_name,
            telegram_id=telegram_id,
            timezone="Europe/Moscow",
        )
        await self.audit.log(
            action="staff.created",
            entity_type="user",
            entity_id=user.id,
            data={"role": role.value, "display_name": display_name},
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return user

    async def update_staff(self, actor: User, staff_id: int, display_name: str | None, role: UserRole | None) -> User:
        if actor.role != UserRole.OWNER:
            raise PermissionDeniedError("update_staff")
        if role == UserRole.OWNER:
            raise PermissionDeniedError("cannot_promote_to_owner")

        staff = await self.users.get(staff_id)
        if not staff or staff.role not in (UserRole.OWNER, UserRole.MANAGER):
            raise NotFoundError("Staff", staff_id)

        if display_name:
            staff.display_name = display_name
        if role:
            old_role = staff.role
            staff.role = role
            await self.audit.log(
                action="staff.role_changed",
                entity_type="user",
                entity_id=staff_id,
                data={"old_role": old_role.value, "new_role": role.value},
                actor_user_id=actor.id,
            )

        await self.session.commit()
        return staff

    async def archive_staff(self, actor: User, staff_id: int) -> User:
        if actor.role != UserRole.OWNER:
            raise PermissionDeniedError("archive_staff")

        staff = await self.users.get(staff_id)
        if not staff:
            raise NotFoundError("Staff", staff_id)

        staff.is_active = False
        staff.archived_at = datetime.now()
        await self.auth.revoke_all_sessions(staff_id)

        await self.audit.log(
            action="staff.archived",
            entity_type="user",
            entity_id=staff_id,
            actor_user_id=actor.id,
        )
        await self.session.commit()
        return staff
