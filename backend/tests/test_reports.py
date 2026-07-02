from app.main import app
from app.models.report import Report
from app.services.admin_event_service import AdminEventType, get_admin_event_service
from tests.helpers import count_rows


class FakeAdminEventService:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


async def test_campaign_report_is_created_and_publishes_admin_event(
    client, db_session, user_factory, campaign_factory, auth_headers
):
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service
    owner = await user_factory(username="owner")
    reporter = await user_factory(username="dur3x")
    campaign = await campaign_factory(owner, title="Help Artem")

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/report",
        json={"reason": "Подозрение на мошенничество", "details": "Проверить документы."},
        headers=auth_headers(reporter),
    )

    assert response.status_code == 201
    assert await count_rows(db_session, Report, Report.campaign_id == campaign.id) == 1
    assert len(fake_service.events) == 1
    event = fake_service.events[0]
    assert event.type == AdminEventType.user_report
    assert ("Сбор", "Help Artem") in event.sections
    assert ("Telegram", "@dur3x") in event.sections
    assert ("ID пользователя", str(reporter.id)) in event.sections
    assert ("Причина", "Подозрение на мошенничество") in event.sections


async def test_anonymous_campaign_report_omits_reporter_fields(
    client, user_factory, campaign_factory
):
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service
    owner = await user_factory(username="owner")
    campaign = await campaign_factory(owner)

    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/report",
        json={"reason": "Suspicious", "details": "No public documents."},
    )

    assert response.status_code == 201
    labels = [title for title, _ in fake_service.events[0].sections]
    assert "Отправил" not in labels
    assert "ID пользователя" not in labels
