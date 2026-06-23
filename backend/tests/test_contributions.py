from decimal import Decimal

from sqlalchemy import select

from app.models.campaign_subscription import CampaignSubscription
from app.models.contribution import Contribution
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment
from app.services.payment_service import confirm_payment
from tests.helpers import count_rows


async def test_successful_and_repeated_registered_donations(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("10000"))

    for _ in range(3):
        response = await client.post(
            f"/api/v1/campaigns/{campaign.id}/donate",
            json={"amount": "100"},
            headers=auth_headers(donor),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "succeeded"
        assert response.json()["subscription_created"] is (_ == 0)

    assert await count_rows(db_session, Contribution, Contribution.user_id == donor.id) == 3
    assert await count_rows(db_session, Payment) == 3
    assert await count_rows(db_session, CampaignSubscription, CampaignSubscription.user_id == donor.id) == 1
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor.id,
        Notification.type == NotificationType.campaign_subscription_created,
    ) == 1
    detail = await client.get(f"/api/v1/campaigns/{campaign.id}")
    assert detail.json()["contributors_count"] == 1


async def test_anonymous_donation_does_not_subscribe(client, db_session, user_factory, campaign_factory):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.post(f"/api/v1/campaigns/{campaign.id}/donate", json={"amount": "100"})
    assert response.status_code == 200
    assert response.json()["anonymous_token"]
    assert await count_rows(db_session, CampaignSubscription) == 0


async def test_anonymous_token_can_be_reused_for_multiple_donations(
    client, db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    token = "stable-anonymous-token"
    for _ in range(2):
        response = await client.post(
            f"/api/v1/campaigns/{campaign.id}/donate",
            json={"amount": "100", "anonymous_token": token},
        )
        assert response.status_code == 200
        assert response.json()["anonymous_token"] == token
    assert await count_rows(db_session, Contribution, Contribution.anonymous_token == token) == 2


async def test_minimum_amount_and_closed_campaign_are_rejected(client, user_factory, campaign_factory):
    owner = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("100"))
    assert (
        await client.post(f"/api/v1/campaigns/{campaign.id}/donate", json={"amount": "99"})
    ).status_code == 422
    assert (
        await client.post(f"/api/v1/campaigns/{campaign.id}/donate", json={"amount": "100"})
    ).status_code == 200
    assert (
        await client.post(f"/api/v1/campaigns/{campaign.id}/donate", json={"amount": "100"})
    ).status_code == 409


async def test_repeated_payment_confirmation_is_idempotent(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    contribution = (await contribution_factory(campaign, user=donor, update_campaign_amount=False))[0]
    payment = await db_session.scalar(select(Payment).where(Payment.contribution_id == contribution.id))
    original_amount = campaign.current_amount

    assert await confirm_payment(db_session, payment) is False
    assert campaign.current_amount == original_amount


async def test_link_anonymous_contributions_is_repeat_safe(
    client, db_session, user_factory, campaign_factory, contribution_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    await contribution_factory(campaign, count=2, anonymous_token="claim-me")

    first = await client.post(
        "/api/v1/me/link-anonymous-contributions",
        json={"anonymous_token": "claim-me"},
        headers=auth_headers(donor),
    )
    second = await client.post(
        "/api/v1/me/link-anonymous-contributions",
        json={"anonymous_token": "claim-me"},
        headers=auth_headers(donor),
    )
    assert first.json()["linked_count"] == 2
    assert second.json()["linked_count"] == 0


async def test_recent_donations_are_paginated_newest_first(
    client, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("100000"))
    created = []
    for index in range(15):
        created.extend(
            await contribution_factory(
                campaign,
                user=donor,
                amount=Decimal(100 + index),
                update_campaign_amount=False,
            )
        )

    first = await client.get(f"/api/v1/campaigns/{campaign.id}/recent-donations?limit=3")
    second = await client.get(f"/api/v1/campaigns/{campaign.id}/recent-donations?offset=3&limit=10")

    assert first.status_code == 200
    assert len(first.json()["items"]) == 3
    assert first.json()["has_more"] is True
    assert len(second.json()["items"]) == 10
    assert second.json()["has_more"] is True
    assert {item["id"] for item in first.json()["items"]}.isdisjoint(
        {item["id"] for item in second.json()["items"]}
    )
    amounts = [Decimal(item["amount"]) for item in first.json()["items"] + second.json()["items"]]
    assert amounts == sorted(amounts, reverse=True)
