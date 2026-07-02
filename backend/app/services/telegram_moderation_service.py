from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.telegram_notifier import TelegramNotifier
from app.models.activity import ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.notification import NotificationType
from app.models.telegram_moderation_session import TelegramModerationSession
from app.services.activity_service import create_activity
from app.services.notification_service import create_notification

ACTION_PREFIX = "hvc"


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
    parsed = _parse_callback_data(data)
    if parsed is None:
        if callback_id:
            await telegram.answer_callback_query(callback_id, "Неизвестное действие.")
        return

    action, campaign_id = parsed
    message = callback_query.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", ""))
    message_id = int(message.get("message_id") or 0)
    admin = callback_query.get("from") or {}
    admin_id = str(admin.get("id") or "")
    admin_name = _admin_name(admin)

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
    if not text or not admin_id:
        return

    pending = await session.scalar(
        select(TelegramModerationSession).where(TelegramModerationSession.admin_telegram_id == admin_id)
    )
    if pending is None:
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


async def _pending_campaign(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.scalar(
        select(Campaign)
        .options(selectinload(Campaign.owner))
        .where(Campaign.id == campaign_id, Campaign.status == CampaignStatus.pending_review)
        .with_for_update()
    )


def _parse_callback_data(data: str) -> tuple[str, UUID] | None:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != ACTION_PREFIX or parts[1] not in {"approve", "revision", "reject"}:
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
