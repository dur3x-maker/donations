from datetime import datetime
import logging
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import log_event
from app.integrations.telegram_notifier import TelegramNotifier
from app.models.activity import ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.notification import NotificationType
from app.models.telegram_moderation_session import TelegramModerationSession
from app.services.activity_service import create_activity
from app.services.campaign_service import recalculate_campaign_aggregates
from app.services.featured_campaign_service import (
    FeaturedCampaignActiveCampaignNotFoundError,
    FeaturedCampaignAlreadySelectedError,
    FeaturedCampaignMultipleActiveCampaignsError,
    FeaturedCampaignUserNotFoundError,
    find_active_campaign_by_username,
    is_featured_campaign,
    set_featured_campaign_by_username,
)
from app.services.notification_service import create_notification

ACTION_PREFIX = "hvc"
ADMIN_ACTION_PREFIX = "admin"
PROMO_ACTION_PREFIX = "promo"
REVISION_REASON_STATE = "revision_reason"
FEATURED_USERNAME_STATE = "featured_username"
FEATURED_CONFIRMATION_STATE = "featured_confirmation"
FEATURED_STATES = (FEATURED_USERNAME_STATE, FEATURED_CONFIRMATION_STATE)
logger = logging.getLogger("telegram_moderation")


def _trace(step: str, **fields) -> None:
    log_event(logger, logging.INFO, "telegram_promo_trace", step=step, **fields)


async def handle_telegram_update(
    session: AsyncSession,
    update: dict,
    telegram: TelegramNotifier,
) -> None:
    callback_query = update.get("callback_query")
    message = update.get("message")
    payload = callback_query or message or {}
    payload_message = (callback_query or {}).get("message") or message or {}
    _trace(
        "update_dispatch",
        update_id=update.get("update_id"),
        update_type="callback_query" if callback_query else "message" if message else "unsupported",
        chat_id=str((payload_message.get("chat") or {}).get("id") or ""),
        from_id=str((payload.get("from") or {}).get("id") or ""),
        sender_chat_id=str((payload_message.get("sender_chat") or {}).get("id") or ""),
        callback_data=str((callback_query or {}).get("data") or ""),
    )
    if callback_query:
        await _handle_callback_query(session, callback_query, telegram)
        return

    if message:
        await _handle_message(session, message, telegram)
        return

    _trace("update_ignored", update_id=update.get("update_id"), reason="unsupported_update_type")


async def _handle_callback_query(
    session: AsyncSession,
    callback_query: dict,
    telegram: TelegramNotifier,
) -> None:
    callback_id = str(callback_query.get("id", ""))
    data = str(callback_query.get("data") or "")
    message = callback_query.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    message_id = int(message.get("message_id") or 0)
    admin = callback_query.get("from") or {}
    admin_id = str(admin.get("id") or "")
    admin_name = _admin_name(admin)
    _trace(
        "callback_received",
        callback_data=data,
        callback_id=callback_id,
        chat_id=chat_id,
        from_id=admin_id,
        message_id=message_id,
    )

    admin_chat_allowed = _is_admin_chat(chat_id)
    _trace(
        "admin_chat_check",
        source="callback_query",
        chat_id=chat_id,
        configured_chat_id=str(settings.telegram_chat_id or ""),
        allowed=admin_chat_allowed,
    )
    if not admin_chat_allowed:
        _trace("callback_rejected", reason="not_admin_chat", chat_id=chat_id, from_id=admin_id)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Недостаточно прав.")
        return

    if data.startswith(f"{PROMO_ACTION_PREFIX}:"):
        _trace("promo_callback_enter", callback_data=data, chat_id=chat_id, from_id=admin_id)
        try:
            await _handle_featured_callback(
                session,
                data,
                callback_id,
                chat_id,
                message_id,
                admin_id,
                admin_name,
                telegram,
            )
        except Exception:
            await session.rollback()
            logger.exception(
                "telegram_featured_callback_failed action=%s chat_id=%s admin_id=%s",
                data,
                chat_id,
                admin_id,
            )
            await telegram.send_message(
                "❌ Внутренняя ошибка. Попробуйте ещё раз или проверьте логи.",
                chat_id=chat_id,
            )
            if callback_id:
                await telegram.answer_callback_query(callback_id, "Внутренняя ошибка.")
            raise
        return

    parsed = _parse_callback_data(data)
    if parsed is None:
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Неизвестное действие.")
        return

    action, campaign_id = parsed

    if action == "archive":
        await _ask_archive_confirmation(chat_id, message_id, campaign_id, telegram)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Подтвердите скрытие сбора.")
        return

    if action == "confirm_archive":
        ok = await _archive_campaign(session, campaign_id, chat_id, message_id, admin_name, telegram)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Сбор скрыт." if ok else "Сбор не найден.")
        return

    if action == "recalc":
        ok = await _recalculate_campaign(session, campaign_id, chat_id, message_id, admin_name, telegram)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Пересчет выполнен." if ok else "Сбор не найден.")
        return

    if action == "revision":
        await _start_revision(session, campaign_id, chat_id, message_id, admin_id, admin_name, telegram)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Введите причину возврата.")
        return

    status = CampaignStatus.active if action == "approve" else CampaignStatus.rejected
    title = "Ваш сбор успешно прошёл модерацию." if action == "approve" else "К сожалению, сбор не прошёл модерацию."
    body = title
    final_label = "✅ Одобрено" if action == "approve" else "❌ Отклонено"
    ok = await _finalize_moderation(
        session,
        campaign_id,
        status,
        title,
        body,
        chat_id,
        message_id,
        final_label,
        admin_name,
        telegram,
        create_public_activity=action == "approve",
    )
    if callback_id:
        await telegram.answer_callback_query(callback_id, "Готово." if ok else "Сбор уже обработан.")


