from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.business_rules import CAMPAIGN_CLOSED_FOR_DONATIONS_MESSAGE, MIN_DONATION_AMOUNT, MIN_DONATION_AMOUNT_MESSAGE, can_accept_donation
from app.core.security import generate_anonymous_token
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.realtime.manager import CATALOG_TOPIC, campaign_topic, dashboard_topic, realtime_manager
from app.schemas.contribution import CampaignUpdatedEvent, DonateIn, RecentDonationOut, RecentDonationsPageOut
from app.services.campaign_service import get_campaign_or_404, get_contributors_count
from app.services.payment_service import confirm_payment, create_payment
from app.services.follow_up_service import get_campaign_subscription
from app.services.suspicious_flag_service import maybe_flag_high_donation, maybe_flag_many_token_donations


def _progress_percentage(current_amount: Decimal, target_amount: Decimal) -> int:
    if target_amount <= 0:
        return 0
    return min(100, int((Decimal(current_amount) / Decimal(target_amount)) * 100))


def _donation_out(contribution: Contribution) -> RecentDonationOut:
    return RecentDonationOut(
        id=contribution.id,
        amount=contribution.amount,
        username=contribution.user.username if contribution.user else "Анонимно",
        created_at=contribution.created_at,
    )


async def donate(
    session: AsyncSession,
    campaign_id: UUID,
    payload: DonateIn,
    current_user: User | None,
) -> tuple[Payment, str | None, bool]:
    campaign = await get_campaign_or_404(session, campaign_id)
    if payload.amount < MIN_DONATION_AMOUNT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MIN_DONATION_AMOUNT_MESSAGE)
    if not can_accept_donation(campaign):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CAMPAIGN_CLOSED_FOR_DONATIONS_MESSAGE)

    anonymous_token = None if current_user else payload.anonymous_token or generate_anonymous_token()
    subscription_created = bool(
        current_user
        and await get_campaign_subscription(session, current_user.id, campaign.id) is None
    )
    try:
        contribution = Contribution(
            campaign_id=campaign.id,
            user_id=current_user.id if current_user else None,
            anonymous_token=anonymous_token,
            amount=payload.amount,
            status=ContributionStatus.pending,
        )
        session.add(contribution)
        await session.flush()

        payment = await create_payment(
            session,
            contribution,
            provider="mock",
            currency="RUB",
            metadata_json={"provider_mode": "immediate_success"},
        )
        await confirm_payment(session, payment)
        await maybe_flag_high_donation(session, current_user.id if current_user else None, campaign.id, contribution.amount)
        await maybe_flag_many_token_donations(session, anonymous_token, campaign.id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(contribution)
    await session.refresh(campaign)
    await session.refresh(payment)
    if current_user:
        contribution.user = current_user

    contributors_count = await get_contributors_count(session, campaign.id)
    update_event = CampaignUpdatedEvent(
            campaign_id=campaign.id,
            current_amount=campaign.current_amount,
            goal_amount=campaign.target_amount,
            progress_percentage=_progress_percentage(campaign.current_amount, campaign.target_amount),
            contributors_count=contributors_count,
            donation=_donation_out(contribution),
    )
    await realtime_manager.broadcast(campaign_topic(campaign.id), update_event)
    await realtime_manager.broadcast(CATALOG_TOPIC, update_event)
    await realtime_manager.broadcast(dashboard_topic(campaign.owner_id), update_event)
    return payment, anonymous_token, subscription_created


async def get_recent_donations(
    session: AsyncSession,
    campaign_id: UUID,
    offset: int = 0,
    limit: int = 3,
) -> RecentDonationsPageOut:
    await get_campaign_or_404(session, campaign_id)
    donations = list(await session.scalars(
        select(Contribution)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .options(selectinload(Contribution.user))
        .where(
            Contribution.campaign_id == campaign_id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount > 0,
        )
        .order_by(desc(Contribution.created_at))
        .offset(offset)
        .limit(limit + 1)
    ))
    return RecentDonationsPageOut(
        items=[_donation_out(contribution) for contribution in donations[:limit]],
        has_more=len(donations) > limit,
    )
