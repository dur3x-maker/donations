from decimal import Decimal

from sqlalchemy import select

from app.models.platform_setting import PlatformSetting
from app.models.telegram_moderation_session import TelegramModerationSession
from app.core.config import settings
from app.services.telegram_moderation_service import (
    FEATURED_CONFIRMATION_STATE,
    FEATURED_USERNAME_STATE,
    handle_telegram_update,
)


class FakeTelegramNotifier:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.edited: list[dict] = []
        self.answered: list[dict] = []

    async def send_message(self, text, reply_markup=None, chat_id=None) -> None:
        self.sent.append({"text": text, "reply_markup": reply_markup, "chat_id": chat_id})

    async def edit_message_text(self, chat_id, message_id, text, reply_markup=None) -> None:
        self.edited.append(
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": reply_markup,
            }
        )

    async def answer_callback_query(self, callback_query_id, text=None) -> None:
        self.answered.append({"id": callback_query_id, "text": text})


async def test_telegram_featured_campaign_flow(db_session, user_factory, campaign_factory):
    owner = await user_factory(username="hakatoshka")
    owner.first_name = "Никита"
    owner.last_name = "Егоров"
    await db_session.commit()
    campaign = await campaign_factory(
        owner,
        title="Безопасная ванная для Ирины",
        current_amount=Decimal("353100"),
        target_amount=Decimal("730000"),
    )
    telegram = FakeTelegramNotifier()

    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    pending = await db_session.scalar(select(TelegramModerationSession))
    assert pending.state == FEATURED_USERNAME_STATE
    assert telegram.sent[-1]["text"] == "Введите username пользователя (без символа @)\n\nНапример:\n\nhakatoshka"

    await handle_telegram_update(db_session, _message_update("hakatoshka"), telegram)

    await db_session.refresh(pending)
    assert pending.state == FEATURED_CONFIRMATION_STATE
    assert pending.requested_username == "hakatoshka"
    assert telegram.sent[-1]["text"] == (
        "Никита Егоров\n"
        "@hakatoshka\n\n"
        "Безопасная ванная для Ирины\n\n"
        "353 100 ₽ из 730 000 ₽"
    )
    assert telegram.sent[-1]["reply_markup"]["inline_keyboard"][0][0]["text"] == "⭐ Сделать главным"

    await handle_telegram_update(db_session, _callback_update("promo:confirm", message_id=102), telegram)

    platform_settings = await db_session.get(PlatformSetting, 1)
    assert platform_settings.featured_campaign_id == campaign.id
    assert telegram.edited[-1]["text"] == "✅ Главная история обновлена."
    assert await db_session.scalar(select(TelegramModerationSession)) is None


async def test_telegram_featured_campaign_lookup_errors(db_session, user_factory):
    telegram = FakeTelegramNotifier()
    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    await handle_telegram_update(db_session, _message_update("missing"), telegram)
    assert telegram.sent[-1]["text"] == "❌ Пользователь не найден."

    await user_factory(username="without_campaign")
    await handle_telegram_update(db_session, _message_update("without_campaign"), telegram)
    assert telegram.sent[-1]["text"] == "❌ У пользователя сейчас нет активной истории."


async def test_telegram_admin_menu_contains_featured_control(db_session):
    telegram = FakeTelegramNotifier()

    await handle_telegram_update(db_session, _message_update("/start"), telegram)

    button = telegram.sent[-1]["reply_markup"]["inline_keyboard"][0][0]
    assert button == {"text": "⭐ Главное промо", "callback_data": "promo:start"}


async def test_telegram_featured_control_rejects_foreign_chat(db_session, monkeypatch):
    monkeypatch.setattr(settings, "telegram_chat_id", "-100500")
    telegram = FakeTelegramNotifier()
    update = _callback_update("promo:start")
    update["callback_query"]["message"]["chat"]["id"] = -999

    await handle_telegram_update(db_session, update, telegram)

    assert telegram.sent == []
    assert telegram.answered[-1]["text"] == "Недостаточно прав."


async def test_telegram_featured_control_fails_closed_without_production_chat_id(db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "telegram_chat_id", None)
    telegram = FakeTelegramNotifier()

    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    assert telegram.sent == []
    assert telegram.answered[-1]["text"] == "Недостаточно прав."


def _callback_update(data: str, message_id: int = 100) -> dict:
    return {
        "callback_query": {
            "id": f"callback-{message_id}",
            "data": data,
            "from": {"id": 42, "username": "admin"},
            "message": {"message_id": message_id, "chat": {"id": -100500}},
        }
    }


def _message_update(text: str) -> dict:
    return {
        "message": {
            "text": text,
            "from": {"id": 42, "username": "admin"},
            "chat": {"id": -100500},
        }
    }
