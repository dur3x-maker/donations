from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.business_rules import MIN_DONATION_AMOUNT, UNFINISHED_CAMPAIGN_STATUSES
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.activity import ActivityType
from app.models.campaign import Campaign
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.campaign import CampaignListItem
from app.schemas.common import OwnerOut
from app.schemas.contribution import RecentDonationOut
from app.schemas.user import OwnerCampaignStatsOut, OwnerDashboardOut, ProfileAchievementOut, ProfileContributionOut, ProfileSummaryOut, ProfileTimelineItemOut, TokenResponse, UserLoginIn, UserRegisterIn
from app.services.activity_service import create_once_activity
from app.services.level_service import current_level_for
from app.services.notification_service import create_notification

REQUIRED_CONFIRMED_DONATIONS = 5
REQUIRED_CONFIRMED_CONTRIBUTIONS = REQUIRED_CONFIRMED_DONATIONS


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


def build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=user,
    )


async def register_user(session: AsyncSession, payload: UserRegisterIn) -> TokenResponse:
    email = payload.email.lower()
    username = payload.username.lower()

    existing = await session.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Имя пользователя уже занято")

    existing_email = await get_user_by_email(session, email)
    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже используется")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
    )
    try:
        session.add(user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email или имя пользователя уже используется",
        )
    await session.refresh(user)
    return build_token_response(user)


