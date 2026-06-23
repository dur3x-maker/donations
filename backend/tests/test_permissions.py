from decimal import Decimal

from app.models.campaign import CampaignStatus


async def test_foreign_campaign_delete_is_forbidden(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    intruder = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.delete(f"/api/v1/campaigns/{campaign.id}", headers=auth_headers(intruder))
    assert response.status_code == 403


async def test_non_moderator_cannot_access_moderation(client, user_factory, auth_headers):
    user = await user_factory()
    response = await client.get("/api/v1/moderation/reports", headers=auth_headers(user))
    assert response.status_code == 403


async def test_completion_report_is_public_but_mutation_is_owner_only(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/completion-report",
        json={"gratitude_text": "Thank you for making this result possible.", "photos": ["/a.jpg"]},
        headers=auth_headers(owner),
    )
    response = await client.get(f"/api/v1/campaigns/{campaign.id}/completion-report")
    assert response.status_code == 200