async def _handle_message(session: AsyncSession, message: dict, telegram: TelegramNotifier) -> None:
    text = (message.get("text") or "").strip()
    admin = message.get("from") or {}
    admin_id = str(admin.get("id") or "")
    chat_id = str((message.get("chat") or {}).get("id", ""))
    sender_chat_id = str((message.get("sender_chat") or {}).get("id") or "")
    _trace(
        "message_received",
        chat_id=chat_id,
        from_id=admin_id,
        sender_chat_id=sender_chat_id,
        has_text=bool(text),
        text_length=len(text),
    )
    if not text:
        _trace("message_ignored", reason="empty_text", chat_id=chat_id, from_id=admin_id)
        return
    admin_chat_allowed = _is_admin_chat(chat_id)
    _trace(
        "admin_chat_check",
        source="message",
        chat_id=chat_id,
        configured_chat_id=str(settings.telegram_chat_id or ""),
        allowed=admin_chat_allowed,
    )
    if not admin_chat_allowed:
        _trace("message_ignored", reason="not_admin_chat", chat_id=chat_id, from_id=admin_id)
        logger.warning("telegram_admin_message_rejected chat_id=%s admin_id=%s", chat_id, admin_id)
        return

    if text in {"/start", "/admin"}:
        _trace("admin_menu_send", chat_id=chat_id, from_id=admin_id)
        await telegram.send_message(
            "Управление платформой",
            chat_id=chat_id,
            reply_markup=_admin_menu_markup(),
        )
        _trace("admin_menu_sent", chat_id=chat_id, from_id=admin_id)
        return

    _trace("session_resolution_start", chat_id=chat_id, from_id=admin_id, sender_chat_id=sender_chat_id)
    pending = await _pending_session_for_message(session, admin_id, chat_id)
    if pending is None:
        _trace("session_resolution_result", chat_id=chat_id, from_id=admin_id, found=False)
        logger.warning(
            "telegram_admin_message_without_session chat_id=%s admin_id=%s sender_chat_id=%s",
            chat_id,
            admin_id,
            str((message.get("sender_chat") or {}).get("id") or ""),
        )
        await telegram.send_message(
            "⚠️ Активный сценарий не найден. Нажмите «⭐ Главное промо» и попробуйте снова.",
            chat_id=chat_id,
        )
        _trace("telegram_response_requested", chat_id=chat_id, outcome="session_not_found")
        return

    _trace(
        "session_resolution_result",
        chat_id=chat_id,
        from_id=admin_id,
        found=True,
        session_id=str(pending.id),
        session_admin_id=pending.admin_telegram_id,
        state=pending.state,
    )
    if pending.state == FEATURED_USERNAME_STATE:
        _trace(
            "promo_username_handler_enter",
            chat_id=chat_id,
            from_id=admin_id,
            session_id=str(pending.id),
            username=text,
        )
        try:
            await _handle_featured_username(session, pending, text, telegram)
        except Exception:
            await session.rollback()
            logger.exception(
                "telegram_featured_username_failed chat_id=%s admin_id=%s username=%s",
                chat_id,
                admin_id,
                text,
            )
            await telegram.send_message(
                "❌ Внутренняя ошибка. Попробуйте ещё раз или проверьте логи.",
                chat_id=chat_id,
            )
            raise
        return

    if pending.state == FEATURED_CONFIRMATION_STATE:
        await telegram.send_message("Используйте кнопки подтверждения или отмены.", chat_id=chat_id)
        return

    if pending.campaign_id is None:
        await session.delete(pending)
        await session.commit()
        return

    await _finalize_moderation(
        session,
        pending.campaign_id,
        CampaignStatus.revision_required,
        "Сбор возвращён на доработку.",
        f"Сбор возвращён на доработку.\n\nКомментарий:\n{text}",
        pending.chat_id,
        pending.message_id,
        "✏️ Возвращено на доработку",
        pending.admin_name,
        telegram,
        comment=text,
    )


