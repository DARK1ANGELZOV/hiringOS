from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_notification_use_cases
from app.api.serializers import notification_to_schema
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.use_cases.notifications.use_cases import NotificationUseCases

router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('', response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(default=100, ge=1, le=200),
    use_cases: NotificationUseCases = Depends(get_notification_use_cases),
    current_user: User = Depends(get_current_user),
):
    items, unread_count = await use_cases.list(user_id=UUID(str(current_user.id)), limit=limit)
    return NotificationListResponse(items=[notification_to_schema(item) for item in items], unread_count=unread_count)


@router.patch('/{notification_id}/read', response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    use_cases: NotificationUseCases = Depends(get_notification_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = await use_cases.mark_read(user_id=UUID(str(current_user.id)), notification_id=notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notification not found')
    await db.commit()
    return notification_to_schema(notification)
