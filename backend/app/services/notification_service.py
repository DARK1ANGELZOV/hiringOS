from uuid import UUID

from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self.repository = repository

    async def create(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ):
        return await self.repository.create(
            user_id=user_id,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    async def list_for_user(self, user_id: UUID, limit: int = 100):
        items = await self.repository.list_for_user(user_id, limit=limit)
        unread_count = await self.repository.unread_count(user_id)
        return items, unread_count

    async def mark_read(self, user_id: UUID, notification_id: UUID):
        notification = await self.repository.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            return None
        return await self.repository.mark_read(notification)