async def _pending_session_for_message(
    session: AsyncSession,
    admin_id: str,
    chat_id: str,
) -> TelegramModerationSession | None:
    if admin_id:
        _trace("session_lookup_by_from_id_start", chat_id=chat_id, from_id=admin_id)
        pending = await session.scalar(
            select(TelegramModerationSession).where(
                TelegramModerationSession.admin_telegram_id == admin_id
            ).with_for_update()
        )
        _trace(
            "session_lookup_by_from_id_result",
            chat_id=chat_id,
            from_id=admin_id,
            found=pending is not None,
            session_id=str(pending.id) if pending else None,
            state=pending.state if pending else None,
        )
        if pending is not None:
            return pending
    else:
        _trace("session_lookup_by_from_id_skipped", chat_id=chat_id, reason="missing_from_id")

    _trace("session_lookup_by_chat_id_start", chat_id=chat_id, states=FEATURED_STATES)
    featured_sessions = list(
        await session.scalars(
            select(TelegramModerationSession).where(
                TelegramModerationSession.chat_id == chat_id,
                TelegramModerationSession.state.in_(FEATURED_STATES),
            ).with_for_update()
        )
    )
    _trace(
        "session_lookup_by_chat_id_result",
        chat_id=chat_id,
        count=len(featured_sessions),
        session_ids=[str(item.id) for item in featured_sessions],
        states=[item.state for item in featured_sessions],
    )
    if len(featured_sessions) == 1:
        pending = featured_sessions[0]
        logger.warning(
            "telegram_featured_session_recovered chat_id=%s expected_admin_id=%s actual_admin_id=%s",
            chat_id,
            pending.admin_telegram_id,
            admin_id,
        )
        return pending
    if len(featured_sessions) > 1:
        logger.error("telegram_featured_session_ambiguous chat_id=%s count=%s", chat_id, len(featured_sessions))
    return None


async def _start_revision(
    session: AsyncSession,
    campaign_id: UUID,
    chat_id: str,
    message_id: int,
    admin_id: str,
    admin_name: str,
    telegram: TelegramNotifier,
) -> None:
    campaign = await _pending_campaign(session, campaign_id)
    if campaign is None:
        await telegram.edit_message_text(chat_id, message_id, _final_text("Уже обработано", admin_name), reply_markup={"inline_keyboard": []})
        return

    await session.execute(delete(TelegramModerationSession).where(TelegramModerationSession.admin_telegram_id == admin_id))
    session.add(
        TelegramModerationSession(
            campaign_id=campaign.id,
            chat_id=chat_id,
            message_id=message_id,
            admin_telegram_id=admin_id,
            admin_name=admin_name,
            state=REVISION_REASON_STATE,
        )
    )
    await session.commit()
    await telegram.edit_message_text(
        chat_id,
        message_id,
        _final_text("✏️ Ожидается комментарий", admin_name),
        reply_markup={"inline_keyboard": []},
    )
    await telegram.send_message("Введите причину возврата.", chat_id=chat_id)


