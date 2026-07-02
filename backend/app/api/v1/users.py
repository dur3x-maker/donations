from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_current_user
from app.core.business_rules import MIN_DONATION_AMOUNT
from app.db.session import get_session
from app.models.campaign import Campaign
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.campaign import CampaignListItem
from app.schemas.common import OwnerOut
from app.schemas.user import AuthorReputationOut, PublicUserProfileOut, UnlockProgressOut
from app.services.user_service import REQUIRED_CONFIRMED_DONATIONS, can_create_campaign, get_confirmed_donation_count

router = APIRouter(prefix="/users", tags=["users"])


async def get_author_reputation_summary(session: AsyncSession, user_id: UUID) -> AuthorReputationOut:
    user_exists = await session.scalar(select(User.id).where(User.id == user_id))
    if user_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    campaigns_created, campaigns_completed, campaigns_with_reports, campaigns_without_reports, total_raised_amount = (
        await session.execute(
            select(
                func.count(Campaign.id),
                func.count(Campaign.id).filter(Campaign.has_completion_report.is_(True)),
                func.count(Campaign.id).filter(Campaign.has_completion_report.is_(True)),
                func.count(Campaign.id).filter(Campaign.report_overdue.is_(True)),
                func.coalesce(func.sum(Campaign.current_amount), 0),
            ).where(Campaign.owner_id == user_id)
        )
    ).one()
    created_count = int(campaigns_created or 0)
    reports_count = int(campaigns_with_reports or 0)
    return AuthorReputationOut(
        campaigns_created=created_count,
        campaigns_completed=int(campaigns_completed or 0),
        campaigns_with_reports=reports_count,
        campaigns_without_reports=int(campaigns_without_reports or 0),
        total_raised_amount=str(total_raised_amount or Decimal("0")),
    )


@router.get("/me/unlock-progress", response_model=UnlockProgressOut)
async def unlock_progress(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> UnlockProgressOut:
    confirmed_donations = await get_confirmed_donation_count(session, current_user.id)
    remaining = max(0, REQUIRED_CONFIRMED_DONATIONS - confirmed_donations)
    return UnlockProgressOut(
        confirmed_donations=confirmed_donations,
        required_donations=REQUIRED_CONFIRMED_DONATIONS,
        can_create_campaign=await can_create_campaign(session, current_user.id),
        remaining=remaining,
    )


@router.get("/{user_id}/reputation", response_model=AuthorReputationOut)
async def author_reputation(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AuthorReputationOut:
    return await get_author_reputation_summary(session, user_id)


@router.get("/{username}", response_model=PublicUserProfileOut)
async def public_profile(
    username: str,
    session: AsyncSession = Depends(get_session),
) -> PublicUserProfileOut:
    user = await session.scalar(select(User).where(User.username == username.lower()))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    total_supported_campaigns = await session.scalar(
        select(func.count(distinct(Contribution.campaign_id)))
        .join(Payment, Payment.contribution_id == Contribution.id)
        .where(
            Contribution.user_id == user.id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount >= MIN_DONATION_AMOUNT,
        )
    )
    total_donated_amount = await session.scalar(
        select(func.coalesce(func.sum(Contribution.amount), 0))
        .join(Payment, Payment.contribution_id == Contribution.id)
        .where(
            Contribution.user_id == user.id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount >= MIN_DONATION_AMOUNT,
        )
    )
    campaigns = await session.scalars(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(Campaign.owner_id == user.id, Campaign.is_active.is_(True))
        .order_by(desc(Campaign.created_at))
    )
    campaigns_created = list(campaigns)
    completed_campaigns_count = sum(1 for campaign in campaigns_created if campaign.has_completion_report)
    supported_count = int(total_supported_campaigns or 0)
    achievements = []
    if supported_count >= 1:
        achievements.append("first_support")
    if supported_count >= 5:
        achievements.append("supporter_5")
    if campaigns_created:
        achievements.append("campaign_creator")
    if completed_campaigns_count:
        achievements.append("fundraiser_completed")

    campaign_items: list[CampaignListItem] = []
    for campaign in campaigns_created:
        contributors_count = await session.scalar(
            select(func.count(Contribution.id))
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(
                Contribution.campaign_id == campaign.id,
                Contribution.status == ContributionStatus.confirmed,
                Payment.status == PaymentStatus.succeeded,
                Contribution.amount > 0,
            )
        )
        campaign_items.append(
            CampaignListItem(
                id=campaign.id,
                owner_id=campaign.owner_id,
                title=campaign.title,
                description=campaign.description,
                description_preview=campaign.description[:179],
                target_amount=campaign.target_amount,
                current_amount=campaign.current_amount,
                category=campaign.category,
                cover_image_url=campaign.cover_image_url,
                is_verified=campaign.is_verified,
                is_active=campaign.is_active,
                status=campaign.status.value,
                has_completion_report=campaign.has_completion_report,
                report_requested_at=campaign.report_requested_at,
                report_completed_at=campaign.report_completed_at,
                report_overdue=campaign.report_overdue,
                created_at=campaign.created_at,
                progress_percentage=min(100, int((campaign.current_amount / campaign.target_amount) * 100)) if campaign.target_amount else 0,
                owner=OwnerOut.model_validate(user),
                contributors_count=int(contributors_count or 0),
            )
        )

    author_reputation = await get_author_reputation_summary(session, user.id)

    return PublicUserProfileOut(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        city=user.city,
        created_at=user.created_at,
        supported_campaigns_count=supported_count,
        total_supported_campaigns=supported_count,
        total_donated_amount=str(total_donated_amount or Decimal("0")),
        created_campaigns_count=len(campaigns_created),
        completed_campaigns_count=completed_campaigns_count,
        achievements_count=len(achievements),
        achievements=achievements,
        campaigns_created=campaign_items,
        author_reputation=author_reputation,
        is_verified=user.is_verified,
    )
