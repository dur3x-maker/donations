from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.integrations.telegram_notifier import TelegramNotifier
from app.models.activity import ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.notification import NotificationType
from app.models.telegram_moderation_session import TelegramModerationSession
from app.services.activity_service import create_activity
from app.services.campaign_service import recalculate_campaign_aggregates
from app.services.featured_campaign_service import (
    FeaturedCampaignActiveCampaignNotFoundError,
    FeaturedCampaignUserNotFoundError,
    find_active_campaign_by_username,
    set_featured_campaign_by_username,
)
from app.services.notification_service import create_notification

ACTION_PREFIX = "hvc"
ADMIN_ACTION_PREFIX = "admin"
PROMO_ACTION_PREFIX = "promo"
REVISION_REASON_STATE = "revision_reason"
FEATURED_USERNAME_STATE = "featured_username"
FEATURED_CONFIRMATION_STATE = "featured_confirmation"


async def handle_telegram_update(
    session: AsyncSession,
    update: dict,
    telegram: TelegramNotifier,
) -> None:
    callback_query = update.get("callback_query")
    if callback_query:
        await _handle_callback_query(session, callback_query, telegram)
        return

    message = update.get("message")
    if message:
        await _handle_message(session, message, telegram)


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

    if not _is_admin_chat(chat_id):
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Недостаточно прав.")
        return

    if data.startswith(f"{PROMO_ACTION_PREFIX}:"):
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
    if not text or not admin_id:
        return
    if not _is_admin_chat(chat_id):
        return

    if text in {"/start", "/admin"}:
        await telegram.send_message(
            "Управление платформой",
            chat_id=chat_id,
            reply_markup=_admin_menu_markup(),
        )
        return

    pending = await session.scalar(
        select(TelegramModerationSession).where(TelegramModerationSession.admin_telegram_id == admin_id)
    )
    if pending is None:
        return

    if pending.state == FEATURED_USERNAME_STATE:
        await _handle_featured_username(session, pending, text, telegram)
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
    if action == "start":
        await _start_featured_selection(session, chat_id, message_id, admin_id, admin_name, telegram)
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
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Неизвестное действие.")
        return

    pending = await session.scalar(
        select(TelegramModerationSession).where(
            TelegramModerationSession.admin_telegram_id == admin_id,
            TelegramModerationSession.state == FEATURED_CONFIRMATION_STATE,
        )
    )
    if pending is None or not pending.requested_username:
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Сессия устарела.")
        return

    try:
        await set_featured_campaign_by_username(session, pending.requested_username)
    except FeaturedCampaignUserNotFoundError:
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

    await session.delete(pending)
    await session.commit()
    await telegram.edit_message_text(
        chat_id,
        message_id,
        "✅ Главная история обновлена.",
        reply_markup={"inline_keyboard": []},
    )
    if callback_id:
        await telegram.answer_callback_query(callback_id, "Главная история обновлена.")


async def _start_featured_selection(
    session: AsyncSession,
    chat_id: str,
    message_id: int,
    admin_id: str,
    admin_name: str,
    telegram: TelegramNotifier,
) -> None:
    await session.execute(
        delete(TelegramModerationSession).where(TelegramModerationSession.admin_telegram_id == admin_id)
    )
    session.add(
        TelegramModerationSession(
            campaign_id=None,
            chat_id=chat_id,
            message_id=message_id,
            admin_telegram_id=admin_id,
            admin_name=admin_name,
            state=FEATURED_USERNAME_STATE,
        )
    )
    await session.commit()
    await telegram.send_message(
        "Введите username пользователя (без символа @)\n\nНапример:\n\nhakatoshka",
        chat_id=chat_id,
        reply_markup={
            "inline_keyboard": [
                [{"text": "❌ Отмена", "callback_data": f"{PROMO_ACTION_PREFIX}:cancel"}],
            ]
        },
    )


async def _handle_featured_username(
    session: AsyncSession,
    pending: TelegramModerationSession,
    username: str,
    telegram: TelegramNotifier,
) -> None:
    try:
        campaign = await find_active_campaign_by_username(session, username)
    except FeaturedCampaignUserNotFoundError:
        await telegram.send_message("❌ Пользователь не найден.", chat_id=pending.chat_id)
        return
    except FeaturedCampaignActiveCampaignNotFoundError:
        await telegram.send_message(
            "❌ У пользователя сейчас нет активной истории.",
            chat_id=pending.chat_id,
        )
        return

    pending.campaign_id = campaign.id
    pending.requested_username = campaign.owner.username
    pending.state = FEATURED_CONFIRMATION_STATE
    await session.commit()
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