async def _finalize_moderation(
    session: AsyncSession,
    campaign_id: UUID,
    new_status: CampaignStatus,
    notification_title: str,
    notification_body: str,
    chat_id: str,
    message_id: int,
    final_label: str,
    admin_name: str,
    telegram: TelegramNotifier,
    comment: str | None = None,
    create_public_activity: bool = False,
) -> bool:
    campaign = await _pending_campaign(session, campaign_id)
    if campaign is None:
        await session.execute(delete(TelegramModerationSession).where(TelegramModerationSession.campaign_id == campaign_id))
        await session.commit()
        await telegram.edit_message_text(chat_id, message_id, _final_text("Уже обработано", admin_name), reply_markup={"inline_keyboard": []})
        return False

    campaign.status = new_status
    if create_public_activity:
        await create_activity(session, ActivityType.campaign_created, actor_user_id=campaign.owner_id, campaign_id=campaign.id)
    await create_notification(
        session,
        campaign.owner_id,
        NotificationType.campaign_moderation,
        notification_title,
        notification_body,
        campaign_id=campaign.id,
        action_url=f"/campaigns/{campaign.id}/edit" if new_status == CampaignStatus.revision_required else f"/campaigns/{campaign.id}",
    )
    await session.execute(delete(TelegramModerationSession).where(TelegramModerationSession.campaign_id == campaign.id))
    await session.commit()
    await telegram.edit_message_text(
        chat_id,
        message_id,
        _final_text(final_label, admin_name, comment=comment),
        reply_markup={"inline_keyboard": []},
    )
    return True


async def _handle_featured_callback(
    session: AsyncSession,
    data: str,
    callback_id: str,
    chat_id: str,
    message_id: int,
    admin_id: str,
    admin_name: str,
    telegram: TelegramNotifier,
) -> None:
    action = data.split(":", 1)[1] if ":" in data else ""
    _trace(
        "promo_callback_handler_enter",
        action=action,
        chat_id=chat_id,
        from_id=admin_id,
        callback_id=callback_id,
    )
    if action == "start":
        _trace("promo_selection_start_requested", chat_id=chat_id, from_id=admin_id)
        await _start_featured_selection(session, chat_id, message_id, admin_id, admin_name, telegram)
        _trace("promo_selection_start_completed", chat_id=chat_id, from_id=admin_id)
        if callback_id:
            await telegram.answer_callback_query(callback_id)
        return

    if action == "cancel":
        await session.execute(
            delete(TelegramModerationSession).where(TelegramModerationSession.admin_telegram_id == admin_id)
        )
        await session.commit()
        await telegram.edit_message_text(
            chat_id,
            message_id,
            "❌ Отменено.",
            reply_markup={"inline_keyboard": []},
        )
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Отменено.")
        return

    if action != "confirm":
        _trace("promo_callback_ignored", action=action, reason="unknown_action", chat_id=chat_id)
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Неизвестное действие.")
        return

    _trace("promo_confirmation_session_lookup_start", chat_id=chat_id, from_id=admin_id)
    pending = await session.scalar(
        select(TelegramModerationSession).where(
            TelegramModerationSession.admin_telegram_id == admin_id,
            TelegramModerationSession.state == FEATURED_CONFIRMATION_STATE,
        ).with_for_update()
    )
    _trace(
        "promo_confirmation_session_lookup_result",
        chat_id=chat_id,
        from_id=admin_id,
        found=pending is not None,
        session_id=str(pending.id) if pending else None,
        state=pending.state if pending else None,
        requested_username=pending.requested_username if pending else None,
    )
    if pending is None or not pending.requested_username:
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Сессия устарела.")
        return

    try:
        _trace(
            "featured_campaign_update_start",
            chat_id=chat_id,
            session_id=str(pending.id),
            username=pending.requested_username,
        )
        await set_featured_campaign_by_username(session, pending.requested_username)
        _trace(
            "featured_campaign_update_completed",
            chat_id=chat_id,
            session_id=str(pending.id),
            username=pending.requested_username,
        )
    except FeaturedCampaignUserNotFoundError:
        _trace("promo_outcome", chat_id=chat_id, outcome="user_not_found")
        await session.delete(pending)
        await session.commit()
        await telegram.edit_message_text(
            chat_id,
            message_id,
            "❌ Пользователь не найден.",
            reply_markup={"inline_keyboard": []},
        )
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Пользователь не найден.")
        return
    except FeaturedCampaignActiveCampaignNotFoundError:
        _trace("promo_outcome", chat_id=chat_id, outcome="active_campaign_not_found")
        await session.delete(pending)
        await session.commit()
        await telegram.edit_message_text(
            chat_id,
            message_id,
            "❌ У пользователя сейчас нет активной истории.",
            reply_markup={"inline_keyboard": []},
        )
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Нет активной истории.")
        return
    except FeaturedCampaignMultipleActiveCampaignsError:
        _trace("promo_outcome", chat_id=chat_id, outcome="multiple_active_campaigns")
        await session.delete(pending)
        await session.commit()
        await telegram.edit_message_text(
            chat_id,
            message_id,
            "❌ У пользователя найдено несколько активных сборов.",
            reply_markup={"inline_keyboard": []},
        )
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Найдено несколько сборов.")
        return
    except FeaturedCampaignAlreadySelectedError:
        _trace("promo_outcome", chat_id=chat_id, outcome="already_featured")
        await session.delete(pending)
        await session.commit()
        await telegram.edit_message_text(
            chat_id,
            message_id,
            "ℹ️ Этот сбор уже является главным.",
            reply_markup={"inline_keyboard": []},
        )
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Сбор уже является главным.")
        return

    await session.delete(pending)
    await session.commit()
    _trace("promo_session_deleted", chat_id=chat_id, outcome="success")
    _trace("telegram_response_send", chat_id=chat_id, method="editMessageText", outcome="success")
    await telegram.edit_message_text(
        chat_id,
        message_id,
        "✅ Сбор успешно назначен главным.",
        reply_markup={"inline_keyboard": []},
    )
    if callback_id:
        await telegram.answer_callback_query(callback_id, "Сбор успешно назначен главным.")
    _trace("promo_outcome", chat_id=chat_id, outcome="success")


