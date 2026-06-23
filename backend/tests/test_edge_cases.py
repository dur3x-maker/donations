from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.campaign import CampaignStatus
from app.models.campaign_subscription import CampaignSubscription
from app.models.payment import Payment, PaymentStatus
from tests.helpers import campaign_payload


async def test_repeated_campaign_form_is_rejected_by_unfinished_rule(
    client, user_factory, campaign_factory, contribution_factory, auth_headers
):
    author = await user_factory()
    owner = await user_factory()
    unlock_campaign = await campaign_factory(owner, target_amount=Decimal("100000"))
    await contribution_factory(unlock_campaign, user=author, count=5)
    first = await client.post("/api/v1/campaigns", json=campaign_payload(), headers=auth_headers(author))
    second = await client.post("/api/v1/campaigns", json=campaign_payload(), headers=auth_headers(author))
    assert first.status_code == 201
    assert second.status_code == 409


async def test_subscription_database_constraint_blocks_duplicates(
    db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    db_session.add(CampaignSubscription(user_id=donor.id, campaign_id=campaign.id))
    await db_session.commit()
    db_session.add(CampaignSubscription(user_id=donor.id, campaign_id=campaign.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_one_payment_per_contribution_constraint(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    contribution = (await contribution_factory(campaign, user=donor))[0]
    db_session.add(
        Payment(
            contribution_id=contribution.id,
            provider="duplicate",
            amount=contribution.amount,
            currency="RUB",
            status=PaymentStatus.pending,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_donation_with_excess_precision_is_rejected(client, user_factory, campaign_factory):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/donate",
        json={"amount": "100.001"},
    )
    assert response.status_code == 422


async def test_update_photos_remove_blank_values(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    campaign = await campaign_factory(owner, status=CampaignStatus.active)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/updates",
        json={
            "title": "Valid update title",
            "content": "A sufficiently long update body.",
            "photos": [" ", "/valid.jpg", ""],
        },
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    assert len(response.json()["photos"]) == 1


async def test_photo_urls_over_database_limit_are_rejected(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/updates",
        json={
            "title": "Valid update title",
            "content": "A sufficiently long update body.",
            "photos": ["/" + "x" * 1024],
        },
        headers=auth_headers(owner),
    )
    assert response.status_code == 422
