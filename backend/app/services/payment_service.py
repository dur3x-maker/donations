import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.business_rules import CAMPAIGN_CLOSED_FOR_DONATIONS_MESSAGE, can_accept_donation
from app.core.logging import log_event
from app.db.base import utcnow
from app.models.activity import ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import NotificationType
from app.models.payment import Payment, PaymentStatus
from app.services.activity_service import create_activity, create_once_activity
from app.services.achievement_service import evaluate_user_achievements
from app.services.follow_up_service import notify_campaign_subscribers, subscribe_user_to_campaign
from app.services.notification_service import create_notification
from app.services.user_service import REQUIRED_CONFIRMED_DONATIONS, get_confirmed_donation_count

logger = logging.getLogger("payments")


async def create_payment(
    session: AsyncSession,
    contribution: Contribution,
    provider: str = "mock",
    currency: str = "RUB",
    metadata_json: dict | None = None,
) -> Payment:
    payment = Payment(
        contribution_id=contribution.id,
        provider=provider,
        amount=contribution.amount,
        currency=currency,
        status=PaymentStatus.pending,
        metadata_json=metadata_json,
    )
    session.add(payment)
    await session.flush()
    return payment


async def confirm_payment(session: AsyncSession, payment: Payment) -> bool:
    payment = await _load_payment(session, payment.id)
    if payment.status == PaymentStatus.succeeded:
        return False

    contribution = payment.contribution
    campaign = await session.scalar(
        select(Campaign)
        .where(Campaign.id == contribution.campaign_id)
        .with_for_update()
    )
    if campaign is None:
        return False
    if not can_accept_donation(campaign):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CAMPAIGN_CLOSED_FOR_DONATIONS_MESSAGE)
    was_completed = campaign.current_amount < campaign.target_amount

    payment.status = PaymentStatus.succeeded
    payment.confirmed_at = utcnow()

    if contribution.status != ContributionStatus.confirmed:
        contribution.status = ContributionStatus.confirmed
        campaign.current_amount = Decimal(campaign.current_amount) + Decimal(contribution.amount)
        _, subscription_created = await subscribe_user_to_campaign(session, contribution.user_id, campaign.id)
        await evaluate_user_achievements(session, contribution.user_id)
        await create_activity(
            session,
            ActivityType.donation_made,
            actor_user_id=contribution.user_id,
            campaign_id=campaign.id,
            metadata_json={"amount": str(contribution.amount)},
        )

        if contribution.user_id and campaign.owner_id != contribution.user_id:
            if subscription_created:
                await create_notification(
                    session,
                    contribution.user_id,
                    NotificationType.campaign_subscription_created,
                    "Вы следите за историей",
                    "Вы автоматически подписались на обновления этой истории.",
                    campaign_id=campaign.id,
                    action_url=f"/campaigns/{campaign.id}",
                )
            confirmed_count = await get_confirmed_donation_count(session, contribution.user_id)
            if confirmed_count >= REQUIRED_CONFIRMED_DONATIONS:
                created = await create_once_activity(
                    session,
                    ActivityType.unlock_achieved,
                    actor_user_id=contribution.user_id,
                    metadata_json={"confirmed_donations": confirmed_count},
                )
                if created is not None:
                    await create_notification(
                        session,
                        contribution.user_id,
                        NotificationType.unlock_achieved,
                        "Создание сбора доступно",
                        "Вы поддержали достаточно сборов, чтобы открыть свой.",
                        action_url="/campaigns/new",
                    )

        if campaign.owner_id != contribution.user_id:
            await create_notification(
                session,
                campaign.owner_id,
                NotificationType.donation_received,
                "Новая поддержка",
                f"Кто-то поддержал сбор «{campaign.title}».",
                campaign_id=campaign.id,
                action_url=f"/campaigns/{campaign.id}",
            )

        if was_completed and campaign.current_amount >= campaign.target_amount:
            campaign.status = CampaignStatus.awaiting_report
            if campaign.report_requested_at is None:
                campaign.report_requested_at = utcnow()
            await create_once_activity(session, ActivityType.campaign_completed, campaign_id=campaign.id)
            await create_notification(
                session,
                campaign.owner_id,
                NotificationType.campaign_funded,
                "Сбор закрыт",
                f"Сбор «{campaign.title}» достиг цели.",
                campaign_id=campaign.id,
                action_url=f"/campaigns/{campaign.id}",
            )
            if campaign.goal_reached_notified_at is None:
                campaign.goal_reached_notified_at = utcnow()
                await notify_campaign_subscribers(
                    session,
                    campaign.id,
                    NotificationType.campaign_goal_reached,
                    "Сбор достиг цели",
                    "История, которую вы поддержали, собрала нужную сумму.",
                    action_url=f"/campaigns/{campaign.id}",
                )

    await session.flush()
    return True


async def fail_payment(session: AsyncSession, payment: Payment) -> bool:
    payment = await _load_payment(session, payment.id)
    if payment.status == PaymentStatus.succeeded:
        return False

    payment.status = PaymentStatus.failed
    if payment.contribution.status == ContributionStatus.pending:
        payment.contribution.status = ContributionStatus.rejected

    await session.flush()
    log_event(logger, logging.WARNING, "failed_payment", payment_id=payment.id, contribution_id=payment.contribution_id)
    return True


async def _load_payment(session: AsyncSession, payment_id) -> Payment:
    payment = await session.scalar(
        select(Payment)
        .options(selectinload(Payment.contribution))
        .where(Payment.id == payment_id)
        .with_for_update()
    )
    if payment is None:
        raise ValueError("Платеж не найден")
    return payment
