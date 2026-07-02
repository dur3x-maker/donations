from decimal import Decimal

from app.db.base import utcnow
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_completion_report import CampaignCompletionPhoto, CampaignCompletionReport
from app.services.admin_event_service import AdminEventType, get_admin_event_service
from tests.helpers import campaign_payload, count_rows


class FakeAdminEventService:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


async def test_create_and_view_campaign(
    client, db_session, user_factory, campaign_factory, contribution_factory, auth_headers
):
    author = await user_factory()
    other_owner = await user_factory()
    unlock_campaign = await campaign_factory(other_owner, target_amount=Decimal("100000"))
    await contribution_factory(unlock_campaign, user=author, count=5)

    created = await client.post("/api/v1/campaigns", json=campaign_payload(), headers=auth_headers(author))
    assert created.status_code == 201
    campaign_id = created.json()["id"]

    viewed = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert viewed.status_code == 200
    assert viewed.json()["owner_id"] == str(author.id)
    assert await count_rows(db_session, Campaign, Campaign.owner_id == author.id) == 1


async def test_high_value_campaign_goes_to_pending_review_and_publishes_admin_event(
    client, db_session, user_factory, campaign_factory, contribution_factory, auth_headers
):
    from app.main import app

    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service
    author = await user_factory(username="ivan")
    other_owner = await user_factory()
    unlock_campaign = await campaign_factory(other_owner, target_amount=Decimal("100000"))
    await contribution_factory(unlock_campaign, user=author, count=5)

    response = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(target_amount="1250000"),
        headers=auth_headers(author),
    )

    assert response.status_code == 201
    assert response.json()["status"] == CampaignStatus.pending_review.value
    campaign = await db_session.get(Campaign, response.json()["id"])
    assert campaign.status == CampaignStatus.pending_review
    assert len(fake_service.events) == 1
    assert fake_service.events[0].type == AdminEventType.high_value_campaign
    assert ("Сумма", "1 250 000 ₽") in fake_service.events[0].sections


async def test_regular_campaign_creation_stays_active_without_admin_event(
    client, user_factory, campaign_factory, contribution_factory, auth_headers
):
    from app.main import app

    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service
    author = await user_factory()
    other_owner = await user_factory()
    unlock_campaign = await campaign_factory(other_owner, target_amount=Decimal("100000"))
    await contribution_factory(unlock_campaign, user=author, count=5)

    response = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(target_amount="999999"),
        headers=auth_headers(author),
    )

    assert response.status_code == 201
    assert response.json()["status"] == CampaignStatus.active.value
    assert fake_service.events == []


async def test_create_campaign_requires_five_foreign_contributions(client, user_factory, auth_headers):
    author = await user_factory()
    response = await client.post("/api/v1/campaigns", json=campaign_payload(), headers=auth_headers(author))
    assert response.status_code == 403