async def _start_featured_selection(
    session: AsyncSession,
    chat_id: str,
    message_id: int,
    admin_id: str,
    admin_name: str,
    telegram: TelegramNotifier,
) -> None:
    _trace("promo_session_reset_start", chat_id=chat_id, from_id=admin_id)
    await session.execute(
        delete(TelegramModerationSession).where(
            (TelegramModerationSession.admin_telegram_id == admin_id)
            | (
                (TelegramModerationSession.chat_id == chat_id)
                & TelegramModerationSession.state.in_(FEATURED_STATES)
            )
        )
    )
    pending = TelegramModerationSession(
        campaign_id=None,
        chat_id=chat_id,
        message_id=message_id,
        admin_telegram_id=admin_id,
        admin_name=admin_name,
        state=FEATURED_USERNAME_STATE,
    )
    session.add(pending)
    _trace(
        "promo_session_added",
        chat_id=chat_id,
        from_id=admin_id,
        state=FEATURED_USERNAME_STATE,
    )
    await session.commit()
    _trace(
        "promo_session_committed",
        chat_id=chat_id,
        from_id=admin_id,
        session_id=str(pending.id),
        state=pending.state,
    )
    _trace("telegram_response_send", chat_id=chat_id, method="sendMessage", outcome="username_prompt")
    await telegram.send_message(
        "Введите username пользователя (без символа @)\n\nНапример:\n\nhakatoshka",
        chat_id=chat_id,
        reply_markup={
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": f"{PROMO_ACTION_PREFIX}:cancel"}],
            ]
        },
    )
    _trace("telegram_response_returned", chat_id=chat_id, method="sendMessage", outcome="username_prompt")


