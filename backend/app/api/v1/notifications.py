from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.services.notification_service import get_notifications, mark_notification_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationOut]:
    return await get_notifications(session, current_user.id, page=page, page_size=page_size)


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def read_notification(
    notification_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationOut:
    notification = await mark_notification_read(session, notification_id, current_user.id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification
