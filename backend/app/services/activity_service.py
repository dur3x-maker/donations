from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity, ActivityType
from app.schemas.activity import ActivityCampaignOut, ActivityOut
from app.schemas.common import OwnerOut


async def create_activity(
    session: AsyncSession,
    activity_type: ActivityType,
    actor_user_id: UUID | None = None,
    campaign_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> Activity:
    activity = Activity(
        type=activity_type,
        actor_user_id=actor_user_id,
        campaign_id=campaign_id,
        metadata_json=metadata_json,
    )
    session.add(activity)
    await session.flush()
    return activity


async def create_once_activity(
    session: AsyncSession,
    activity_type: ActivityType,
    actor_user_id: UUID | None = None,
    campaign_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> Activity | None:
    existing = await session.scalar(
        select(Activity).where(
            Activity.type == activity_type,
            Activity.actor_user_id == actor_user_id,
            Activity.campaign_id == campaign_id,
        )
    )
    if existing is not None:
        return None
    return await create_activity(session, activity_type, actor_user_id, campaign_id, metadata_json)


async def get_activity_feed(session: AsyncSession, page: int = 1, page_size: int = 20) -> list[ActivityOut]:
    activities = await session.scalars(
        select(Activity)
        .options(selectinload(Activity.actor), selectinload(Activity.campaign))
        .order_by(desc(Activity.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [
        ActivityOut(
            id=activity.id,
            type=activity.type.value,
            actor=OwnerOut.model_validate(activity.actor) if activity.actor else None,
            campaign=ActivityCampaignOut(id=activity.campaign.id, title=activity.campaign.title) if activity.campaign else None,
            metadata_json=activity.metadata_json,
            created_at=activity.created_at,
        )
        for activity in activities
    ]
