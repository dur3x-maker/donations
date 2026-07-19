import logging
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import log_event
from app.models.campaign import Campaign, CampaignStatus
from app.models.platform_setting import PlatformSetting
from app.models.user import User

logger = logging.getLogger("featured_campaign")


def _trace(step: str, **fields) -> None:
    log_event(logger, logging.INFO, "telegram_promo_trace", step=step, **fields)


class FeaturedCampaignUserNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("Пользователь не найден.")


class FeaturedCampaignActiveCampaignNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("У пользователя сейчас нет активной истории.")


class FeaturedCampaignMultipleActiveCampaignsError(Exception):
    def __init__(self) -> None:
        super().__init__("У пользователя найдено несколько активных сборов.")


class FeaturedCampaignAlreadySelectedError(Exception):
    def __init__(self) -> None:
        super().__init__("Сбор уже является главным.")


async def find_active_campaign_by_username(session: AsyncSession, username: str) -> Campaign:
    normalized_username = username.strip().removeprefix("@").lower()
    _trace(
        "featured_user_lookup_start",
        supplied_username=username,
        normalized_username=normalized_username,
    )
    user = await session.scalar(select(User).where(User.username == normalized_username))
    _trace(
        "featured_user_lookup_result",
        normalized_username=normalized_username,
        found=user is not None,
        user_id=str(user.id) if user else None,
    )
    if user is None:
        raise FeaturedCampaignUserNotFoundError

    _trace("featured_active_campaign_lookup_start", user_id=str(user.id), username=user.username)
    campaigns = list(
        await session.scalars(
            select(Campaign)
            .options(selectinload(Campaign.owner))
            .where(
                Campaign.owner_id == user.id,
                Campaign.status == CampaignStatus.active,
                Campaign.is_active.is_(True),
            )
            .with_for_update()
        )
    )
    _trace(
        "featured_active_campaign_lookup_result",
        user_id=str(user.id),
        username=user.username,
        count=len(campaigns),
        campaign_ids=[str(campaign.id) for campaign in campaigns],
        statuses=[campaign.status.value for campaign in campaigns],
        is_active_values=[campaign.is_active for campaign in campaigns],
    )
    if not campaigns:
        raise FeaturedCampaignActiveCampaignNotFoundError
    if len(campaigns) > 1:
        raise FeaturedCampaignMultipleActiveCampaignsError
    return campaigns[0]


async def set_featured_campaign_by_username(session: AsyncSession, username: str) -> Campaign:
    _trace("featured_update_service_enter", username=username)
    campaign = await find_active_campaign_by_username(session, username)
    already_featured = await is_featured_campaign(session, campaign.id)
    _trace(
        "featured_update_current_check",
        username=username,
        campaign_id=str(campaign.id),
        already_featured=already_featured,
    )
    if already_featured:
        raise FeaturedCampaignAlreadySelectedError
    _trace("featured_campaign_id_store_start", username=username, campaign_id=str(campaign.id))
    await _store_featured_campaign_id(session, campaign.id)
    _trace("featured_campaign_id_store_committed", username=username, campaign_id=str(campaign.id))
    return campaign


async def is_featured_campaign(session: AsyncSession, campaign_id: UUID) -> bool:
    platform_settings = await session.get(PlatformSetting, 1)
    current_campaign_id = platform_settings.featured_campaign_id if platform_settings else None
    result = current_campaign_id == campaign_id
    _trace(
        "featured_campaign_id_read",
        requested_campaign_id=str(campaign_id),
        current_campaign_id=str(current_campaign_id) if current_campaign_id else None,
        matches=result,
    )
    return result


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
