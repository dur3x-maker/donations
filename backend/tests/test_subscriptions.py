from sqlalchemy import select

from app.models.campaign_subscription import CampaignSubscription
from app.services.follow_up_service import subscribe_user_to_campaign
from tests.helpers import count_rows


async def test_repeated_subscription_creation_is_idempotent(
    db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    first, first_created = await subscribe_user_to_campaign(db_session, donor.id, campaign.id)
    second, second_created = await subscribe_user_to_campaign(db_session, donor.id, campaign.id)
    await db_session.commit()
    assert first.id == second.id
    assert first_created is True
    assert second_created is False
    assert await count_rows(db_session, CampaignSubscription) == 1


async def test_anonymous_user_is_not_subscribed(db_session, user_factory, campaign_factory):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    subscription, created = await subscribe_user_to_campaign(db_session, None, campaign.id)
    assert subscription is None
    assert created is False
    assert await count_rows(db_session, CampaignSubscription) == 0


async def test_manual_subscription_and_unsubscription(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)

    initial = await client.get(
        f"/api/v1/campaigns/{campaign.id}/subscription",
        headers=auth_headers(donor),
    )
    subscribed = await client.post(
        f"/api/v1/campaigns/{campaign.id}/subscription",
        headers=auth_headers(donor),
    )
    unsubscribed = await client.delete(
        f"/api/v1/campaigns/{campaign.id}/subscription",
        headers=auth_headers(donor),
    )

    assert initial.json()["is_subscribed"] is False
    assert subscribed.json()["is_subscribed"] is True
    assert unsubscribed.json()["is_subscribed"] is False
    assert await count_rows(db_session, CampaignSubscription) == 1


async def test_donation_reactivates_existing_subscription_without_duplicate(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=10000)
    await client.post(f"/api/v1/campaigns/{campaign.id}/subscription", headers=auth_headers(donor))
    await client.delete(f"/api/v1/campaigns/{campaign.id}/subscription", headers=auth_headers(donor))

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/donate",
        json={"amount": "100"},
        headers=auth_headers(donor),
    )

    assert response.status_code == 200
    assert response.json()["subscription_created"] is False
    assert await count_rows(db_session, CampaignSubscription) == 1
    subscription = await db_session.scalar(
        select(CampaignSubscription).where(CampaignSubscription.user_id == donor.id)
    )
    assert subscription.is_active is True
