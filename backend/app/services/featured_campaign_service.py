from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, CampaignStatus
from app.models.platform_setting import PlatformSetting
from app.models.user import User


class FeaturedCampaignUserNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("Пользователь не найден.")


class FeaturedCampaignActiveCampaignNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("У пользователя сейчас нет активной истории.")


async def find_active_campaign_by_username(session: AsyncSession, username: str) -> Campaign:
    normalized_username = username.strip().removeprefix("@").lower()
    user = await session.scalar(select(User).where(User.username == normalized_username))
    if user is None:
        raise FeaturedCampaignUserNotFoundError

    campaign = await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(
            Campaign.owner_id == user.id,
            Campaign.status == CampaignStatus.active,
            Campaign.is_active.is_(True),
        )
        .with_for_update()
    )
    if campaign is None:
        raise FeaturedCampaignActiveCampaignNotFoundError
    return campaign


async def set_featured_campaign_by_username(session: AsyncSession, username: str) -> Campaign:
    campaign = await find_active_campaign_by_username(session, username)
    await _store_featured_campaign_id(session, campaign.id)
    return campaign


async def get_featured_campaign(session: AsyncSession) -> Campaign | None:
    platform_settings = await session.get(PlatformSetting, 1)
    if platform_settings and platform_settings.featured_campaign_id:
        selected = await _active_campaign_by_id(session, platform_settings.featured_campaign_id)
        if selected is not None:
            return selected

    fallback = await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(
            Campaign.status == CampaignStatus.active,
            Campaign.is_active.is_(True),
        )
        .order_by(desc(Campaign.created_at))
        .limit(1)
    )
    fallback_id = fallback.id if fallback else None
    if platform_settings is None or platform_settings.featured_campaign_id != fallback_id:
        await _store_featured_campaign_id(session, fallback_id)
    return fallback


async def _active_campaign_by_id(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(
            Campaign.id == campaign_id,
            Campaign.status == CampaignStatus.active,
            Campaign.is_active.is_(True),
        )
    )


async def _store_featured_campaign_id(session: AsyncSession, campaign_id: UUID | None) -> None:
    statement = (
        insert(PlatformSetting)
        .values(id=1, featured_campaign_id=campaign_id)
        .on_conflict_do_update(
            index_elements=[PlatformSetting.id],
            set_={"featured_campaign_id": campaign_id},
        )
    )
    await session.scalar(
        statement.returning(PlatformSetting),
        execution_options={"populate_existing": True},
    )
    await session.commit()
