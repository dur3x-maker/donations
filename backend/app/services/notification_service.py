from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.realtime.manager import notifications_topic, realtime_manager
from app.schemas.notification import NotificationCreatedEvent, NotificationOut


def notification_out(notification: Notification) -> NotificationOut:
    return NotificationOut(
        id=notification.id,
        type=notification.type.value,
        title=notification.title,
        body=notification.body,
        campaign_id=notification.campaign_id,
        action_url=notification.action_url,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


async def publish_notification(notification: Notification) -> None:
    await realtime_manager.broadcast(
        notifications_topic(notification.user_id),
        NotificationCreatedEvent(notification=notification_out(notification)),
    )


async def create_notification(
    session: AsyncSession,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    campaign_id: UUID | None = None,
    action_url: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        campaign_id=campaign_id,
        type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
        is_read=False,
    )
    session.add(notification)
    await session.flush()
    await publish_notification(notification)
    return notification


async def get_notifications(session: AsyncSession, user_id: UUID, page: int = 1, page_size: int = 20) -> list[NotificationOut]:
    notifications = await session.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [notification_out(notification) for notification in notifications]


async def mark_notification_read(session: AsyncSession, notification_id: UUID, user_id: UUID) -> NotificationOut | None:
    notification = await session.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    if notification is None:
        return None

    notification.is_read = True
    await session.commit()
    await session.refresh(notification)
    return notification_out(notification)


async def mark_notifications_read(
    session: AsyncSession,
    notification_ids: list[UUID],
    user_id: UUID,
) -> int:
    result = await session.execute(
        update(Notification)
        .where(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await session.commit()
    return int(result.rowcount or 0)
