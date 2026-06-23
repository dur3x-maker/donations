from decimal import Decimal

from app.models.campaign import CampaignStatus


async def test_author_reputation_updates_after_completed_report(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("150"),
        status=CampaignStatus.awaiting_report,
    )
    before = await client.get(f"/api/v1/users/{owner.id}/reputation")
    assert before.status_code == 200
    assert before.json()["campaigns_with_reports"] == 0

    await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "Thank you for making this result possible.", "photos": ["/a.jpg"]},
        headers=auth_headers(owner),
    )
    after = await client.get(f"/api/v1/users/{owner.id}/reputation")
    assert after.status_code == 200
    assert after.json()["campaigns_completed"] == 1
    assert after.json()["campaigns_with_reports"] == 1
    assert Decimal(after.json()["total_raised_amount"]) == Decimal("150")

