from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.business_rules import UNFINISHED_CAMPAIGN_MESSAGE
from app.models.campaign import Campaign, CampaignStatus
from app.models.activity import ActivityType
from app.models.campaign_completion_report import CampaignCompletionReport
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignDetail, CampaignListItem, CampaignUpdate, CompletedCampaignListItem
from app.schemas.common import OwnerOut
from app.services.activity_service import create_activity
from app.services.admin_event_service import AdminEventService, build_high_value_campaign_event
from app.services.suspicious_flag_service import maybe_flag_many_campaigns
from app.services.user_service import can_create_campaign, has_unfinished_campaign


HIGH_VALUE_CAMPAIGN_THRESHOLD = Decimal("1000000")


def _preview(text: str, limit: int = 180) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}..."


def _owner_out(owner: User | None) -> OwnerOut | None:
    if owner is None:
        return None
    return OwnerOut.model_validate(owner)


def _progress_percentage(campaign: Campaign) -> int:
    if campaign.target_amount <= 0:
        return 0
    return min(100, int((Decimal(campaign.current_amount) / Decimal(campaign.target_amount)) * 100))


def _contributors_count_expr():
    participant_key = func.coalesce(
        cast(Contribution.user_id, String),
        Contribution.anonymous_token,
        cast(Contribution.id, String),
    )
    return func.count(func.distinct(participant_key)).filter(
        Contribution.status == ContributionStatus.confirmed,
        Payment.status == PaymentStatus.succeeded,
        Contribution.amount > 0,
    )


def _sort_clause(sort: str):
    if sort == "oldest":
        return asc(Campaign.created_at)
    if sort == "most_funded":
        return desc(Campaign.current_amount)
    if sort == "least_funded":
        return asc(Campaign.current_amount)
    return desc(Campaign.created_at)


