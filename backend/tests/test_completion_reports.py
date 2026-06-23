from decimal import Decimal

from sqlalchemy import select

from app.models.campaign import CampaignStatus
from app.models.campaign_subscription import CampaignSubscription
from app.models.notification import Notification, NotificationType
from tests.helpers import count_rows


async def test_completion_report_requires_photo(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "Thank you for all your meaningful support.", "photos": []},
        headers=auth_headers(owner),
    )
    assert response.status_code == 422


async def test_completion_report_changes_status_and_notifies_subscriber(
    client, db_session, user_factory, campaign_factory, contribution_factory, auth_headers
):
    owner = await user_factory()
    supporter = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    await contribution_factory(campaign, user=supporter, update_campaign_amount=False)
    db_session.add(CampaignSubscription(user_id=supporter.id, campaign_id=campaign.id))
    await db_session.commit()

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={
            "gratitude_text": "Thank you for helping us complete this story.",
            "photos": ["/uploads/result.jpg"],
        },
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    assert response.json()["supporters_count"] == 1

    campaign_id = campaign.id
    supporter_id = supporter.id
    db_session.expire_all()
    refreshed = await db_session.get(type(campaign), campaign_id)
    assert refreshed.status == CampaignStatus.completed
    assert refreshed.has_completion_report is True
    assert refreshed.report_completed_at is not None
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == supporter_id,
        Notification.type == NotificationType.campaign_report_published,
    ) == 1
    notification = await db_session.scalar(
        select(Notification)
        .where(
            Notification.user_id == supporter_id,
            Notification.type == NotificationType.campaign_report_published,
        )
    )
    assert notification.action_url == f"/campaigns/{campaign_id}"

    active_catalog = await client.get("/api/v1/campaigns")
    completed_catalog = await client.get("/api/v1/campaigns/completed")
    assert str(campaign_id) not in {item["id"] for item in active_catalog.json()}
    assert str(campaign_id) in {item["id"] for item in completed_catalog.json()}


async def test_distinct_anonymous_supporters_are_not_collapsed(
    client, user_factory, campaign_factory, contribution_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("200"),
        current_amount=Decimal("200"),
        status=CampaignStatus.awaiting_report,
    )
    await contribution_factory(campaign, anonymous_token="anonymous-a", update_campaign_amount=False)
    await contribution_factory(campaign, anonymous_token="anonymous-b", update_campaign_amount=False)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "Thank you to every supporter of this story.", "photos": ["/a.jpg"]},
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    assert response.json()["supporters_count"] == 2


async def test_completion_report_cannot_be_published_twice(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    payload = {"gratitude_text": "Thank you for helping complete this story.", "photos": ["/a.jpg"]}
    first = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json=payload,
        headers=auth_headers(owner),
    )
    second = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json=payload,
        headers=auth_headers(owner),
    )
    assert first.status_code == 201
    assert second.status_code == 409


async def test_foreign_user_cannot_publish_completion_report(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    intruder = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "This report must not be accepted.", "photos": ["/a.jpg"]},
        headers=auth_headers(intruder),
    )
    assert response.status_code == 403


async def test_report_before_goal_is_rejected(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "This report is too early to publish.", "photos": ["/a.jpg"]},
        headers=auth_headers(owner),
    )
    assert response.status_code == 409
