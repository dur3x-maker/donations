from datetime import timedelta
from decimal import Decimal

from app.db.base import utcnow
from app.models.campaign import CampaignStatus
from app.models.notification import Notification, NotificationType
from app.services.report_reminder_service import process_report_reminders
from tests.helpers import count_rows


async def test_report_reminders_at_30_60_and_90_days(
    db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    now = utcnow()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    campaign.report_requested_at = now - timedelta(days=30)
    await db_session.commit()

    assert await process_report_reminders(db_session, now) == 1
    campaign.report_requested_at = now - timedelta(days=60)
    await db_session.commit()
    assert await process_report_reminders(db_session, now) == 1
    campaign.report_requested_at = now - timedelta(days=90)
    await db_session.commit()
    assert await process_report_reminders(db_session, now) == 1
    await db_session.refresh(campaign)

    assert campaign.report_overdue is True
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == owner.id,
        Notification.type == NotificationType.campaign_report_reminder,
    ) == 3
    assert await process_report_reminders(db_session, now) == 0


async def test_publishing_report_clears_overdue_and_restores_reputation(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    campaign.report_overdue = True
    await db_session.commit()

    before = await client.get(f"/api/v1/users/{owner.id}/reputation")
    assert before.json()["campaigns_without_reports"] == 1

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "The result is ready for everyone to see.", "photos": ["/uploads/story-photos/a.jpg"]},
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    after = await client.get(f"/api/v1/users/{owner.id}/reputation")
    assert after.json()["campaigns_without_reports"] == 0
