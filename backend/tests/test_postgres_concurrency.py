import asyncio
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.activity import Activity, ActivityType
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_completion_report import CampaignCompletionPhoto, CampaignCompletionReport
from app.models.campaign_subscription import CampaignSubscription
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.schemas.campaign import CampaignCompletionReportCreate, CampaignCreate
from app.services.achievement_service import evaluate_user_achievements
from app.services.campaign_service import create_campaign
from app.services.completion_report_service import create_completion_report
from app.services.payment_service import confirm_payment
from tests.helpers import count_rows


async def test_ten_parallel_confirmations_of_one_payment_are_idempotent(
    db_session, session_factory, user_factory, campaign_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("10000"))
    contribution = Contribution(
        campaign_id=campaign.id,
        user_id=donor.id,
        amount=Decimal("100"),
        status=ContributionStatus.pending,
    )
    db_session.add(contribution)
    await db_session.flush()
    payment = Payment(
        contribution_id=contribution.id,
        provider="test",
        amount=contribution.amount,
        currency="RUB",
        status=PaymentStatus.pending,
    )
    db_session.add(payment)
    await db_session.commit()

    async def worker() -> bool:
        async with session_factory() as session:
            result = await confirm_payment(session, payment)
            await session.commit()
            return result

    results = await asyncio.gather(*(worker() for _ in range(10)))
    assert results.count(True) == 1
    assert results.count(False) == 9

    campaign_id = campaign.id
    donor_id = donor.id
    db_session.expire_all()
    refreshed_campaign = await db_session.get(Campaign, campaign_id)
    assert refreshed_campaign.current_amount == Decimal("100")
    assert await count_rows(db_session, CampaignSubscription) == 1
    assert await count_rows(
        db_session,
        UserAchievement,
        UserAchievement.user_id == donor_id,
        UserAchievement.achievement_code == "FIRST_CONTRIBUTION",
    ) == 1
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor_id,
        Notification.type == NotificationType.achievement_unlocked,
    ) == 1
    assert await count_rows(
        db_session,
        Activity,
        Activity.type == ActivityType.donation_made,
        Activity.campaign_id == campaign_id,
    ) == 1


async def test_parallel_first_achievement_evaluation_creates_one_record(
    db_session, session_factory, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    await contribution_factory(campaign, user=donor)

    async def worker() -> int:
        async with session_factory() as session:
            created = await evaluate_user_achievements(session, donor.id)
            await session.commit()
            return len(created)

    results = await asyncio.gather(*(worker() for _ in range(10)))
    assert sum(results) == 1
    assert await count_rows(
        db_session,
        UserAchievement,
        UserAchievement.user_id == donor.id,
        UserAchievement.achievement_code == "FIRST_CONTRIBUTION",
    ) == 1
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor.id,
        Notification.type == NotificationType.achievement_unlocked,
    ) == 1


async def test_parallel_patron_evaluation_at_fiftieth_contribution_is_idempotent(
    db_session, session_factory, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=Decimal("1000000"))
    await contribution_factory(campaign, user=donor, count=49)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()
    await contribution_factory(campaign, user=donor, count=1)

    async def worker() -> None:
        async with session_factory() as session:
            await evaluate_user_achievements(session, donor.id)
            await session.commit()

    await asyncio.gather(*(worker() for _ in range(10)))
    donor_id = donor.id
    db_session.expire_all()
    refreshed_donor = await db_session.get(User, donor_id)
    assert refreshed_donor.patron_since is not None
    assert await count_rows(
        db_session,
        UserAchievement,
        UserAchievement.user_id == donor_id,
        UserAchievement.achievement_code == "PATRON_CIRCLE",
    ) == 1
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor_id,
        Notification.type == NotificationType.patron_unlocked,
    ) == 1


async def test_two_parallel_completion_reports_create_one_report(
    db_session, session_factory, user_factory, campaign_factory
):
    owner = await user_factory()
    campaign = await campaign_factory(
        owner,
        target_amount=Decimal("100"),
        current_amount=Decimal("100"),
        status=CampaignStatus.awaiting_report,
    )
    payload = CampaignCompletionReportCreate(
        gratitude_text="Thank you for making this completion possible.",
        photos=["/uploads/result.jpg"],
    )

    async def worker() -> str:
        async with session_factory() as session:
            author = await session.get(User, owner.id)
            try:
                await create_completion_report(session, campaign.id, author, payload)
                return "created"
            except HTTPException as exc:
                await session.rollback()
                return f"rejected:{exc.status_code}"

    results = await asyncio.gather(worker(), worker())
    assert sorted(results) == ["created", "rejected:409"]
    assert await count_rows(db_session, CampaignCompletionReport) == 1
    assert await count_rows(db_session, CampaignCompletionPhoto) == 1
    campaign_id = campaign.id
    db_session.expire_all()
    refreshed_campaign = await db_session.get(Campaign, campaign_id)
    assert refreshed_campaign.status == CampaignStatus.completed
    assert refreshed_campaign.has_completion_report is True


async def test_parallel_campaign_creation_allows_only_one_unfinished_campaign(
    db_session, session_factory, user_factory, campaign_factory, contribution_factory
):
    author = await user_factory()
    foreign_owner = await user_factory()
    unlock_campaign = await campaign_factory(foreign_owner, target_amount=Decimal("100000"))
    await contribution_factory(unlock_campaign, user=author, count=5)
    payload = CampaignCreate(
        title="Concurrent campaign",
        description="A valid campaign description for a concurrent request.",
        target_amount=Decimal("5000"),
        category="medical",
    )

    async def worker() -> str:
        async with session_factory() as session:
            owner = await session.get(User, author.id)
            try:
                await create_campaign(session, owner, payload)
                return "created"
            except HTTPException as exc:
                await session.rollback()
                return f"rejected:{exc.status_code}"

    results = await asyncio.gather(worker(), worker())
    assert sorted(results) == ["created", "rejected:409"]
    assert await count_rows(
        db_session,
        Campaign,
        Campaign.owner_id == author.id,
        Campaign.is_active.is_(True),
        Campaign.status.in_(
            [
                CampaignStatus.active,
                CampaignStatus.goal_reached,
                CampaignStatus.awaiting_report,
            ]
        ),
    ) == 1


async def test_postgres_partial_unique_index_blocks_direct_second_campaign(
    db_session, user_factory, campaign_factory
):
    owner = await user_factory()
    await campaign_factory(owner)
    db_session.add(
        Campaign(
            owner_id=owner.id,
            title="Second unfinished campaign",
            description="This direct insert must be rejected by PostgreSQL.",
            target_amount=Decimal("1000"),
            current_amount=Decimal("0"),
            category="medical",
            is_active=True,
            status=CampaignStatus.active,
        )
    )
    try:
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
    else:
        raise AssertionError("PostgreSQL partial unique index was bypassed")