async def get_campaigns(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 12,
    sort: str = "newest",
    query: str | None = None,
) -> list[CampaignListItem]:
    contributors_count = _contributors_count_expr()
    statement = (
        select(Campaign, contributors_count.label("contributors_count"))
        .join(User, User.id == Campaign.owner_id)
        .outerjoin(Contribution, Contribution.campaign_id == Campaign.id)
        .outerjoin(Payment, Payment.contribution_id == Contribution.id)
        .options(selectinload(Campaign.owner))
        .where(
            Campaign.is_active.is_(True),
            Campaign.status.in_(
                (
                    CampaignStatus.active,
                    CampaignStatus.goal_reached,
                    CampaignStatus.awaiting_report,
                )
            ),
        )
        .group_by(Campaign.id)
        .order_by(_sort_clause(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Campaign.title.ilike(pattern),
                Campaign.description.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    rows = await session.execute(statement)

    return [
        CampaignListItem(
            id=campaign.id,
            owner_id=campaign.owner_id,
            title=campaign.title,
            description=campaign.description,
            description_preview=_preview(campaign.description),
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
            progress_percentage=_progress_percentage(campaign),
            owner=_owner_out(campaign.owner),
            contributors_count=int(count or 0),
        )
        for campaign, count in rows
    ]


async def get_completed_campaigns(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 12,
    query: str | None = None,
) -> list[CompletedCampaignListItem]:
    contributors_count = _contributors_count_expr()
    statement = (
        select(Campaign, contributors_count.label("contributors_count"))
        .join(User, User.id == Campaign.owner_id)
        .outerjoin(CampaignCompletionReport, CampaignCompletionReport.campaign_id == Campaign.id)
        .outerjoin(Contribution, Contribution.campaign_id == Campaign.id)
        .outerjoin(Payment, Payment.contribution_id == Contribution.id)
        .options(
            selectinload(Campaign.owner),
            selectinload(Campaign.completion_report).selectinload(CampaignCompletionReport.photos),
        )
        .where(Campaign.status == CampaignStatus.completed)
        .group_by(Campaign.id)
        .order_by(desc(Campaign.report_completed_at), desc(Campaign.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Campaign.title.ilike(pattern),
                Campaign.description.ilike(pattern),
                User.username.ilike(pattern),
                CampaignCompletionReport.gratitude_text.ilike(pattern),
            )
        )
    rows = await session.execute(statement)

    return [
        CompletedCampaignListItem(
            id=campaign.id,
            owner_id=campaign.owner_id,
            title=campaign.title,
            description=campaign.description,
            description_preview=_preview(campaign.description),
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
            progress_percentage=_progress_percentage(campaign),
            owner=_owner_out(campaign.owner),
            contributors_count=int(count or 0),
            completion_report_preview=(
                _preview(campaign.completion_report.gratitude_text)
                if campaign.completion_report
                else None
            ),
            completion_photos=(
                campaign.completion_report.photos
                if campaign.completion_report
                else []
            ),
        )
        for campaign, count in rows
    ]


async def get_campaign_detail(session: AsyncSession, campaign_id: UUID, include_hidden: bool = False) -> CampaignDetail:
    campaign = await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(Campaign.id == campaign_id)
    )
    if campaign is None or (not include_hidden and (not campaign.is_active or campaign.status == CampaignStatus.archived)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сбор не найден")

    contributors_count = await get_contributors_count(session, campaign_id)
    return CampaignDetail(
        id=campaign.id,
        owner_id=campaign.owner_id,
        title=campaign.title,
        description=campaign.description,
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
        progress_percentage=_progress_percentage(campaign),
        owner=_owner_out(campaign.owner),
        contributors_count=contributors_count,
    )


async def get_campaign_or_404(session: AsyncSession, campaign_id: UUID, include_inactive: bool = False) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None or (not include_inactive and (not campaign.is_active or campaign.status == CampaignStatus.archived)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сбор не найден")
    return campaign


async def get_contributors_count(session: AsyncSession, campaign_id: UUID) -> int:
    count = await session.scalar(
        select(_contributors_count_expr())
        .select_from(Contribution)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .where(
            Contribution.campaign_id == campaign_id,
            Contribution.amount > 0,
        )
    )
    return int(count or 0)


async def campaign_to_list_item(session: AsyncSession, campaign: Campaign) -> CampaignListItem:
    return CampaignListItem(
        id=campaign.id,
        owner_id=campaign.owner_id,
        title=campaign.title,
        description=campaign.description,
        description_preview=_preview(campaign.description),
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
        progress_percentage=_progress_percentage(campaign),
        owner=_owner_out(campaign.owner),
        contributors_count=await get_contributors_count(session, campaign.id),
    )


async def create_campaign(
    session: AsyncSession,
    owner: User,
    payload: CampaignCreate,
    admin_events: AdminEventService | None = None,
) -> Campaign:
    await session.scalar(select(User.id).where(User.id == owner.id).with_for_update())
    if not await can_create_campaign(session, owner.id):
        if await has_unfinished_campaign(session, owner.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=UNFINISHED_CAMPAIGN_MESSAGE,
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нужно минимум 5 подтвержденных вкладов в чужие сборы.",
        )

    is_high_value = payload.target_amount >= HIGH_VALUE_CAMPAIGN_THRESHOLD
    campaign = Campaign(
        owner_id=owner.id,
        title=payload.title,
        description=payload.description,
        target_amount=payload.target_amount,
        current_amount=Decimal("0"),
        category=payload.category,
        cover_image_url=payload.cover_image_url,
        is_verified=False,
        is_active=True,
        status=CampaignStatus.pending_review if is_high_value else CampaignStatus.active,
    )
    try:
        session.add(campaign)
        await session.flush()
        if campaign.status == CampaignStatus.active:
            await create_activity(session, ActivityType.campaign_created, actor_user_id=owner.id, campaign_id=campaign.id)
        await maybe_flag_many_campaigns(session, owner.id)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=UNFINISHED_CAMPAIGN_MESSAGE,
        )
    await session.refresh(campaign)
    if is_high_value and admin_events is not None:
        await admin_events.publish(build_high_value_campaign_event(campaign, owner))
    return campaign


async def update_campaign(session: AsyncSession, campaign_id: UUID, owner: User, payload: CampaignUpdate) -> Campaign:
    campaign = await get_campaign_or_404(session, campaign_id)
    if campaign.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только автор может изменить сбор")
    if campaign.status != CampaignStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Редактировать можно только активные сборы.",
        )
    if payload.target_amount is not None and payload.target_amount <= campaign.current_amount:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Цель сбора должна быть больше уже собранной суммы",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    await session.commit()
    await session.refresh(campaign)
    return campaign


async def archive_campaign(session: AsyncSession, campaign_id: UUID, owner: User) -> None:
    campaign = await get_campaign_or_404(session, campaign_id)
    if campaign.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только автор может удалить сбор")

    campaign.status = CampaignStatus.archived
    campaign.is_active = False
    await session.commit()


async def set_campaign_active(session: AsyncSession, campaign_id: UUID, is_active: bool) -> Campaign:
    campaign = await get_campaign_or_404(session, campaign_id, include_inactive=True)
    campaign.is_active = is_active
    if not is_active:
        campaign.status = CampaignStatus.archived
    elif campaign.status == CampaignStatus.archived:
        campaign.status = CampaignStatus.active
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def recalculate_campaign_aggregates(session: AsyncSession, campaign_id: UUID) -> Campaign:
    campaign = await get_campaign_or_404(session, campaign_id, include_inactive=True)
    total_amount, _contributors_count = (
        await session.execute(
            select(
                func.coalesce(func.sum(Contribution.amount), 0),
                _contributors_count_expr(),
            )
            .select_from(Contribution)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .where(
                Contribution.campaign_id == campaign.id,
                Contribution.status == ContributionStatus.confirmed,
                Payment.status == PaymentStatus.succeeded,
                Contribution.amount > 0,
            )
        )
    ).one()

    campaign.current_amount = Decimal(total_amount or 0)
    if campaign.status != CampaignStatus.archived:
        campaign.is_active = True
        campaign.status = CampaignStatus.awaiting_report if campaign.current_amount >= campaign.target_amount else CampaignStatus.active
    await session.commit()
    await session.refresh(campaign)
    return campaign
