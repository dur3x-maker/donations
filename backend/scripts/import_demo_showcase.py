"""Safely import the deterministic demo showcase into local/test PostgreSQL."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid5

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_rules import UNFINISHED_CAMPAIGN_STATUSES
from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.session import AsyncSessionLocal
from app.models.activity import Activity, ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_completion_report import CampaignCompletionPhoto, CampaignCompletionReport
from app.models.campaign_subscription import CampaignSubscription
from app.models.campaign_update import CampaignUpdate, CampaignUpdatePhoto
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.report import Report
from app.models.suspicious_flag import SuspiciousFlag
from app.models.telegram_moderation_session import TelegramModerationSession
from app.models.user import User, UserRole


DATASET_MARKER = "demo_showcase_v1"
DATASET_NAMESPACE = UUID("74cc41c5-14c8-4a28-a357-a365b834956f")
SAFE_ENVIRONMENTS = {"dev", "development", "local", "test", "testing", "stage", "staging"}
DISCLAIMER = (
    "Демонстрационная история: имена и обстоятельства вымышлены, "
    "а фотография используется как иллюстрация."
)
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_ROOT = BACKEND_ROOT / "demo_assets" / DATASET_MARKER
DEFAULT_UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "uploads"))
ADVISORY_LOCK_KEY = int.from_bytes(hashlib.sha256(DATASET_MARKER.encode()).digest()[:8], "big", signed=True)


class SafetyError(RuntimeError):
    """Raised when a destructive or ambiguous operation is not safe."""


@dataclass(frozen=True)
class DatabaseInfo:
    name: str
    user: str
    server_address: str


@dataclass
class AssetRollback:
    previous: dict[Path, bytes | None]

    def restore(self) -> None:
        for path, content in self.previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)


def stable_uuid(kind: str, key: str) -> UUID:
    return uuid5(DATASET_NAMESPACE, f"{DATASET_MARKER}:{kind}:{key}")


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SafetyError(f"Timestamp must include timezone: {value}")
    return parsed.astimezone(timezone.utc)


def load_dataset(asset_root: Path = DEFAULT_ASSET_ROOT) -> dict[str, Any]:
    data = json.loads((asset_root / "showcase.json").read_text(encoding="utf-8"))
    if data.get("dataset") != DATASET_MARKER:
        raise SafetyError("Showcase data has an unexpected dataset marker")
    authors = data.get("authors", [])
    campaigns = data.get("campaigns", [])
    if len(authors) != 8:
        raise SafetyError("Showcase must contain exactly 8 demo authors")
    active_count = sum("completion_report" not in item for item in campaigns)
    completed_count = sum("completion_report" in item for item in campaigns)
    if (active_count, completed_count) != (8, 3):
        raise SafetyError("Showcase must contain 8 active and 3 completed campaigns")
    author_keys = {item["key"] for item in authors}
    if len(author_keys) != len(authors):
        raise SafetyError("Demo author keys must be unique")
    for item in campaigns:
        if item["owner"] not in author_keys:
            raise SafetyError(f"Unknown owner for campaign {item['key']}")
        if Decimal(item["current_amount"]) != sum(_donation_amounts(item)):
            raise SafetyError(f"Donation total does not match current_amount for {item['key']}")
        description = _campaign_description(item)
        if not (10 <= len(description) <= 5000):
            raise SafetyError(f"Campaign description has invalid length: {item['key']}")
    validate_assets(data, asset_root)
    return data


def validate_assets(data: dict[str, Any], asset_root: Path = DEFAULT_ASSET_ROOT) -> dict[str, dict[str, str]]:
    manifest = json.loads((asset_root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("dataset") != DATASET_MARKER:
        raise SafetyError("Asset manifest has an unexpected dataset marker")
    by_name = {item["file"]: item for item in manifest.get("assets", [])}
    referenced = {item["cover"] for item in data["campaigns"]}
    if referenced != set(by_name):
        raise SafetyError("Asset manifest and showcase covers do not match")
    for filename, item in by_name.items():
        path = asset_root / "images" / filename
        if not path.is_file():
            raise SafetyError(f"Missing showcase asset: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise SafetyError(f"Checksum mismatch for showcase asset: {filename}")
    return by_name


def load_legacy_ids(path: Path | None) -> list[UUID]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = [UUID(value) for value in payload.get("campaign_ids", [])]
    if len(ids) != len(set(ids)):
        raise SafetyError("Legacy cleanup file contains duplicate campaign IDs")
    return ids


def validate_environment(app_env: str, database_name: str) -> None:
    normalized = app_env.strip().lower()
    if normalized not in SAFE_ENVIRONMENTS:
        raise SafetyError(
            f"Refusing to run in APP_ENV={app_env!r}; allowed environments: local, development, test, staging"
        )
    if "production" in database_name.lower() or database_name.lower().endswith("_prod"):
        raise SafetyError(f"Refusing to run against production-looking database {database_name!r}")


def resolve_public_base_url(app_env: str, explicit_value: str | None = None) -> str:
    value = explicit_value or os.getenv("PUBLIC_WEB_URL")
    if not value:
        raise SafetyError("PUBLIC_WEB_URL is required")
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise SafetyError("PUBLIC_WEB_URL must be an absolute http(s) origin without a path")
    if app_env.strip().lower() in {"stage", "staging"} and parsed.scheme != "https":
        raise SafetyError("Staging showcase images must use an https public base URL")
    return value.rstrip("/")


async def get_database_info(session: AsyncSession) -> DatabaseInfo:
    row = (
        await session.execute(
            text("SELECT current_database(), current_user, COALESCE(inet_server_addr()::text, 'local-socket')")
        )
    ).one()
    return DatabaseInfo(name=row[0], user=row[1], server_address=row[2])


def campaign_ids(data: dict[str, Any]) -> list[UUID]:
    return [stable_uuid("campaign", item["key"]) for item in data["campaigns"]]


async def dependency_counts(session: AsyncSession, ids: list[UUID]) -> dict[str, int]:
    if not ids:
        return {name: 0 for name in _dependency_names()}

    direct = {
        "activities": (Activity, Activity.campaign_id),
        "campaign_completion_reports": (CampaignCompletionReport, CampaignCompletionReport.campaign_id),
        "campaign_subscriptions": (CampaignSubscription, CampaignSubscription.campaign_id),
        "campaign_updates": (CampaignUpdate, CampaignUpdate.campaign_id),
        "contributions": (Contribution, Contribution.campaign_id),
        "notifications": (Notification, Notification.campaign_id),
        "reports": (Report, Report.campaign_id),
        "suspicious_flags": (SuspiciousFlag, SuspiciousFlag.campaign_id),
        "telegram_moderation_sessions": (TelegramModerationSession, TelegramModerationSession.campaign_id),
    }
    result: dict[str, int] = {}
    for name, (model, column) in direct.items():
        result[name] = int(
            await session.scalar(select(func.count()).select_from(model).where(column.in_(ids))) or 0
        )

    result["payments"] = int(
        await session.scalar(
            select(func.count())
            .select_from(Payment)
            .join(Contribution, Contribution.id == Payment.contribution_id)
            .where(Contribution.campaign_id.in_(ids))
        )
        or 0
    )
    result["campaign_update_photos"] = int(
        await session.scalar(
            select(func.count())
            .select_from(CampaignUpdatePhoto)
            .join(CampaignUpdate, CampaignUpdate.id == CampaignUpdatePhoto.update_id)
            .where(CampaignUpdate.campaign_id.in_(ids))
        )
        or 0
    )
    result["campaign_completion_photos"] = int(
        await session.scalar(
            select(func.count())
            .select_from(CampaignCompletionPhoto)
            .join(CampaignCompletionReport, CampaignCompletionReport.id == CampaignCompletionPhoto.report_id)
            .where(CampaignCompletionReport.campaign_id.in_(ids))
        )
        or 0
    )
    return dict(sorted(result.items()))


def _dependency_names() -> list[str]:
    return [
        "activities",
        "campaign_completion_photos",
        "campaign_completion_reports",
        "campaign_subscriptions",
        "campaign_update_photos",
        "campaign_updates",
        "contributions",
        "notifications",
        "payments",
        "reports",
        "suspicious_flags",
        "telegram_moderation_sessions",
    ]


async def existing_campaigns(session: AsyncSession, ids: list[UUID]) -> list[Campaign]:
    if not ids:
        return []
    return list(await session.scalars(select(Campaign).where(Campaign.id.in_(ids)).order_by(Campaign.created_at)))


async def orphan_counts(session: AsyncSession) -> dict[str, int]:
    checks = {
        "payments_without_contribution": (
            select(func.count())
            .select_from(Payment)
            .outerjoin(Contribution, Contribution.id == Payment.contribution_id)
            .where(Contribution.id.is_(None))
        ),
        "update_photos_without_update": (
            select(func.count())
            .select_from(CampaignUpdatePhoto)
            .outerjoin(CampaignUpdate, CampaignUpdate.id == CampaignUpdatePhoto.update_id)
            .where(CampaignUpdate.id.is_(None))
        ),
        "completion_photos_without_report": (
            select(func.count())
            .select_from(CampaignCompletionPhoto)
            .outerjoin(CampaignCompletionReport, CampaignCompletionReport.id == CampaignCompletionPhoto.report_id)
            .where(CampaignCompletionReport.id.is_(None))
        ),
    }
    return {name: int(await session.scalar(statement) or 0) for name, statement in checks.items()}


def asset_plan(data: dict[str, Any], upload_root: Path) -> dict[str, int]:
    destination = upload_root / DATASET_MARKER
    present = sum((destination / item["cover"]).is_file() for item in data["campaigns"])
    return {"source": len(data["campaigns"]), "present": present, "missing": len(data["campaigns"]) - present}


def sync_assets(data: dict[str, Any], asset_root: Path, upload_root: Path) -> AssetRollback:
    manifest = validate_assets(data, asset_root)
    destination = upload_root / DATASET_MARKER
    destination.mkdir(parents=True, exist_ok=True)
    previous: dict[Path, bytes | None] = {}
    for filename, item in manifest.items():
        source = asset_root / "images" / filename
        target = destination / filename
        current = target.read_bytes() if target.exists() else None
        if current is not None and hashlib.sha256(current).hexdigest() == item["sha256"]:
            continue
        previous[target] = current
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(source.read_bytes())
        os.replace(temporary, target)
    return AssetRollback(previous=previous)


async def apply_showcase(
    session: AsyncSession,
    data: dict[str, Any],
    password: str,
    public_base_url: str,
    *,
    replace_existing: bool,
    legacy_ids: list[UUID],
) -> None:
    if len(password) < 12:
        raise SafetyError("DEMO_USERS_PASSWORD must contain at least 12 characters")
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})

    users = await _ensure_demo_users(session, data["authors"], password, replace_existing)
    showcase_ids = campaign_ids(data)
    delete_ids = sorted(set(showcase_ids if replace_existing else []) | set(legacy_ids), key=str)
    if delete_ids:
        await session.execute(delete(Notification).where(Notification.campaign_id.in_(delete_ids)))
        await session.execute(delete(Campaign).where(Campaign.id.in_(delete_ids)))
        await session.flush()

    existing = {item.id: item for item in await existing_campaigns(session, showcase_ids)}
    for spec in data["campaigns"]:
        expected_id = stable_uuid("campaign", spec["key"])
        existing_item = existing.get(expected_id)
        if existing_item is not None:
            expected_owner = users[spec["owner"]].id
            if existing_item.owner_id != expected_owner:
                raise SafetyError(f"UUID collision for showcase campaign {expected_id}")

    missing_specs = [item for item in data["campaigns"] if stable_uuid("campaign", item["key"]) not in existing]
    await _ensure_no_unfinished_owner_conflicts(session, missing_specs, users, showcase_ids)
    for spec in missing_specs:
        await _create_campaign(session, spec, users, public_base_url)


async def _ensure_demo_users(
    session: AsyncSession,
    specs: list[dict[str, Any]],
    password: str,
    replace_existing: bool,
) -> dict[str, User]:
    ids = [stable_uuid("user", item["key"]) for item in specs]
    emails = [item["email"] for item in specs]
    usernames = [item["username"] for item in specs]
    found = list(
        await session.scalars(
            select(User).where(or_(User.id.in_(ids), User.email.in_(emails), User.username.in_(usernames)))
        )
    )
    by_id = {item.id: item for item in found}
    result: dict[str, User] = {}
    for spec in specs:
        expected_id = stable_uuid("user", spec["key"])
        collisions = [
            item
            for item in found
            if item.id == expected_id or item.email == spec["email"] or item.username == spec["username"]
        ]
        if collisions and not all(
            item.id == expected_id and item.email == spec["email"] and item.username == spec["username"]
            for item in collisions
        ):
            raise SafetyError(f"Demo identity collision for {spec['email']}; no user was changed")
        user = by_id.get(expected_id)
        if user is None:
            user = User(
                id=expected_id,
                email=spec["email"],
                username=spec["username"],
                password_hash=hash_password(password),
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                city=spec["city"],
                bio=spec["bio"],
                role=UserRole.user,
                is_active=True,
                is_verified=True,
                patron_since=datetime(2025, 12, 1, tzinfo=timezone.utc),
                created_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
            )
            session.add(user)
        else:
            if not verify_password(password, user.password_hash):
                user.password_hash = hash_password(password)
            if replace_existing:
                user.first_name = spec["first_name"]
                user.last_name = spec["last_name"]
                user.city = spec["city"]
                user.bio = spec["bio"]
                user.is_active = True
                user.is_verified = True
        result[spec["key"]] = user
    await session.flush()
    return result


async def _ensure_no_unfinished_owner_conflicts(
    session: AsyncSession,
    specs: list[dict[str, Any]],
    users: dict[str, User],
    showcase_ids: list[UUID],
) -> None:
    active_owner_ids = {users[item["owner"]].id for item in specs if "completion_report" not in item}
    if not active_owner_ids:
        return
    conflict = await session.scalar(
        select(Campaign).where(
            Campaign.owner_id.in_(active_owner_ids),
            Campaign.is_active.is_(True),
            Campaign.status.in_(UNFINISHED_CAMPAIGN_STATUSES),
            Campaign.id.not_in(showcase_ids),
        )
    )
    if conflict is not None:
        raise SafetyError(
            f"Demo author {conflict.owner_id} already owns unfinished non-showcase campaign {conflict.id}"
        )


async def _create_campaign(
    session: AsyncSession,
    spec: dict[str, Any],
    users: dict[str, User],
    public_base_url: str,
) -> None:
    campaign_id = stable_uuid("campaign", spec["key"])
    owner = users[spec["owner"]]
    created_at = parse_timestamp(spec["created_at"])
    completed = "completion_report" in spec
    report_at = parse_timestamp(spec["completion_report"]["created_at"]) if completed else None
    last_update_at = max((parse_timestamp(item["created_at"]) for item in spec["updates"]), default=created_at)
    updated_at = report_at or last_update_at
    cover_url = f"{public_base_url}/uploads/{DATASET_MARKER}/{spec['cover']}"
    campaign = Campaign(
        id=campaign_id,
        owner_id=owner.id,
        title=spec["title"],
        description=_campaign_description(spec),
        target_amount=Decimal(spec["target_amount"]),
        current_amount=Decimal(spec["current_amount"]),
        category=spec["category"],
        cover_image_url=cover_url,
        is_verified=True,
        is_active=True,
        status=CampaignStatus.completed if completed else CampaignStatus.active,
        has_completion_report=completed,
        goal_reached_notified_at=(report_at - timedelta(days=20)) if report_at else None,
        report_requested_at=(report_at - timedelta(days=18)) if report_at else None,
        report_completed_at=report_at,
        report_overdue=False,
        created_at=created_at,
        updated_at=updated_at,
    )
    session.add(campaign)
    await session.flush()

    author_list = list(users.values())
    donors = [item for item in author_list if item.id != owner.id]
    amounts = _donation_amounts(spec)
    end_at = (report_at - timedelta(days=2)) if report_at else datetime(2026, 7, 14, 9, tzinfo=timezone.utc)
    first_at = created_at + timedelta(days=2)
    interval = (end_at - first_at) / max(len(amounts) - 1, 1)
    contribution_rows: list[Contribution] = []
    for index, amount in enumerate(amounts):
        at = first_at + interval * index
        is_anonymous = index % 4 == 3
        donor = donors[index % len(donors)]
        contribution_id = stable_uuid("contribution", f"{spec['key']}:{index}")
        contribution = Contribution(
            id=contribution_id,
            campaign_id=campaign_id,
            user_id=None if is_anonymous else donor.id,
            anonymous_token=(f"{DATASET_MARKER}:{spec['key']}:{index}" if is_anonymous else None),
            amount=amount,
            status=ContributionStatus.confirmed,
            created_at=at,
        )
        contribution_rows.append(contribution)
        session.add(contribution)
        session.add(
            Payment(
                id=stable_uuid("payment", f"{spec['key']}:{index}"),
                contribution_id=contribution_id,
                provider="demo_showcase",
                external_payment_id=f"{DATASET_MARKER}-{spec['key']}-{index + 1}",
                amount=amount,
                currency="RUB",
                status=PaymentStatus.succeeded,
                confirmed_at=at,
                metadata_json={"dataset": DATASET_MARKER, "sequence": index + 1},
                created_at=at,
            )
        )
        session.add(
            Activity(
                id=stable_uuid("activity-donation", f"{spec['key']}:{index}"),
                type=ActivityType.donation_made,
                actor_user_id=None if is_anonymous else donor.id,
                campaign_id=campaign_id,
                metadata_json={"dataset": DATASET_MARKER, "amount": str(amount)},
                created_at=at,
            )
        )

    session.add(
        Activity(
            id=stable_uuid("activity-created", spec["key"]),
            type=ActivityType.campaign_created,
            actor_user_id=owner.id,
            campaign_id=campaign_id,
            metadata_json={"dataset": DATASET_MARKER},
            created_at=created_at,
        )
    )
    if completed and report_at:
        session.add(
            Activity(
                id=stable_uuid("activity-completed", spec["key"]),
                type=ActivityType.campaign_completed,
                actor_user_id=owner.id,
                campaign_id=campaign_id,
                metadata_json={"dataset": DATASET_MARKER},
                created_at=report_at,
            )
        )

    for index, subscriber in enumerate(donors[:3]):
        session.add(
            CampaignSubscription(
                id=stable_uuid("subscription", f"{spec['key']}:{subscriber.id}"),
                user_id=subscriber.id,
                campaign_id=campaign_id,
                is_active=True,
                muted=False,
                created_at=created_at + timedelta(days=index + 1),
            )
        )

    for index, update_spec in enumerate(spec["updates"]):
        update_at = parse_timestamp(update_spec["created_at"])
        update_id = stable_uuid("update", f"{spec['key']}:{index}")
        session.add(
            CampaignUpdate(
                id=update_id,
                campaign_id=campaign_id,
                author_id=owner.id,
                title=update_spec["title"],
                content=update_spec["content"],
                created_at=update_at,
                updated_at=update_at,
            )
        )
        if index == 0:
            session.add(
                CampaignUpdatePhoto(
                    id=stable_uuid("update-photo", f"{spec['key']}:{index}"),
                    update_id=update_id,
                    image_url=cover_url,
                    created_at=update_at,
                )
            )

    last_contribution = contribution_rows[-1]
    session.add(
        Notification(
            id=stable_uuid("notification", spec["key"]),
            user_id=owner.id,
            campaign_id=campaign_id,
            type=NotificationType.campaign_report_published if completed else NotificationType.donation_received,
            title="История завершена" if completed else "Новая поддержка истории",
            body=(
                "Итоговый отчёт опубликован и доступен участникам."
                if completed
                else "Ваша история получила новую поддержку. Спасибо, что публикуете обновления."
            ),
            action_url=f"/campaigns/{campaign_id}",
            is_read=completed,
            created_at=report_at or last_contribution.created_at,
        )
    )

    if completed and report_at:
        report_id = stable_uuid("completion-report", spec["key"])
        session.add(
            CampaignCompletionReport(
                id=report_id,
                campaign_id=campaign_id,
                author_id=owner.id,
                gratitude_text=spec["completion_report"]["gratitude_text"],
                created_at=report_at,
            )
        )
        session.add(
            CampaignCompletionPhoto(
                id=stable_uuid("completion-photo", spec["key"]),
                report_id=report_id,
                image_url=cover_url,
                created_at=report_at,
            )
        )
    await session.flush()


def _campaign_description(spec: dict[str, Any]) -> str:
    return f"{spec['short_description']}\n\n{spec['story']}\n\n{DISCLAIMER}"


def _donation_amounts(spec: dict[str, Any]) -> list[Decimal]:
    total = Decimal(spec["current_amount"])
    count = int(spec["donation_count"])
    if count < 1 or total < Decimal("100") * count:
        raise SafetyError(f"Invalid donation_count for {spec['key']}")
    weights = [Decimal(value) for value in (7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61)]
    selected = weights[:count]
    denominator = sum(selected)
    amounts = [max(Decimal("100"), (total * weight / denominator).quantize(Decimal("100"), rounding=ROUND_DOWN)) for weight in selected]
    remainder = total - sum(amounts)
    index = count - 1
    while remainder >= Decimal("100"):
        amounts[index] += Decimal("100")
        remainder -= Decimal("100")
        index = (index - 1) % count
    amounts[-1] += remainder
    return amounts


async def run(
    *,
    apply: bool,
    replace_existing: bool,
    app_env: str,
    password: str | None,
    public_base_url: str | None,
    asset_root: Path = DEFAULT_ASSET_ROOT,
    upload_root: Path = DEFAULT_UPLOAD_ROOT,
    legacy_ids: list[UUID] | None = None,
    confirm_legacy_cleanup: bool = False,
) -> dict[str, Any]:
    data = load_dataset(asset_root)
    legacy_ids = legacy_ids or []
    if legacy_ids and not replace_existing:
        raise SafetyError("Legacy cleanup inspection requires --replace-existing")
    if confirm_legacy_cleanup and not legacy_ids:
        raise SafetyError("--confirm-legacy-cleanup requires a non-empty legacy campaign ID file")
    if apply and legacy_ids and not confirm_legacy_cleanup:
        raise SafetyError("Legacy IDs require --confirm-legacy-cleanup; no changes were made")
    if apply and not password:
        raise SafetyError("DEMO_USERS_PASSWORD is required with --apply")

    showcase_ids = campaign_ids(data)
    inspected_ids = sorted(set(showcase_ids) | set(legacy_ids), key=str)
    async with AsyncSessionLocal() as session:
        info = await get_database_info(session)
        validate_environment(app_env, info.name)
        existing_showcase = await existing_campaigns(session, showcase_ids)
        legacy_rows = await existing_campaigns(session, legacy_ids)
        counts = await dependency_counts(session, inspected_ids)
        current_orphans = await orphan_counts(session)

    resolved_base = resolve_public_base_url(app_env, public_base_url)
    plan = {
        "mode": "apply" if apply else "dry-run",
        "environment": app_env,
        "database": info,
        "public_base_url": resolved_base,
        "showcase_existing": existing_showcase,
        "showcase_missing": len(showcase_ids) - len(existing_showcase),
        "legacy_rows": legacy_rows,
        "dependency_counts": counts,
        "asset_plan": asset_plan(data, upload_root),
        "orphans_before": current_orphans,
    }
    _print_plan(plan, replace_existing)
    if not apply:
        print("DRY-RUN: database and upload volume were not changed.")
        return plan

    rollback = sync_assets(data, asset_root, upload_root)
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await apply_showcase(
                    session,
                    data,
                    password or "",
                    resolved_base,
                    replace_existing=replace_existing,
                    legacy_ids=legacy_ids,
                )
                transaction_campaigns = await existing_campaigns(session, showcase_ids)
                transaction_orphans = await orphan_counts(session)
                if len(transaction_campaigns) != len(showcase_ids):
                    raise RuntimeError("Showcase verification failed: not all campaigns were created")
                increased_orphans = {
                    name: count
                    for name, count in transaction_orphans.items()
                    if count > current_orphans.get(name, 0)
                }
                if increased_orphans:
                    raise RuntimeError(
                        f"Showcase verification failed: import created orphan rows {increased_orphans}"
                    )
    except Exception:
        rollback.restore()
        raise

    async with AsyncSessionLocal() as session:
        final_campaigns = await existing_campaigns(session, showcase_ids)
        final_counts = await dependency_counts(session, showcase_ids)
        final_orphans = await orphan_counts(session)
    print("APPLY complete: 8 active campaigns, 3 completed campaigns, 8 demo authors.")
    print("Demo author logins (password was not logged):")
    for author in data["authors"]:
        print(f"  - {author['username']} / {author['email']}")
    print("Imported dependency counts:")
    for name, count in final_counts.items():
        print(f"  {name}: {count}")
    plan["final_counts"] = final_counts
    plan["orphans_after"] = final_orphans
    return plan


def _print_plan(plan: dict[str, Any], replace_existing: bool) -> None:
    info: DatabaseInfo = plan["database"]
    print(f"Dataset: {DATASET_MARKER}")
    print(f"Mode: {plan['mode']} (replace_existing={str(replace_existing).lower()})")
    print(f"Environment: {plan['environment']}")
    print(f"Database: {info.name} (user={info.user}, server={info.server_address})")
    print(f"Image base URL: {plan['public_base_url']}")
    print(
        f"Showcase campaigns: existing={len(plan['showcase_existing'])}, "
        f"missing={plan['showcase_missing']}"
    )
    for campaign in plan["showcase_existing"]:
        action = "delete and recreate" if replace_existing else "keep"
        print(f"  [{action}] {campaign.id} | {campaign.title}")
    if plan["legacy_rows"]:
        print("Explicit legacy cleanup candidates:")
        for campaign in plan["legacy_rows"]:
            print(f"  [requires confirmation] {campaign.id} | {campaign.title}")
    print("Dependent rows for inspected campaign IDs:")
    for name, count in plan["dependency_counts"].items():
        print(f"  {name}: {count}")
    assets = plan["asset_plan"]
    print(f"Assets: source={assets['source']}, present={assets['present']}, missing={assets['missing']}")
    print("Existing global orphan counts:")
    for name, count in plan["orphans_before"].items():
        print(f"  {name}: {count}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="show the plan without changes (default)")
    mode.add_argument("--apply", action="store_true", help="apply the import in one database transaction")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="replace only campaigns carrying deterministic demo_showcase_v1 UUIDs",
    )
    parser.add_argument(
        "--legacy-campaign-ids-file",
        type=Path,
        help="explicit JSON campaign ID list; never loaded automatically",
    )
    parser.add_argument(
        "--confirm-legacy-cleanup",
        action="store_true",
        help="allow deletion of IDs from --legacy-campaign-ids-file during apply",
    )
    parser.add_argument(
        "--public-base-url",
        help="public backend/site origin used for persistent /uploads URLs",
    )
    return parser


async def async_main() -> None:
    args = build_parser().parse_args()
    legacy_ids = load_legacy_ids(args.legacy_campaign_ids_file)
    await run(
        apply=args.apply,
        replace_existing=args.replace_existing,
        app_env=settings.app_env,
        password=os.getenv("DEMO_USERS_PASSWORD"),
        public_base_url=args.public_base_url,
        legacy_ids=legacy_ids,
        confirm_legacy_cleanup=args.confirm_legacy_cleanup,
    )


def main() -> None:
    try:
        asyncio.run(async_main())
    except SafetyError as exc:
        raise SystemExit(f"SAFETY STOP: {exc}") from exc


if __name__ == "__main__":
    main()
