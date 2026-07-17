import pytest

from app.models.campaign import CampaignStatus
from app.models.platform_setting import PlatformSetting
from app.services.featured_campaign_service import (
    FeaturedCampaignActiveCampaignNotFoundError,
    FeaturedCampaignUserNotFoundError,
    get_featured_campaign,
    set_featured_campaign_by_username,
)


async def test_set_featured_campaign_by_username(db_session, user_factory, campaign_factory):
    owner = await user_factory(username="nikita")
    campaign = await campaign_factory(owner, title="Безопасная ванная для Ирины")

    selected = await set_featured_campaign_by_username(db_session, "NIKITA")

    platform_settings = await db_session.get(PlatformSetting, 1)
    assert selected.id == campaign.id
    assert platform_settings.featured_campaign_id == campaign.id


async def test_set_featured_campaign_reports_clear_lookup_errors(db_session, user_factory):
    with pytest.raises(FeaturedCampaignUserNotFoundError, match="Пользователь не найден"):
        await set_featured_campaign_by_username(db_session, "missing")

    await user_factory(username="without_campaign")
    with pytest.raises(
        FeaturedCampaignActiveCampaignNotFoundError,
        match="нет активной истории",
    ):
        await set_featured_campaign_by_username(db_session, "without_campaign")


async def test_featured_campaign_falls_back_after_selected_campaign_is_archived(
    db_session,
    user_factory,
    campaign_factory,
):
    selected_owner = await user_factory(username="selected")
    selected = await campaign_factory(selected_owner)
    await set_featured_campaign_by_username(db_session, selected_owner.username)

    fallback_owner = await user_factory(username="fallback")
    fallback = await campaign_factory(fallback_owner)
    selected.status = CampaignStatus.archived
    selected.is_active = False
    await db_session.commit()

    resolved = await get_featured_campaign(db_session)

    platform_settings = await db_session.get(PlatformSetting, 1)
    await db_session.refresh(platform_settings)
    assert resolved.id == fallback.id
    assert platform_settings.featured_campaign_id == fallback.id


async def test_featured_campaign_endpoint_returns_selected_campaign(
    client,
    db_session,
    user_factory,
    campaign_factory,
):
    selected_owner = await user_factory(username="selected")
    selected = await campaign_factory(selected_owner)
    other_owner = await user_factory(username="newer")
    await campaign_factory(other_owner)
    await set_featured_campaign_by_username(db_session, selected_owner.username)

    response = await client.get("/api/v1/platform/featured-campaign")
    catalog_response = await client.get("/api/v1/campaigns")

    assert response.status_code == 200
    assert response.json()["id"] == str(selected.id)
    assert str(selected.id) in {item["id"] for item in catalog_response.json()}


async def test_only_active_campaign_can_be_featured(db_session, user_factory, campaign_factory):
    owner = await user_factory(username="completed_owner")
    await campaign_factory(
        owner,
        status=CampaignStatus.completed,
        has_completion_report=True,
    )

    with pytest.raises(FeaturedCampaignActiveCampaignNotFoundError):
        await set_featured_campaign_by_username(db_session, owner.username)