async def _handle_featured_username(
    session: AsyncSession,
    pending: TelegramModerationSession,
    username: str,
    telegram: TelegramNotifier,
) -> None:
    _trace(
        "promo_username_lookup_start",
        chat_id=pending.chat_id,
        session_id=str(pending.id),
        username=username,
    )
    try:
        campaign = await find_active_campaign_by_username(session, username)
    except FeaturedCampaignUserNotFoundError:
        _trace("promo_outcome", chat_id=pending.chat_id, outcome="user_not_found", username=username)
        _trace("telegram_response_send", chat_id=pending.chat_id, method="sendMessage", outcome="user_not_found")
        await telegram.send_message("❌ Пользователь не найден.", chat_id=pending.chat_id)
        return
    except FeaturedCampaignActiveCampaignNotFoundError:
        _trace("promo_outcome", chat_id=pending.chat_id, outcome="active_campaign_not_found", username=username)
        _trace(
            "telegram_response_send",
            chat_id=pending.chat_id,
            method="sendMessage",
            outcome="active_campaign_not_found",
        )
        await telegram.send_message(
            "❌ У пользователя сейчас нет активной истории.",
            chat_id=pending.chat_id,
        )
        return
    except FeaturedCampaignMultipleActiveCampaignsError:
        _trace("promo_outcome", chat_id=pending.chat_id, outcome="multiple_active_campaigns", username=username)
        _trace(
            "telegram_response_send",
            chat_id=pending.chat_id,
            method="sendMessage",
            outcome="multiple_active_campaigns",
        )
        await telegram.send_message(
            "❌ У пользователя найдено несколько активных сборов.",
            chat_id=pending.chat_id,
        )
        return

    _trace(
        "promo_username_lookup_result",
        chat_id=pending.chat_id,
        session_id=str(pending.id),
        username=username,
        campaign_id=str(campaign.id),
        owner_id=str(campaign.owner_id),
        campaign_status=campaign.status.value,
        campaign_is_active=campaign.is_active,
    )
    already_featured = await is_featured_campaign(session, campaign.id)
    _trace(
        "featured_campaign_current_check",
        chat_id=pending.chat_id,
        campaign_id=str(campaign.id),
        already_featured=already_featured,
    )
    if already_featured:
        await session.delete(pending)
        await session.commit()
        _trace("promo_outcome", chat_id=pending.chat_id, outcome="already_featured")
        _trace("telegram_response_send", chat_id=pending.chat_id, method="sendMessage", outcome="already_featured")
        await telegram.send_message("ℹ️ Этот сбор уже является главным.", chat_id=pending.chat_id)
        return

    _trace(
        "promo_fsm_transition_start",
        chat_id=pending.chat_id,
        session_id=str(pending.id),
        from_state=pending.state,
        to_state=FEATURED_CONFIRMATION_STATE,
        campaign_id=str(campaign.id),
    )
    pending.campaign_id = campaign.id
    pending.requested_username = campaign.owner.username
    pending.state = FEATURED_CONFIRMATION_STATE
    await session.commit()
    _trace(
        "promo_fsm_transition_committed",
        chat_id=pending.chat_id,
        session_id=str(pending.id),
        state=pending.state,
        requested_username=pending.requested_username,
        campaign_id=str(pending.campaign_id),
    )
    _trace("telegram_response_send", chat_id=pending.chat_id, method="sendMessage", outcome="confirmation_card")
    await telegram.send_message(
        _featured_campaign_card(campaign),
        chat_id=pending.chat_id,
        reply_markup={
            "inline_keyboard": [
                [{"text": "⭐ Сделать главным", "callback_data": f"{PROMO_ACTION_PREFIX}:confirm"}],
                [{"text": "❌ Отмена", "callback_data": f"{PROMO_ACTION_PREFIX}:cancel"}],
            ]
        },
    )
    _trace("telegram_response_returned", chat_id=pending.chat_id, method="sendMessage", outcome="confirmation_card")


async def _ask_archive_confirmation(
    chat_id: str,
    message_id: int,
    campaign_id: UUID,
    telegram: TelegramNotifier,
) -> None:
    await telegram.edit_message_text(
        chat_id,
        message_id,
        "Скрыть сбор из публичной части?\n\nСбор останется в базе, платежи и донаты сохранятся.",
        reply_markup={
            "inline_keyboard": [
                [{"text": "Да, скрыть сбор", "callback_data": f"{ADMIN_ACTION_PREFIX}:confirm_archive:{campaign_id}"}],
                [{"text": "Отмена", "callback_data": f"{ADMIN_ACTION_PREFIX}:recalc:{campaign_id}"}],
            ]
        },
    )