async def test_owner_can_edit_campaign(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        json={"title": "Updated campaign title"},
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated campaign title"


async def test_owner_cannot_edit_non_active_campaigns(client, user_factory, campaign_factory, auth_headers):
    for campaign_status in (
        CampaignStatus.pending_review,
        CampaignStatus.goal_reached,
        CampaignStatus.awaiting_report,
        CampaignStatus.completed,
    ):
        owner = await user_factory()
        campaign = await campaign_factory(
            owner,
            status=campaign_status,
            has_completion_report=campaign_status == CampaignStatus.completed,
        )
        response = await client.patch(
            f"/api/v1/campaigns/{campaign.id}",
            json={"title": "Blocked campaign edit"},
            headers=auth_headers(owner),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Редактировать можно только активные сборы."


async def test_put_campaign_update_is_not_allowed(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    campaign = await campaign_factory(owner)

    response = await client.put(
        f"/api/v1/campaigns/{campaign.id}",
        json={"title": "PUT should not update"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 405


async def test_foreign_user_cannot_edit_campaign(client, user_factory, campaign_factory, auth_headers):
    owner = await user_factory()
    intruder = await user_factory()
    campaign = await campaign_factory(owner)
    response = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        json={"title": "Stolen campaign"},
        headers=auth_headers(intruder),
    )
    assert response.status_code == 403


async def test_campaign_fields_reject_empty_and_oversized_values(client, user_factory, auth_headers):
    author = await user_factory()
    for payload in (
        campaign_payload(title=""),
        campaign_payload(description=""),
        campaign_payload(title="x" * 161),
        campaign_payload(description="x" * 5001),
    ):
        response = await client.post("/api/v1/campaigns", json=payload, headers=auth_headers(author))
        assert response.status_code == 422


async def test_campaign_field_boundaries_match_frontend_limits(client, user_factory, auth_headers):
    author = await user_factory()
    too_short_title = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(title="ab"),
        headers=auth_headers(author),
    )
    too_short_description = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(description="x" * 9),
        headers=auth_headers(author),
    )
    assert too_short_title.status_code == 422
    assert too_short_description.status_code == 422


async def test_campaign_rejects_whitespace_only_fields(client, user_factory, auth_headers):
    author = await user_factory()
    response = await client.post(
        "/api/v1/campaigns",
        json=campaign_payload(title="   ", description="          "),
        headers=auth_headers(author),
    )
    assert response.status_code == 422


async def test_target_cannot_be_lowered_to_collected_amount(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("1000"), current_amount=Decimal("500"))
    response = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        json={"target_amount": "500"},
        headers=auth_headers(owner),
    )
    assert response.status_code == 409


async def test_active_catalog_excludes_completed_campaigns(
    client, user_factory, campaign_factory
):
    owner = await user_factory()
    active = await campaign_factory(owner, title="Active story")
    await campaign_factory(
        owner,
        title="Completed story",
        status=CampaignStatus.completed,
        has_completion_report=True,
    )

    response = await client.get("/api/v1/campaigns")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(active.id)]


async def test_completed_catalog_includes_report_photos_and_search(
    client, db_session, user_factory, campaign_factory
):
    owner = await user_factory(username="marina")
    campaign = await campaign_factory(
        owner,
        title="Wheelchair delivered",
        target_amount=Decimal("120000"),
        current_amount=Decimal("123500"),
        status=CampaignStatus.completed,
        has_completion_report=True,
    )
    campaign.report_completed_at = utcnow()
    report = CampaignCompletionReport(
        campaign_id=campaign.id,
        author_id=owner.id,
        gratitude_text="Коля уже использует новую коляску каждый день.",
    )
    db_session.add(report)
    await db_session.flush()
    db_session.add(CampaignCompletionPhoto(report_id=report.id, image_url="/uploads/result.jpg"))
    await db_session.commit()

    response = await client.get("/api/v1/campaigns/completed?q=коляску")

    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["id"] == str(campaign.id)
    assert item["owner"]["username"] == "marina"
    assert item["completion_report_preview"].startswith("Коля")
    assert item["completion_photos"][0]["image_url"] == "/uploads/result.jpg"


async def test_withdrawal_info_is_available_only_for_owner_and_reached_lifecycle(
    client, user_factory, campaign_factory, auth_headers
):
    donor = await user_factory()

    for campaign_status, expected in (
        (CampaignStatus.active, False),
        (CampaignStatus.goal_reached, True),
        (CampaignStatus.awaiting_report, True),
        (CampaignStatus.completed, True),
    ):
        owner = await user_factory()
        campaign = await campaign_factory(
            owner,
            target_amount=Decimal("100"),
            current_amount=Decimal("100"),
            status=campaign_status,
            has_completion_report=campaign_status == CampaignStatus.completed,
        )
        response = await client.get(
            f"/api/v1/campaigns/{campaign.id}/withdrawal-info",
            headers=auth_headers(owner),
        )
        assert response.status_code == 200
        assert response.json() == {
            "campaign_id": str(campaign.id),
            "available": expected,
            "mode": "demo",
        }

        forbidden = await client.get(
            f"/api/v1/campaigns/{campaign.id}/withdrawal-info",
            headers=auth_headers(donor),
        )
        assert forbidden.status_code == 403


async def test_withdrawal_info_requires_reached_amount_and_authentication(
    client, user_factory, campaign_factory, auth_headers
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("99"),
        status=CampaignStatus.awaiting_report,
    )

    response = await client.get(
        f"/api/v1/campaigns/{campaign.id}/withdrawal-info",
        headers=auth_headers(owner),
    )
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert (
        await client.get(f"/api/v1/campaigns/{campaign.id}/withdrawal-info")
    ).status_code == 401
