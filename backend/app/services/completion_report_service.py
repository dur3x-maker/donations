from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import utcnow
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_completion_report import CampaignCompletionPhoto, CampaignCompletionReport
from app.models.campaign_subscription import CampaignSubscription
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.realtime.manager import CATALOG_TOPIC, campaign_topic, dashboard_topic, realtime_manager
from app.schemas.campaign import CampaignCompletionReportCreate, CampaignCompletionReportOut, CampaignCompletionSupporterOut
from app.schemas.contribution import CampaignLifecycleChangedEvent
from app.services.achievement_service import evaluate_user_achievements
from app.services.follow_up_service import notify_campaign_subscribers


async def create_completion_report(
    session: AsyncSession,
    campaign_id: UUID,
    author: User,
    payload: CampaignCompletionReportCreate,
) -> CampaignCompletionReportOut:
    campaign = await session.scalar(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .with_for_update()
    )
    if campaign is None or not campaign.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сбор не найден")
    if campaign.owner_id != author.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только автор может опубликовать итоговый отчет")
    if campaign.has_completion_report:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Итоговый отчет уже опубликован")
    if campaign.status != CampaignStatus.awaiting_report:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Итоговый отчет доступен после достижения цели")

    report = CampaignCompletionReport(
        campaign_id=campaign.id,
        author_id=author.id,
        gratitude_text=payload.gratitude_text,
    )
    session.add(report)
    await session.flush()
    session.add_all([CampaignCompletionPhoto(report_id=report.id, image_url=image_url) for image_url in payload.photos])

    completed_at = utcnow()
    campaign.has_completion_report = True
    campaign.status = CampaignStatus.completed
    campaign.report_completed_at = completed_at
    campaign.report_overdue = False

    await notify_campaign_subscribers(
        session,
        campaign.id,
        NotificationType.campaign_report_published,
        "История завершена",
        "История, которую вы поддержали, опубликовала итоговый результат.",
        action_url=f"/campaigns/{campaign.id}",
        exclude_user_id=author.id,
    )

    subscriber_ids = list(
        await session.scalars(
            select(CampaignSubscription.user_id).where(
                CampaignSubscription.campaign_id == campaign.id,
                CampaignSubscription.user_id != author.id,
                CampaignSubscription.is_active.is_(True),
            )
        )
    )
    for user_id in subscriber_ids:
        await evaluate_user_achievements(session, user_id)

    await session.commit()
    lifecycle_event = CampaignLifecycleChangedEvent(
        campaign_id=campaign.id,
        status=campaign.status.value,
    )
    await realtime_manager.broadcast(campaign_topic(campaign.id), lifecycle_event)
    await realtime_manager.broadcast(CATALOG_TOPIC, lifecycle_event)
    await realtime_manager.broadcast(dashboard_topic(campaign.owner_id), lifecycle_event)
    return await get_completion_report(session, campaign.id)


async def get_completion_report(session: AsyncSession, campaign_id: UUID) -> CampaignCompletionReportOut:
    report = await session.scalar(
        select(CampaignCompletionReport)
        .options(selectinload(CampaignCompletionReport.photos), selectinload(CampaignCompletionReport.campaign))
        .where(CampaignCompletionReport.campaign_id == campaign_id)
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Итоговый отчет не найден")

    supporters = await _get_supporters(session, campaign_id)
    return CampaignCompletionReportOut(
        id=report.id,
        campaign_id=report.campaign_id,
        author_id=report.author_id,
        gratitude_text=report.gratitude_text,
        created_at=report.created_at,
        raised_amount=report.campaign.current_amount,
        supporters_count=len(supporters),
        photos=report.photos,
        supporters=supporters,
    )


async def _get_supporters(session: AsyncSession, campaign_id: UUID) -> list[CampaignCompletionSupporterOut]:
    participant_key = func.coalesce(
        cast(Contribution.user_id, String),
        Contribution.anonymous_token,
        cast(Contribution.id, String),
    )
    rows = await session.execute(
        select(participant_key.label("participant_key"), User.username, func.min(Contribution.created_at).label("first_at"))
        .select_from(Contribution)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .outerjoin(User, User.id == Contribution.user_id)
        .where(
            Contribution.campaign_id == campaign_id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount > 0,
        )
        .group_by(participant_key, User.username)
        .order_by("first_at")
    )
    supporters = []
    for _, username, _ in rows:
        is_anonymous = not username
        supporters.append(CampaignCompletionSupporterOut(name=username if not is_anonymous else "Анонимный участник", is_anonymous=is_anonymous))
    return supporters
