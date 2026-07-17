from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import select

from app.main import app
from app.api.v1.contact import get_admin_event_service
from app.core.config import settings
from app.models.contact_request import ContactRequest
from app.services.admin_event_service import _format_telegram_message, admin_actor_from_user


class FakeAdminEventService:
    def __init__(self) -> None:
        self.events = []

    async def publish(self, event) -> None:
        self.events.append(event)


async def test_contact_request_publishes_admin_event_and_is_stored(client, db_session):
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
    stored = await db_session.scalar(select(ContactRequest))
    assert stored is not None
    assert stored.name == "Иван Иванов"
    assert stored.telegram is None
    assert stored.subject == "Сообщить об ошибке"


async def test_contact_request_adds_authenticated_actor_and_telegram(client, db_session, user_factory, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "public_web_url", "https://test.digitalgardens.online")
    user = await user_factory(username="ivan")
    fake_service = FakeAdminEventService()
    app.dependency_overrides[get_admin_event_service] = lambda: fake_service

    response = await client.post(
        "/api/v1/contact",
        json={
            "name": "Иван",
            "email": "ivan@example.com",
            "telegram": "https://t.me/ivan_support",
            "subject": "Общий вопрос",
            "message": "Подскажите, пожалуйста, как правильно оформить первый сбор.",
        },
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert len(fake_service.events) == 1
    assert fake_service.events[0].actor.username == "ivan"
    assert str(user.id) == str(fake_service.events[0].actor.id)
    event = fake_service.events[0]
    assert event.actor.profile_url == "https://test.digitalgardens.online/u/ivan"
    assert ("Telegram", "@ivan_support") in event.sections
    assert "@ivan_support" in _format_telegram_message(
        replace(event, created_at=datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc))
    )

    stored = await db_session.scalar(select(ContactRequest))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.telegram == "@ivan_support"


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


async def test_contact_request_rejects_invalid_telegram(client):
    response = await client.post(
        "/api/v1/contact",
        json={
            "name": "Иван",
            "email": "ivan@example.com",
            "telegram": "ivan_support",
            "subject": "Другое",
            "message": "Достаточно длинное тестовое сообщение для проверки.",
        },
    )

    assert response.status_code == 422


def test_admin_profile_url_uses_public_web_url(monkeypatch):
    from uuid import uuid4

    monkeypatch.setattr(settings, "public_web_url", "https://test.digitalgardens.online")

    actor = admin_actor_from_user(uuid4(), "exact_username")

    assert actor.profile_url == "https://test.digitalgardens.online/u/exact_username"
