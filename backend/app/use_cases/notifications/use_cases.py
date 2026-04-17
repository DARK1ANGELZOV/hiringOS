from uuid import UUID

from app.services.notification_service import NotificationService


class NotificationUseCases:
    def __init__(self, *, notification_service: NotificationService):
        self.notification_service = notification_service

    async def list(self, user_id: UUID, limit: int = 100):
        return await self.notification_service.list_for_user(user_id=user_id, limit=limit)

    async def mark_read(self, user_id: UUID, notification_id: UUID):
        return await self.notification_service.mark_read(user_id=user_id, notification_id=notification_id)

