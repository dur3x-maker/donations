from decimal import Decimal
import logging

import pytest
from sqlalchemy import select

from app.models.platform_setting import PlatformSetting
from app.models.telegram_moderation_session import TelegramModerationSession
from app.core.config import settings
from app.services import telegram_moderation_service
from app.services.featured_campaign_service import FeaturedCampaignMultipleActiveCampaignsError
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


async def test_telegram_featured_campaign_flow_persists_state_across_requests(
    db_session,
    session_factory,
    user_factory,
    campaign_factory,
):
    owner = await user_factory(username="anna_belova")
    owner.first_name = "Анна"
    owner.last_name = "Белова"
    await db_session.commit()
    campaign = await campaign_factory(
        owner,
        title="Слуховой аппарат для работы и общения",
        current_amount=Decimal("92400"),
        target_amount=Decimal("165000"),
    )
    telegram = FakeTelegramNotifier()

    async with session_factory() as callback_session:
        await handle_telegram_update(callback_session, _callback_update("promo:start"), telegram)

    async with session_factory() as state_session:
        pending = await state_session.scalar(select(TelegramModerationSession))
        assert pending.state == FEATURED_USERNAME_STATE
    assert telegram.sent[-1]["text"] == "Введите username пользователя (без символа @)\n\nНапример:\n\nhakatoshka"

    anonymous_admin_message = _message_update("anna_belova", from_id=1087968824)
    anonymous_admin_message["message"]["sender_chat"] = {"id": -100500, "type": "supergroup"}
    async with session_factory() as message_session:
        await handle_telegram_update(message_session, anonymous_admin_message, telegram)

    async with session_factory() as confirmation_state_session:
        pending = await confirmation_state_session.scalar(select(TelegramModerationSession))
        assert pending.state == FEATURED_CONFIRMATION_STATE
        assert pending.requested_username == "anna_belova"
    assert telegram.sent[-1]["text"] == (
        "Анна Белова\n"
        "@anna_belova\n\n"
        "Слуховой аппарат для работы и общения\n\n"
        "92 400 ₽ из 165 000 ₽"
    )
    assert telegram.sent[-1]["reply_markup"]["inline_keyboard"][0][0]["text"] == "⭐ Сделать главным"

    async with session_factory() as confirmation_session:
        await handle_telegram_update(
            confirmation_session,
            _callback_update("promo:confirm", message_id=102),
            telegram,
        )

    async with session_factory() as result_session:
        platform_settings = await result_session.get(PlatformSetting, 1)
        assert platform_settings.featured_campaign_id == campaign.id
        assert await result_session.scalar(select(TelegramModerationSession)) is None
    assert telegram.edited[-1]["text"] == "✅ Сбор успешно назначен главным."


async def test_telegram_featured_campaign_lookup_errors(db_session, user_factory):
    telegram = FakeTelegramNotifier()
    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    await handle_telegram_update(db_session, _message_update("missing"), telegram)
    assert telegram.sent[-1]["text"] == "❌ Пользователь не найден."

    await user_factory(username="without_campaign")
    await handle_telegram_update(db_session, _message_update("without_campaign"), telegram)
    assert telegram.sent[-1]["text"] == "❌ У пользователя сейчас нет активной истории."


async def test_telegram_featured_campaign_reports_multiple_campaigns(
    db_session,
    monkeypatch,
):
    async def raise_multiple(*args, **kwargs):
        raise FeaturedCampaignMultipleActiveCampaignsError

    monkeypatch.setattr(telegram_moderation_service, "find_active_campaign_by_username", raise_multiple)
    telegram = FakeTelegramNotifier()
    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    await handle_telegram_update(db_session, _message_update("anna_belova"), telegram)

    assert telegram.sent[-1]["text"] == "❌ У пользователя найдено несколько активных сборов."


async def test_telegram_featured_campaign_reports_already_selected(
    db_session,
    user_factory,
    campaign_factory,
):
    owner = await user_factory(username="anna_belova")
    campaign = await campaign_factory(owner)
    db_session.add(PlatformSetting(id=1, featured_campaign_id=campaign.id))
    await db_session.commit()
    telegram = FakeTelegramNotifier()
    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    await handle_telegram_update(db_session, _message_update("@ANNA_BELOVA"), telegram)

    assert telegram.sent[-1]["text"] == "ℹ️ Этот сбор уже является главным."
    assert await db_session.scalar(select(TelegramModerationSession)) is None


async def test_telegram_featured_campaign_logs_and_reports_internal_error(
    db_session,
    monkeypatch,
    caplog,
):
    async def fail(*args, **kwargs):
        raise RuntimeError("database failure")

    monkeypatch.setattr(telegram_moderation_service, "find_active_campaign_by_username", fail)
    telegram = FakeTelegramNotifier()
    await handle_telegram_update(db_session, _callback_update("promo:start"), telegram)

    with caplog.at_level(logging.ERROR, logger="telegram_moderation"):
        with pytest.raises(RuntimeError, match="database failure"):
            await handle_telegram_update(db_session, _message_update("anna_belova"), telegram)

    assert telegram.sent[-1]["text"] == "❌ Внутренняя ошибка. Попробуйте ещё раз или проверьте логи."
    record = next(
        record
        for record in caplog.records
        if record.getMessage().startswith("telegram_featured_username_failed")
    )
    assert record.exc_info is not None


async def test_telegram_admin_message_without_state_is_not_silent(db_session):
    telegram = FakeTelegramNotifier()

    await handle_telegram_update(db_session, _message_update("anna_belova"), telegram)

    assert telegram.sent[-1]["text"] == (
        "⚠️ Активный сценарий не найден. Нажмите «⭐ Главное промо» и попробуйте снова."
    )


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


def _message_update(text: str, *, from_id: int = 42) -> dict:
    return {
        "message": {
            "text": text,
            "from": {"id": from_id, "username": "admin"},
            "chat": {"id": -100500},
        }
    }
