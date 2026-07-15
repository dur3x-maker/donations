import secrets
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_completion_report import CampaignCompletionPhoto, CampaignCompletionReport
from app.models.campaign_update import CampaignUpdate, CampaignUpdatePhoto
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.models.user import User
from scripts.import_demo_showcase import (
    DATASET_MARKER,
    DEFAULT_ASSET_ROOT,
    SafetyError,
    apply_showcase,
    campaign_ids,
    load_dataset,
    stable_uuid,
    sync_assets,
    validate_environment,
)


DEMO_PASSWORD = secrets.token_urlsafe(24)
PUBLIC_BASE_URL = "http://test"


def test_showcase_contract_and_assets(tmp_path: Path):
    data = load_dataset()

    assert len(data["authors"]) == 8
    assert sum("completion_report" not in item for item in data["campaigns"]) == 8
    assert sum("completion_report" in item for item in data["campaigns"]) == 3

    rollback = sync_assets(data, DEFAULT_ASSET_ROOT, tmp_path)
    copied = list((tmp_path / DATASET_MARKER).glob("*.jpg"))
    assert len(copied) == 11
    assert all(path.stat().st_size > 50_000 for path in copied)

    rollback.restore()
    assert not list((tmp_path / DATASET_MARKER).glob("*.jpg"))


def test_showcase_refuses_production_environment():
    with pytest.raises(SafetyError):
        validate_environment("production", "donations")
    with pytest.raises(SafetyError):
        validate_environment("staging", "donations_prod")


async def test_showcase_apply_is_idempotent_and_replace_preserves_real_data(session_factory):
    data = load_dataset()
    async with session_factory() as session:
        real_user = User(
            email="real-user@example.com",
            username="real_user",
            password_hash=hash_password("real-password"),
        )
        session.add(real_user)
        await session.flush()
        real_campaign = Campaign(
            owner_id=real_user.id,
            title="Real user campaign",
            description="This campaign must survive every showcase operation.",
            target_amount=10000,
            current_amount=0,
            category="other",
            status=CampaignStatus.active,
        )
        session.add(real_campaign)
        await session.commit()
        real_user_id = real_user.id
        real_campaign_id = real_campaign.id

    async with session_factory() as session:
        async with session.begin():
            await apply_showcase(
                session,
                data,
                DEMO_PASSWORD,
                PUBLIC_BASE_URL,
                replace_existing=False,
                legacy_ids=[],
            )

    first_counts = await _showcase_counts(session_factory, data)
    assert first_counts == {
        "campaigns": 11,
        "completion_photos": 3,
        "completion_reports": 3,
        "contributions": 115,
        "payments": 115,
        "update_photos": 11,
        "updates": 22,
        "users": 8,
    }

    async with session_factory() as session:
        async with session.begin():
            await apply_showcase(
                session,
                data,
                DEMO_PASSWORD,
                PUBLIC_BASE_URL,
                replace_existing=False,
                legacy_ids=[],
            )
    assert await _showcase_counts(session_factory, data) == first_counts

    async with session_factory() as session:
        campaign = await session.get(Campaign, stable_uuid("campaign", "rehab_after_injury"))
        campaign.title = "Temporary demo edit"
        await session.commit()

    async with session_factory() as session:
        async with session.begin():
            await apply_showcase(
                session,
                data,
                DEMO_PASSWORD,
                PUBLIC_BASE_URL,
                replace_existing=False,
                legacy_ids=[],
            )
    async with session_factory() as session:
        preserved = await session.get(Campaign, stable_uuid("campaign", "rehab_after_injury"))
        assert preserved.title == "Temporary demo edit"

    async with session_factory() as session:
        async with session.begin():
            await apply_showcase(
                session,
                data,
                DEMO_PASSWORD,
                PUBLIC_BASE_URL,
                replace_existing=True,
                legacy_ids=[],
            )
    assert await _showcase_counts(session_factory, data) == first_counts

    async with session_factory() as session:
        assert await session.get(User, real_user_id) is not None
        assert await session.get(Campaign, real_campaign_id) is not None
        restored = await session.get(Campaign, stable_uuid("campaign", "rehab_after_injury"))
        assert restored.title == "Вернуться к самостоятельным шагам после травмы"


async def test_demo_authors_can_login_and_only_edit_active_campaigns(client, session_factory):
    data = load_dataset()
    async with session_factory() as session:
        async with session.begin():
            await apply_showcase(
                session,
                data,
                DEMO_PASSWORD,
                PUBLIC_BASE_URL,
                replace_existing=False,
                legacy_ids=[],
            )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "elena.krivtsova@demo.digitalgardens.example", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    active_id = stable_uuid("campaign", "rehab_after_injury")
    completed_id = stable_uuid("campaign", "community_courtyard_garden")
    active_edit = await client.patch(
        f"/api/v1/campaigns/{active_id}",
        json={"title": "Обновлённый заголовок демо-истории"},
        headers=headers,
    )
    completed_edit = await client.patch(
        f"/api/v1/campaigns/{completed_id}",
        json={"title": "Этот заголовок не должен сохраниться"},
        headers=headers,
    )

    assert active_edit.status_code == 200
    assert completed_edit.status_code == 409
    assert len((await client.get("/api/v1/campaigns")).json()) == 8
    assert len((await client.get("/api/v1/campaigns/completed")).json()) == 3


async def _showcase_counts(session_factory, data) -> dict[str, int]:
    ids = campaign_ids(data)
    user_ids = [stable_uuid("user", item["key"]) for item in data["authors"]]
    async with session_factory() as session:
        return {
            "campaigns": int(
                await session.scalar(select(func.count()).select_from(Campaign).where(Campaign.id.in_(ids))) or 0
            ),
            "completion_photos": int(
                await session.scalar(
                    select(func.count())
                    .select_from(CampaignCompletionPhoto)
                    .join(CampaignCompletionReport)
                    .where(CampaignCompletionReport.campaign_id.in_(ids))
                )
                or 0
            ),
            "completion_reports": int(
                await session.scalar(
                    select(func.count())
                    .select_from(CampaignCompletionReport)
                    .where(CampaignCompletionReport.campaign_id.in_(ids))
                )
                or 0
            ),
            "contributions": int(
                await session.scalar(
                    select(func.count()).select_from(Contribution).where(Contribution.campaign_id.in_(ids))
                )
                or 0
            ),
            "payments": int(
                await session.scalar(
                    select(func.count())
                    .select_from(Payment)
                    .join(Contribution)
                    .where(Contribution.campaign_id.in_(ids))
                )
                or 0
            ),
            "update_photos": int(
                await session.scalar(
                    select(func.count())
                    .select_from(CampaignUpdatePhoto)
                    .join(CampaignUpdate)
                    .where(CampaignUpdate.campaign_id.in_(ids))
                )
                or 0
            ),
            "updates": int(
                await session.scalar(
                    select(func.count()).select_from(CampaignUpdate).where(CampaignUpdate.campaign_id.in_(ids))
                )
                or 0
            ),
            "users": int(
                await session.scalar(select(func.count()).select_from(User).where(User.id.in_(user_ids))) or 0
            ),
        }
