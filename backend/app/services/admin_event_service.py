from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.integrations.telegram_notifier import TelegramNotifier
from app.models.campaign import Campaign
from app.models.report import Report
from app.models.user import User
from app.schemas.contact import ContactRequestIn


class AdminEventType(str, Enum):
    contact_request = "contact_request"
    user_report = "user_report"
    high_value_campaign = "high_value_campaign"


@dataclass(frozen=True)
class AdminActor:
    id: UUID
    username: str
    profile_url: str


@dataclass(frozen=True)
class AdminEvent:
    type: AdminEventType
    title: str
    sections: list[tuple[str, str]]
    actor: AdminActor | None = None
    created_at: datetime | None = None
    metadata: dict[str, str] | None = None


class AdminEventService:
    def __init__(self, telegram_notifier: TelegramNotifier) -> None:
        self.telegram_notifier = telegram_notifier

    async def publish(self, event: AdminEvent) -> None:
        await self.telegram_notifier.send_message(
            _format_telegram_message(event),
            reply_markup=_reply_markup_for_event(event),
        )


def build_contact_event(payload: ContactRequestIn, actor: AdminActor | None = None) -> AdminEvent:
    sections = [
        ("Тема", payload.subject.value),
        ("Имя", payload.name),
        ("Email", str(payload.email)),
        ("Сообщение", payload.message),
    ]
    return AdminEvent(
        type=AdminEventType.contact_request,
        title="📩 Новое обращение",
        sections=sections,
        actor=actor,
    )


def build_user_report_event(report: Report, campaign: Campaign, reporter: User | None) -> AdminEvent:
    sections = [
        ("Сбор", campaign.title),
        ("ID кампании", str(campaign.id)),
    ]
    if campaign.owner is not None:
        sections.append(("Автор сбора", _user_display_name(campaign.owner)))
    sections.append(("__divider__", ""))
    if reporter is not None:
        sections.extend(
            [
                ("Отправил", _user_display_name(reporter)),
                ("Telegram", f"@{reporter.username}"),
                ("ID пользователя", str(reporter.id)),
                ("__divider__", ""),
            ]
        )
    sections.extend(
        [
            ("Причина", report.reason),
            ("Комментарий", report.details or "—"),
            ("__divider__", ""),
            ("Открыть сбор", _campaign_url(campaign.id)),
        ]
    )
    return AdminEvent(
        type=AdminEventType.user_report,
        title="🚨 Новая жалоба",
        sections=sections,
    )


def build_high_value_campaign_event(campaign: Campaign, owner: User) -> AdminEvent:
    return AdminEvent(
        type=AdminEventType.high_value_campaign,
        title="💰 Новый крупный сбор",
        sections=[
            ("Название", campaign.title),
            ("Сумма", _format_rub(campaign.target_amount)),
            ("Автор", _user_display_name(owner)),
            ("Telegram", f"@{owner.username}"),
            ("ID пользователя", str(owner.id)),
            ("__divider__", ""),
            ("Описание", _truncate(campaign.description, 500)),
            ("__divider__", ""),
            ("Открыть сбор", _campaign_url(campaign.id)),
        ],
        metadata={"campaign_id": str(campaign.id)},
    )


def admin_actor_from_user(user_id: UUID, username: str) -> AdminActor:
    base_url = settings.frontend_public_url.rstrip("/")
    return AdminActor(
        id=user_id,
        username=username,
        profile_url=f"{base_url}/u/{username}",
    )


def get_admin_event_service() -> AdminEventService:
    return AdminEventService(
        TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
    )


def _format_telegram_message(event: AdminEvent) -> str:
    created_at = event.created_at or datetime.now(ZoneInfo("Europe/Moscow"))
    parts = [
        event.title,
        "",
        "━━━━━━━━━━━━━━",
    ]

    for title, value in event.sections:
        if title == "__divider__":
            parts.extend(["", "━━━━━━━━━━━━━━"])
            continue
        if title == "Сообщение":
            continue
        parts.extend(["", title, value])

    if event.actor is not None:
        parts.extend(
            [
                "",
                "Пользователь",
                f"@{event.actor.username}",
                f"ID: {event.actor.id}",
                event.actor.profile_url,
            ]
        )

    message = next((value for title, value in event.sections if title == "Сообщение"), None)
    if message is not None:
        parts.extend(
            [
                "",
                "━━━━━━━━━━━━━━",
                "",
                "Сообщение",
                message,
                "",
                "━━━━━━━━━━━━━━",
            ]
        )
    parts.extend(["", created_at.strftime("%d.%m.%Y %H:%M")])
    return "\n".join(parts)


def _campaign_url(campaign_id: UUID) -> str:
    return f"{settings.frontend_public_url.rstrip('/')}/campaigns/{campaign_id}"


def _format_rub(amount) -> str:
    value = int(amount) if amount == int(amount) else amount
    return f"{value:,}".replace(",", " ") + " ₽"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def _user_display_name(user: User) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part)
    return name or user.username


def _reply_markup_for_event(event: AdminEvent) -> dict | None:
    if event.type != AdminEventType.high_value_campaign or not event.metadata:
        return None
    campaign_id = event.metadata.get("campaign_id")
    if not campaign_id:
        return None
    return {
        "inline_keyboard": [
            [{"text": "✅ Одобрить", "callback_data": f"hvc:approve:{campaign_id}"}],
            [{"text": "✏️ Вернуть на доработку", "callback_data": f"hvc:revision:{campaign_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"hvc:reject:{campaign_id}"}],
        ]
    }