async def login_user(session: AsyncSession, payload: UserLoginIn) -> TokenResponse:
    user = await get_user_by_email(session, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Профиль неактивен")
    return build_token_response(user)


async def link_anonymous_contributions(
    session: AsyncSession,
    user: User,
    anonymous_token: str,
    commit: bool = True,
) -> int:
    result = await session.execute(
        update(Contribution)
        .where(
            Contribution.anonymous_token == anonymous_token,
            Contribution.user_id.is_(None),
        )
        .values(user_id=user.id)
    )
    linked_count = int(result.rowcount or 0)
    if linked_count:
        confirmed_count = await get_confirmed_donation_count(session, user.id)
        if confirmed_count >= REQUIRED_CONFIRMED_DONATIONS:
            created = await create_once_activity(
                session,
                ActivityType.unlock_achieved,
                actor_user_id=user.id,
                metadata_json={"confirmed_donations": confirmed_count},
            )
            if created is not None:
                await create_notification(
                    session,
                    user.id,
                    NotificationType.unlock_achieved,
                    "Создание сбора доступно",
                    "Ваши привязанные вклады помогли открыть собственный сбор.",
                    action_url="/campaigns/new",
                )

    if commit:
        await session.commit()
    return linked_count


async def get_confirmed_donation_count(session: AsyncSession, user_id: UUID) -> int:
    count = await session.scalar(
        select(func.count(Contribution.id))
        .join(Campaign, Campaign.id == Contribution.campaign_id)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .where(
            Contribution.user_id == user_id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount >= MIN_DONATION_AMOUNT,
            Campaign.owner_id != user_id,
        )
    )
    return int(count or 0)


async def confirmed_foreign_contributions_count(session: AsyncSession, user_id: UUID) -> int:
    return await get_confirmed_donation_count(session, user_id)


async def has_unfinished_campaign(session: AsyncSession, user_id: UUID) -> bool:
    existing_campaign_id = await session.scalar(
        select(Campaign.id)
        .where(
            Campaign.owner_id == user_id,
            Campaign.is_active.is_(True),
            Campaign.status.in_(UNFINISHED_CAMPAIGN_STATUSES),
        )
        .limit(1)
    )
    return existing_campaign_id is not None


async def can_create_campaign(session: AsyncSession, user_id: UUID) -> bool:
    return (
        (await get_confirmed_donation_count(session, user_id)) >= REQUIRED_CONFIRMED_DONATIONS
        and not await has_unfinished_campaign(session, user_id)
    )


async def get_profile_summary(session: AsyncSession, user_id: UUID) -> ProfileSummaryOut:
    now = datetime.now(timezone.utc)
    thirty_days_ago = now.replace(microsecond=0) - timedelta(days=30)
    valid_contributions = (
        Contribution.user_id == user_id,
        Contribution.status == ContributionStatus.confirmed,
        Payment.status == PaymentStatus.succeeded,
        Contribution.amount >= MIN_DONATION_AMOUNT,
        Campaign.owner_id != user_id,
    )
    contributions_count, supported_campaigns_count, total_amount, last_contribution_at = (
        await session.execute(
            select(
                func.count(Contribution.id),
                func.count(func.distinct(Contribution.campaign_id)),
                func.coalesce(func.sum(Contribution.amount), 0),
                func.max(Contribution.created_at),
            )
            .select_from(Contribution)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(*valid_contributions)
        )
    ).one()
    recent_rows = (
        await session.execute(
            select(Contribution, Campaign.title)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(*valid_contributions)
            .order_by(desc(Contribution.created_at))
            .limit(5)
        )
    ).all()
    contribution_dates = list(
        await session.scalars(
            select(Contribution.created_at)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(*valid_contributions)
            .order_by(Contribution.created_at)
        )
    )
    supported_campaigns_current_amount = await session.scalar(
        select(func.coalesce(func.sum(Campaign.current_amount), 0)).where(
            Campaign.id.in_(
                select(Contribution.campaign_id)
                .join(Campaign, Campaign.id == Contribution.campaign_id)
                .join(Payment, Payment.contribution_id == Contribution.id)
                .where(
                    Contribution.user_id == user_id,
                    Contribution.status == ContributionStatus.confirmed,
                    Payment.status == PaymentStatus.succeeded,
                    Contribution.amount >= MIN_DONATION_AMOUNT,
                    Campaign.owner_id != user_id,
                )
                .distinct()
            )
        )
    )
    contributions_last_30_days, supported_campaigns_last_30_days = (
        await session.execute(
            select(
                func.count(Contribution.id),
                func.count(func.distinct(Contribution.campaign_id)),
            )
            .select_from(Contribution)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(*valid_contributions, Contribution.created_at >= thirty_days_ago)
        )
    ).one()
    participant_counts = (
        select(Contribution.user_id.label("user_id"), func.count(Contribution.id).label("contributions_count"))
        .join(Campaign, Campaign.id == Contribution.campaign_id)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .where(
            Contribution.user_id.is_not(None),
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount >= MIN_DONATION_AMOUNT,
            Campaign.owner_id != Contribution.user_id,
        )
        .group_by(Contribution.user_id)
        .subquery()
    )
    confirmed_count = int(contributions_count or 0)
    active_contributors_count = int(await session.scalar(select(func.count()).select_from(participant_counts)) or 0)
    higher_ranked_count = int(
        await session.scalar(select(func.count()).select_from(participant_counts).where(participant_counts.c.contributions_count > confirmed_count)) or 0
    )
    community_rank = higher_ranked_count + 1 if confirmed_count else None
    percentile = ceil((community_rank / active_contributors_count) * 100) if community_rank and active_contributors_count else None
    community_top_percent = next((bracket for bracket in (5, 10, 25, 50, 100) if percentile is not None and percentile <= bracket), None)
    timeline = _profile_timeline(contribution_dates)
    achievements = _profile_achievements(contribution_dates)
    return ProfileSummaryOut(
        confirmed_contributions_count=confirmed_count,
        required_contributions_count=REQUIRED_CONFIRMED_DONATIONS,
        can_create_campaign=await can_create_campaign(session, user_id),
        has_unfinished_campaign=await has_unfinished_campaign(session, user_id),
        supported_campaigns_count=int(supported_campaigns_count or 0),
        total_donated_amount=str(total_amount or 0),
        last_contribution_at=last_contribution_at,
        recent_contributions=[
            ProfileContributionOut(
                id=contribution.id,
                campaign_id=contribution.campaign_id,
                campaign_title=campaign_title,
                amount=str(contribution.amount),
                created_at=contribution.created_at,
            )
            for contribution, campaign_title in recent_rows
        ],
        supported_campaigns_current_amount=str(supported_campaigns_current_amount or 0),
        contributions_last_30_days=int(contributions_last_30_days or 0),
        supported_campaigns_last_30_days=int(supported_campaigns_last_30_days or 0),
        achievements=achievements,
        achievements_last_30_days=sum(
            1
            for achievement in achievements
            if _as_utc(achievement.achieved_at) >= thirty_days_ago
        ),
        user_level=_profile_user_level(confirmed_count),
        community_top_percent=community_top_percent,
        community_rank=community_rank,
        active_contributors_count=active_contributors_count,
        timeline=timeline,
    )


def _profile_timeline(contribution_dates: list[datetime]) -> list[ProfileTimelineItemOut]:
    if not contribution_dates:
        return []
    milestones = [
        ("first_contribution", 1, "Первый подтвержденный вклад"),
        ("campaign_unlock", REQUIRED_CONFIRMED_DONATIONS, "Получено право создавать сборы"),
        ("ten_contributions", 10, "10 подтвержденных вкладов"),
        ("twenty_five_contributions", 25, "25 подтвержденных вкладов"),
        ("forty_contributions", 40, "40 подтвержденных вкладов"),
    ]
    return [
        ProfileTimelineItemOut(id=milestone_id, title=title, created_at=contribution_dates[threshold - 1])
        for milestone_id, threshold, title in milestones
        if len(contribution_dates) >= threshold
    ]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _profile_achievements(contribution_dates: list[datetime]) -> list[ProfileAchievementOut]:
    rules = [
        ("first", 1, "Первый вклад", "Начало вашей истории поддержки"),
        ("helper", 5, "5 подтвержденных вкладов", "Открыта возможность создать сбор"),
        ("ten", 10, "10 подтвержденных вкладов", "Вы регулярно помогаете историям"),
        ("twenty_five", 25, "25 подтвержденных вкладов", "Весомый вклад в сообщество"),
        ("forty", 40, "40 подтвержденных вкладов", "Поддержка стала доброй привычкой"),
    ]
    achievements = [
        ProfileAchievementOut(
            id=achievement_id,
            title=title,
            copy=copy,
            achieved_at=contribution_dates[threshold - 1],
        )
        for achievement_id, threshold, title, copy in rules
        if len(contribution_dates) >= threshold
    ]
    if len(contribution_dates) >= REQUIRED_CONFIRMED_DONATIONS:
        achievements.append(
            ProfileAchievementOut(
                id="campaign_unlock",
                title="Право создать сбор",
                copy="Ваш вклад открыл возможность рассказать свою историю",
                achieved_at=contribution_dates[REQUIRED_CONFIRMED_DONATIONS - 1],
            )
        )
    return achievements


def _profile_user_level(confirmed_count: int) -> str:
    level = current_level_for(confirmed_count)
    return level.title if level else "Путь помощи еще не начался"


def _campaign_out(campaign: Campaign, contributors_count: int) -> CampaignListItem:
    progress = 0 if campaign.target_amount <= 0 else min(100, int((Decimal(campaign.current_amount) / Decimal(campaign.target_amount)) * 100))
    description_preview = campaign.description if len(campaign.description) <= 180 else f"{campaign.description[:179].rstrip()}..."
    return CampaignListItem(
        id=campaign.id,
        owner_id=campaign.owner_id,
        title=campaign.title,
        description=campaign.description,
        description_preview=description_preview,
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
        progress_percentage=progress,
        owner=OwnerOut.model_validate(campaign.owner),
        contributors_count=contributors_count,
    )


async def get_owner_dashboard(session: AsyncSession, user_id: UUID) -> OwnerDashboardOut:
    campaigns = list(
        await session.scalars(
            select(Campaign)
            .options(selectinload(Campaign.owner))
            .where(Campaign.owner_id == user_id)
            .order_by(desc(Campaign.created_at))
        )
    )
    if not campaigns:
        return OwnerDashboardOut(campaign=None, campaigns_count=0, stats=None, recent_donations=[])

    campaign = next((item for item in campaigns if item.status in UNFINISHED_CAMPAIGN_STATUSES), campaigns[0])
    valid_contributions = (
        Contribution.campaign_id == campaign.id,
        Contribution.status == ContributionStatus.confirmed,
        Payment.status == PaymentStatus.succeeded,
        Contribution.amount > 0,
    )
    participant_key = func.coalesce(cast(Contribution.user_id, String), Contribution.anonymous_token, cast(Contribution.id, String))
    contributions_count, unique_count, average_amount, today_amount = (
        await session.execute(
            select(
                func.count(Contribution.id),
                func.count(func.distinct(participant_key)),
                func.coalesce(func.avg(Contribution.amount), 0),
                func.coalesce(func.sum(Contribution.amount).filter(Contribution.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)), 0),
            )
            .select_from(Contribution)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(*valid_contributions)
        )
    ).one()

    recent_contributions = list(
        await session.scalars(
            select(Contribution)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .options(selectinload(Contribution.user))
            .where(*valid_contributions)
            .order_by(desc(Contribution.created_at))
            .limit(5)
        )
    )
    recent_donations = [
        RecentDonationOut(
            id=contribution.id,
            amount=contribution.amount,
            username=contribution.user.username if contribution.user else "Анонимно",
            created_at=contribution.created_at,
        )
        for contribution in recent_contributions
    ]
    return OwnerDashboardOut(
        campaign=_campaign_out(campaign, int(contributions_count or 0)),
        campaigns_count=len(campaigns),
        stats=OwnerCampaignStatsOut(
            contributions_count=int(contributions_count or 0),
            unique_contributors_count=int(unique_count or 0),
            average_contribution=str(average_amount or 0),
            today_amount=str(today_amount or 0),
        ),
        recent_donations=recent_donations,
    )
