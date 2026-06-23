from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_subscription import CampaignSubscription
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.notification_service import publish_notification


async def subscribe_user_to_campaign(
    session: AsyncSession,
    user_id: UUID | None,
    campaign_id: UUID,
) -> tuple[CampaignSubscription | None, bool]:
    if user_id is None:
        return None, False

    await session.scalar(select(User.id).where(User.id == user_id).with_for_update())
    existing = await session.scalar(
        select(CampaignSubscription).where(
            CampaignSubscription.user_id == user_id,
            CampaignSubscription.campaign_id == campaign_id,
        )
    )
    if existing is not None:
        if not existing.is_active or existing.muted:
            existing.is_active = True
            existing.muted = False
            await session.flush()
        return existing, False

    subscription = CampaignSubscription(user_id=user_id, campaign_id=campaign_id, is_active=True, muted=False)
    session.add(subscription)
    await session.flush()
    return subscription, True


async def get_campaign_subscription(
    session: AsyncSession,
    user_id: UUID,
    campaign_id: UUID,
) -> CampaignSubscription | None:
    return await session.scalar(
        select(CampaignSubscription).where(
            CampaignSubscription.user_id == user_id,
            CampaignSubscription.campaign_id == campaign_id,
        )
    )


async def set_campaign_subscription(
    session: AsyncSession,
    user_id: UUID,
    campaign_id: UUID,
    *,
    is_active: bool,
) -> CampaignSubscription:
    subscription = await get_campaign_subscription(session, user_id, campaign_id)
    if subscription is None:
        subscription = CampaignSubscription(
            user_id=user_id,
            campaign_id=campaign_id,
            is_active=is_active,
            muted=False,
        )
        session.add(subscription)
    else:
        subscription.is_active = is_active
        if is_active:
            subscription.muted = False
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def create_follow_up_notification(
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


async def notify_campaign_subscribers(
    session: AsyncSession,
    campaign_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    action_url: str | None = None,
    exclude_user_id: UUID | None = None,
) -> int:
    conditions = [
        CampaignSubscription.campaign_id == campaign_id,
        CampaignSubscription.is_active.is_(True),
        CampaignSubscription.muted.is_(False),
    ]
    if exclude_user_id is not None:
        conditions.append(CampaignSubscription.user_id != exclude_user_id)

    user_ids = list(await session.scalars(select(CampaignSubscription.user_id).where(*conditions)))
    if not user_ids:
        return 0

    notifications = [
        Notification(
            user_id=user_id,
            campaign_id=campaign_id,
            type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            is_read=False,
        )
        for user_id in user_ids
    ]
    session.add_all(notifications)
    await session.flush()
    for notification in notifications:
        await publish_notification(notification)
    return len(user_ids)
