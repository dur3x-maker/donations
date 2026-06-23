from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.user import CommunityPatronCampaignOut, CommunityPatronOut
from app.services.level_service import current_level_for


async def get_community_patrons(session: AsyncSession) -> list[CommunityPatronOut]:
    rows = await session.execute(
        select(
            User.id,
            User.username,
            User.patron_since,
            func.count(Contribution.id).label("confirmed_count"),
            func.count(func.distinct(Contribution.campaign_id)).label("supported_campaigns_count"),
            func.coalesce(func.sum(Contribution.amount), 0).label("total_donated_amount"),
        )
        .join(Contribution, Contribution.user_id == User.id)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .join(Campaign, Campaign.id == Contribution.campaign_id)
        .where(
            User.patron_since.is_not(None),
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount > 0,
            Campaign.owner_id != User.id,
        )
        .group_by(User.id, User.username, User.patron_since)
        .order_by(User.username)
    )

    patron_rows = list(rows)
    patron_ids = [user_id for user_id, _, patron_since, count, _, _ in patron_rows if patron_since is not None and int(count or 0) >= 50]
    recent_campaigns: dict = defaultdict(list)
    if patron_ids:
        supported_campaigns = (
            select(
                Contribution.user_id.label("user_id"),
                Contribution.campaign_id.label("campaign_id"),
                func.max(Contribution.created_at).label("last_supported_at"),
            )
            .join(Payment, Payment.contribution_id == Contribution.id)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .where(
                Contribution.user_id.in_(patron_ids),
                Contribution.status == ContributionStatus.confirmed,
                Payment.status == PaymentStatus.succeeded,
                Contribution.amount > 0,
                Campaign.owner_id != Contribution.user_id,
            )
            .group_by(Contribution.user_id, Contribution.campaign_id)
            .subquery()
        )
        ranked_campaigns = (
            select(
                supported_campaigns.c.user_id,
                supported_campaigns.c.campaign_id,
                supported_campaigns.c.last_supported_at,
                func.row_number().over(
                    partition_by=supported_campaigns.c.user_id,
                    order_by=supported_campaigns.c.last_supported_at.desc(),
                ).label("position"),
            )
            .subquery()
        )
        campaign_rows = await session.execute(
            select(
                ranked_campaigns.c.user_id,
                Campaign.id,
                Campaign.title,
                Campaign.cover_image_url,
                ranked_campaigns.c.last_supported_at,
            )
            .join(Campaign, Campaign.id == ranked_campaigns.c.campaign_id)
            .where(ranked_campaigns.c.position <= 3)
            .order_by(ranked_campaigns.c.user_id, ranked_campaigns.c.position)
        )
        for user_id, campaign_id, title, cover_image_url, last_supported_at in campaign_rows:
            recent_campaigns[user_id].append(
                CommunityPatronCampaignOut(
                    id=campaign_id,
                    title=title,
                    cover_image_url=cover_image_url,
                    last_supported_at=last_supported_at,
                )
            )

    patrons = []
    for user_id, username, patron_since, confirmed_count, supported_count, total_amount in patron_rows:
        count = int(confirmed_count or 0)
        level = current_level_for(count)
        if patron_since is None or count < 50:
            continue
        patrons.append(
            CommunityPatronOut(
                user_id=user_id,
                username=username,
                level=level.title if level else "",
                confirmed_contributions_count=count,
                supported_campaigns_count=int(supported_count or 0),
                total_donated_amount=str(total_amount),
                patron_since=patron_since,
                recent_supported_campaigns=recent_campaigns[user_id],
            )
        )
    return patrons
