"""Notification and audit repositories."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import NotificationStatus
from src.db.models.service import AuditLog, Notification
from src.repositories import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def get_due_pending(self, limit: int = 100) -> list[Notification]:
        from datetime import datetime
        now = datetime.now()
        stmt = select(Notification).where(
            Notification.status == NotificationStatus.PENDING,
            Notification.scheduled_for <= now,
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists_dedup(self, dedup_key: str) -> bool:
        from sqlalchemy import exists
        stmt = select(exists().where(Notification.dedup_key == dedup_key))
        result = await self.session.execute(stmt)
        return result.scalar_one()


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        data: dict | None = None,
        actor_user_id: int | None = None,
    ) -> AuditLog:
        return await self.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data or {},
            actor_user_id=actor_user_id,
        )