async def _archive_campaign(
    session: AsyncSession,
    campaign_id: UUID,
    chat_id: str,
    message_id: int,
    admin_name: str,
    telegram: TelegramNotifier,
) -> bool:
    campaign = await _campaign_any(session, campaign_id)
    if campaign is None:
        await telegram.edit_message_text(chat_id, message_id, _final_text("Сбор не найден", admin_name), reply_markup={"inline_keyboard": []})
        return False

    campaign.status = CampaignStatus.archived
    campaign.is_active = False
    await session.commit()
    await telegram.edit_message_text(chat_id, message_id, _final_text("Сбор скрыт", admin_name), reply_markup={"inline_keyboard": []})
    return True


async def _recalculate_campaign(
    session: AsyncSession,
    campaign_id: UUID,
    chat_id: str,
    message_id: int,
    admin_name: str,
    telegram: TelegramNotifier,
) -> bool:
    campaign = await _campaign_any(session, campaign_id)
    if campaign is None:
        await telegram.edit_message_text(chat_id, message_id, _final_text("Сбор не найден", admin_name), reply_markup={"inline_keyboard": []})
        return False

    campaign = await recalculate_campaign_aggregates(session, campaign_id)
    await telegram.edit_message_text(
        chat_id,
        message_id,
        _final_text(f"Пересчет выполнен\nСумма: {campaign.current_amount}\nСтатус: {campaign.status.value}", admin_name),
        reply_markup={"inline_keyboard": []},
    )
    return True


async def _pending_campaign(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(Campaign.id == campaign_id, Campaign.status == CampaignStatus.pending_review)
        .with_for_update()
    )


async def _campaign_any(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update())


def _admin_menu_markup() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "⭐ Главное промо", "callback_data": f"{PROMO_ACTION_PREFIX}:start"}],
        ]
    }


def _is_admin_chat(chat_id: str) -> bool:
    configured_chat_id = settings.telegram_chat_id
    if not configured_chat_id:
        return settings.app_env.lower() != "production"
    return str(configured_chat_id) == chat_id


def _featured_campaign_card(campaign: Campaign) -> str:
    owner_name = " ".join(
        part for part in (campaign.owner.first_name, campaign.owner.last_name) if part
    ) or campaign.owner.username
    return "\n".join(
        [
            owner_name,
            f"@{campaign.owner.username}",
            "",
            campaign.title,
            "",
            f"{_format_money(campaign.current_amount)} из {_format_money(campaign.target_amount)}",
        ]
    )


def _format_money(amount) -> str:
    if amount == int(amount):
        value = f"{int(amount):,}"
    else:
        value = f"{amount:,.2f}"
    return f"{value.replace(',', ' ')} ₽"


def _parse_callback_data(data: str) -> tuple[str, UUID] | None:
    parts = data.split(":")
    if len(parts) != 3:
        return None
    if parts[0] == ACTION_PREFIX and parts[1] not in {"approve", "revision", "reject"}:
        return None
    if parts[0] == ADMIN_ACTION_PREFIX and parts[1] not in {"archive", "confirm_archive", "recalc"}:
        return None
    if parts[0] not in {ACTION_PREFIX, ADMIN_ACTION_PREFIX}:
        return None
    try:
        return parts[1], UUID(parts[2])
    except ValueError:
        return None


def _admin_name(admin: dict) -> str:
    username = admin.get("username")
    if username:
        return f"@{username}"
    name = " ".join(part for part in (admin.get("first_name"), admin.get("last_name")) if part)
    return name or "Администратор"


def _final_text(label: str, admin_name: str, comment: str | None = None) -> str:
    parts = [
        label,
        "",
        admin_name,
        _now_moscow(),
    ]
    if comment:
        parts.extend(["", "Комментарий:", comment])
    return "\n".join(parts)


def _now_moscow() -> str:
    return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y\n%H:%M")
