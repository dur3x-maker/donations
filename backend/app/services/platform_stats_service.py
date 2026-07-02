from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.platform import PlatformStatsOut


async def get_platform_stats(session: AsyncSession) -> PlatformStatsOut:
    users_count = int(await session.scalar(select(func.count(User.id))) or 0)

    campaigns_total, campaigns_active, campaigns_completed, successful_reports = (
        await session.execute(
            select(
                func.count(Campaign.id),
                func.count(Campaign.id).filter(Campaign.status == CampaignStatus.active),
                func.count(Campaign.id).filter(Campaign.status == CampaignStatus.completed),
                func.count(Campaign.id).filter(
                    Campaign.status == CampaignStatus.completed,
                    Campaign.has_completion_report.is_(True),
                ),
            )
        )
    ).one()

    confirmed_contributions, total_donated_amount = (
        await session.execute(
            select(
                func.count(Contribution.id),
                func.coalesce(func.sum(Payment.amount), 0),
            )
            .select_from(Contribution)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(
                Contribution.status == ContributionStatus.confirmed,
                Payment.status == PaymentStatus.succeeded,
            )
        )
    ).one()

    return PlatformStatsOut(
        users_count=users_count,
        campaigns_total=int(campaigns_total or 0),
        campaigns_active=int(campaigns_active or 0),
        campaigns_completed=int(campaigns_completed or 0),
        successful_reports=int(successful_reports or 0),
        confirmed_contributions=int(confirmed_contributions or 0),
        total_donated_amount=Decimal(total_donated_amount or 0),
    )
