from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.campaign import Campaign, CampaignStatus
from app.models.notification import NotificationType
from app.services.notification_service import create_notification


async def process_report_reminders(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or utcnow()
    campaigns = list(
        await session.scalars(
            select(Campaign)
            .where(
                Campaign.status == CampaignStatus.awaiting_report,
                Campaign.report_requested_at.is_not(None),
            )
            .with_for_update(skip_locked=True)
        )
    )
    created = 0
    for campaign in campaigns:
        requested_at = _as_utc(campaign.report_requested_at)
        age = now - requested_at
        if age >= timedelta(days=90) and campaign.report_reminder_90_sent_at is None:
            campaign.report_overdue = True
            campaign.report_reminder_90_sent_at = now
            await _notify(session, campaign, "Отчёт по истории до сих пор не опубликован.")
            created += 1
        elif age >= timedelta(days=60) and campaign.report_reminder_60_sent_at is None:
            campaign.report_reminder_60_sent_at = now
            await _notify(session, campaign, "Участники будут рады увидеть результат вашей истории.")
            created += 1
        elif age >= timedelta(days=30) and campaign.report_reminder_30_sent_at is None:
            campaign.report_reminder_30_sent_at = now
            await _notify(session, campaign, "Участники будут рады увидеть результат вашей истории.")
            created += 1
    await session.commit()
    return created


async def _notify(session: AsyncSession, campaign: Campaign, body: str) -> None:
    await create_notification(
        session,
        campaign.owner_id,
        NotificationType.campaign_report_reminder,
        "Итоговый отчёт ждут",
        body,
        campaign_id=campaign.id,
        action_url=f"/campaigns/{campaign.id}",
    )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
