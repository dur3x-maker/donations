from app.main import app
from app.api.v1.contact import get_admin_event_service


class FakeAdminEventService:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


async def test_contact_request_publishes_admin_event(client):
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service
    response = await client.post(
        "/api/v1/contact",
        json={
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "subject": "Сообщить об ошибке",
            "message": "На странице сбора не открывается список пожертвований.",
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert len(fake_service.events) == 1
    event = fake_service.events[0]
    assert event.actor is None
    assert ("Тема", "Сообщить об ошибке") in event.sections
    assert ("Email", "ivan@example.com") in event.sections


async def test_contact_request_adds_authenticated_actor(client, user_factory, auth_headers):
    user = await user_factory(username="ivan")
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service

    response = await client.post(
        "/api/v1/contact",
        json={
            "name": "Иван",
            "email": "ivan@example.com",
            "subject": "Общий вопрос",
            "message": "Подскажите, пожалуйста, как правильно оформить первый сбор.",
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert len(fake_service.events) == 1
    assert fake_service.events[0].actor.username == "ivan"
    assert str(user.id) == str(fake_service.events[0].actor.id)
    assert fake_service.events[0].actor.profile_url.endswith("/u/ivan")


async def test_contact_request_validates_payload(client):
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service

    response = await client.post(
        "/api/v1/contact",
        json={
            "name": "",
            "email": "bad-email",
            "subject": "Другое",
            "message": "слишком коротко",
        },
    )

    assert response.status_code == 422
    assert fake_service.events == []
