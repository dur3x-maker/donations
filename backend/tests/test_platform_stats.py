from decimal import Decimal

from app.models.campaign import CampaignStatus
from app.models.contribution import Contribution, ContributionStatus
from app.models.payment import Payment, PaymentStatus


async def test_platform_stats_empty_database(client):
    response = await client.get("/api/v1/platform/stats")
    assert response.status_code == 200
    assert response.json() == {
        "users_count": 0,
        "campaigns_total": 0,
        "campaigns_active": 0,
        "campaigns_completed": 0,
        "successful_reports": 0,
        "confirmed_contributions": 0,
        "total_donated_amount": "0",
    }


async def test_platform_stats_uses_real_aggregates(
    client,
    db_session,
    user_factory,
    campaign_factory,
    contribution_factory,
):
    owner = await user_factory()
    donor = await user_factory()
    active_campaign = await campaign_factory(owner, status=CampaignStatus.active, target_amount=Decimal("1000"))
    completed_campaign = await campaign_factory(
        owner,
        status=CampaignStatus.completed,
        target_amount=Decimal("2000"),
        has_completion_report=True,
    )
    await contribution_factory(active_campaign, user=donor, count=2, amount=Decimal("150"))
    await contribution_factory(completed_campaign, user=donor, count=1, amount=Decimal("500"))

    pending_contribution = Contribution(
        campaign_id=active_campaign.id,
        user_id=donor.id,
        amount=Decimal("999"),
        status=ContributionStatus.pending,
    )
    db_session.add(pending_contribution)
    await db_session.flush()
    db_session.add(
        Payment(
            contribution_id=pending_contribution.id,
            provider="test",
            amount=Decimal("999"),
            currency="RUB",
            status=PaymentStatus.pending,
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/platform/stats")
    assert response.status_code == 200
    assert response.json() == {
        "users_count": 2,
        "campaigns_total": 2,
        "campaigns_active": 1,
        "campaigns_completed": 1,
        "successful_reports": 1,
        "confirmed_contributions": 3,
        "total_donated_amount": "800.00",
    }
