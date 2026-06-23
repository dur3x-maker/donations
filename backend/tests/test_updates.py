from sqlalchemy import select

from app.models.campaign_subscription import CampaignSubscription
from app.models.notification import Notification, NotificationType
from tests.helpers import count_rows


async def test_update_with_photos_notifies_subscriber_once_per_event(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    subscriber = await user_factory()
    campaign = await campaign_factory(owner)
    db_session.add(CampaignSubscription(user_id=subscriber.id, campaign_id=campaign.id))
    await db_session.commit()

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/updates",
        json={
            "title": "Treatment progress",
            "content": "A detailed update about the treatment progress.",
            "photos": ["/uploads/one.jpg", "/uploads/two.jpg"],
        },
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    assert len(response.json()["photos"]) == 2
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == subscriber.id,
        Notification.type == NotificationType.campaign_author_update_created,
    ) == 1
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == subscriber.id,
        Notification.type == NotificationType.campaign_photos_added,
    ) == 1
    notifications = list(
        await db_session.scalars(
            select(Notification).where(Notification.user_id == subscriber.id)
        )
    )
    assert {item.action_url for item in notifications} == {f"/campaigns/{campaign.id}"}


async def test_foreign_user_cannot_publish_update(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    intruder = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/updates",
        json={"title": "Foreign update", "content": "This must never be published.", "photos": []},
        headers=auth_headers(intruder),
    )
    assert response.status_code == 403
