from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.campaign import Campaign
from app.models.contribution import Contribution
from app.models.suspicious_flag import SuspiciousFlag
from app.services.moderation_alert_service import send_moderation_alert


async def create_suspicious_flag(
    session: AsyncSession,
    flag_type: str,
    user_id: UUID | None = None,
    campaign_id: UUID | None = None,
    metadata_json: dict | None = None,
) -> SuspiciousFlag:
    flag = SuspiciousFlag(
        type=flag_type,
        user_id=user_id,
        campaign_id=campaign_id,
        metadata_json=metadata_json,
    )
    session.add(flag)
    await session.flush()
    await send_moderation_alert("suspicious_flag_generated", {"type": flag_type, "user_id": str(user_id) if user_id else None, "campaign_id": str(campaign_id) if campaign_id else None})
    return flag


async def maybe_flag_many_campaigns(session: AsyncSession, user_id: UUID) -> None:
    since = utcnow() - timedelta(hours=1)
    count = await session.scalar(select(func.count(Campaign.id)).where(Campaign.owner_id == user_id, Campaign.created_at >= since))
    if int(count or 0) >= 3:
        await create_suspicious_flag(session, "too_many_campaigns_quickly", user_id=user_id, metadata_json={"campaigns_last_hour": int(count or 0)})


async def maybe_flag_high_donation(session: AsyncSession, user_id: UUID | None, campaign_id: UUID, amount) -> None:
    if amount >= 100000:
        await create_suspicious_flag(session, "high_value_donation", user_id=user_id, campaign_id=campaign_id, metadata_json={"amount": str(amount)})


async def maybe_flag_many_token_donations(session: AsyncSession, anonymous_token: str | None, campaign_id: UUID) -> None:
    if not anonymous_token:
        return
    since = utcnow() - timedelta(hours=1)
    count = await session.scalar(select(func.count(Contribution.id)).where(Contribution.anonymous_token == anonymous_token, Contribution.created_at >= since))
    if int(count or 0) >= 10:
        await create_suspicious_flag(session, "too_many_donations_from_token", campaign_id=campaign_id, metadata_json={"anonymous_token": anonymous_token, "donations_last_hour": int(count or 0)})
