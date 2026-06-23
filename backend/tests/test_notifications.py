from decimal import Decimal

from sqlalchemy import select

from app.models.notification import Notification, NotificationType
from app.services.notification_service import create_notification
from tests.helpers import count_rows


async def test_goal_reached_notifications_are_not_duplicated(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("100"))
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/donate",
        json={"amount": "100"},
        headers=auth_headers(donor),
    )
    assert response.status_code == 200
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor.id,
        Notification.type == NotificationType.campaign_goal_reached,
    ) == 1
    donor_notification = await db_session.scalar(
        select(Notification).where(
            Notification.user_id == donor.id,
            Notification.type == NotificationType.campaign_goal_reached,
        )
    )
    assert donor_notification.action_url == f"/campaigns/{campaign.id}"
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == owner.id,
        Notification.type == NotificationType.campaign_funded,
    ) == 1


async def test_user_cannot_read_foreign_notification(
    client, db_session, user_factory, auth_headers
):
    owner = await user_factory()
    intruder = await user_factory()
    notification = Notification(
        user_id=owner.id,
        type=NotificationType.donation_received,
        title="Private",
        body="Private body",
    )
    db_session.add(notification)
    await db_session.commit()
    response = await client.post(
        f"/api/v1/notifications/{notification.id}/read",
        headers=auth_headers(intruder),
    )
    assert response.status_code == 404


async def test_notification_owner_can_mark_it_read(client, db_session, user_factory, auth_headers):
    owner = await user_factory()
    notification = Notification(
        user_id=owner.id,
        type=NotificationType.donation_received,
        title="Own",
        body="Own body",
    )
    db_session.add(notification)
    await db_session.commit()
    response = await client.post(
        f"/api/v1/notifications/{notification.id}/read",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


async def test_user_can_mark_visible_notifications_read_in_bulk(
    client, db_session, user_factory, auth_headers
):
    owner = await user_factory()
    notifications = [
        Notification(
            user_id=owner.id,
            type=NotificationType.donation_received,
            title=f"Notification {index}",
            body="Visible body",
        )
        for index in range(3)
    ]
    db_session.add_all(notifications)
    await db_session.commit()
    notification_ids = [item.id for item in notifications]

    response = await client.post(
        "/api/v1/me/notifications/read",
        json={"notification_ids": [str(item_id) for item_id in notification_ids[:2]]},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2
    db_session.expire_all()
    assert (await db_session.get(Notification, notification_ids[0])).is_read is True
    assert (await db_session.get(Notification, notification_ids[1])).is_read is True
    assert (await db_session.get(Notification, notification_ids[2])).is_read is False


async def test_bulk_read_ignores_foreign_notifications(
    client, db_session, user_factory, auth_headers
):
    owner = await user_factory()
    intruder = await user_factory()
    notification = Notification(
        user_id=owner.id,
        type=NotificationType.donation_received,
        title="Private",
        body="Private body",
    )
    db_session.add(notification)
    await db_session.commit()
    notification_id = notification.id

    response = await client.post(
        "/api/v1/me/notifications/read",
        json={"notification_ids": [str(notification_id)]},
        headers=auth_headers(intruder),
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 0
    db_session.expire_all()
    assert (await db_session.get(Notification, notification_id)).is_read is False


async def test_created_notification_is_published_to_user_realtime_topic(
    db_session, user_factory, monkeypatch
):
    user = await user_factory()
    published = []

    async def capture(topic, payload):
        published.append((topic, payload))

    monkeypatch.setattr("app.services.notification_service.realtime_manager.broadcast", capture)
    notification = await create_notification(
        db_session,
        user.id,
        NotificationType.achievement_unlocked,
        "Achievement",
        "Unlocked now",
        action_url="/profile#achievements",
    )

    assert len(published) == 1
    topic, event = published[0]
    assert topic == f"notifications:{user.id}"
    assert event.type == "notification_created"
    assert event.notification.id == notification.id
