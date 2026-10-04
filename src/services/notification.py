"""Notification service: outbox pattern."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import NotificationStatus
from src.core.timeutils import utc_now
from src.db.models.service import Notification
from src.db.models.users import User
from src.repositories.service import NotificationRepository
from src.repositories.user import UserRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.notifications = NotificationRepository(session)
        self.users = UserRepository(session)

    async def enqueue(
        self,
        user_id: int,
        type: str,
        payload: dict,
        dedup_key: str,
        is_urgent: bool = False,
        scheduled_for: datetime | None = None,
    ) -> Notification:
        """Add notification to outbox."""
        if scheduled_for is None:
            scheduled_for = utc_now()

        # Check deduplication
        if await self.notifications.exists_dedup(dedup_key):
            return None  # Already exists

        notification = await self.notifications.create(
            user_id=user_id,
            type=type,
            payload=payload,
            dedup_key=dedup_key,
            is_urgent=is_urgent,
            scheduled_for=scheduled_for,
            status=NotificationStatus.PENDING,
        )
        await self.session.commit()
        return notification

    async def get_due(self, limit: int = 100) -> list[Notification]:
        """Get notifications ready to send."""
        return await self.notifications.get_due_pending(limit)

    async def mark_sent(self, notification: Notification) -> None:
        notification.status = NotificationStatus.SENT
        notification.sent_at = utc_now()
        await self.session.commit()

    async def mark_failed(self, notification: Notification, error: str) -> None:
        notification.attempts += 1
        notification.last_error = error
        if notification.attempts >= 3:
            notification.status = NotificationStatus.FAILED
        await self.session.commit()

    async def mark_skipped(self, notification: Notification) -> None:
        notification.status = NotificationStatus.SKIPPED
        await self.session.commit()

    async def build_morning_digest(self, user: User) -> dict:
        """Build morning digest payload for user."""
        # TODO: Aggregate data for digest
        return {
            "date": utc_now().date().isoformat(),
            "lessons": [],
            "review_queue_count": 0,
            "not_submitted_count": 0,
            "unmarked_count": 0,
            "upcoming_deadlines_count": 0,
        }
