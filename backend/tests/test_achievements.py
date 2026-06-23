import pytest
from sqlalchemy import select

from app.models.notification import Notification, NotificationType
from app.models.user_achievement import UserAchievement
from app.services.achievement_service import evaluate_user_achievements
from tests.helpers import count_rows


@pytest.mark.parametrize(
    ("count", "expected_codes"),
    [
        (1, {"FIRST_CONTRIBUTION"}),
        (5, {"FIRST_CONTRIBUTION", "FIVE_CONTRIBUTIONS"}),
        (50, {"FIRST_CONTRIBUTION", "FIVE_CONTRIBUTIONS", "PATRON_CIRCLE"}),
    ],
)
async def test_threshold_achievements_are_created(
    db_session, user_factory, campaign_factory, contribution_factory, count, expected_codes
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=1000000)
    await contribution_factory(campaign, user=donor, count=count)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()
    achievements = set(
        await db_session.scalars(
            UserAchievement.__table__.select()
            .with_only_columns(UserAchievement.achievement_code)
            .where(UserAchievement.user_id == donor.id)
        )
    )
    assert expected_codes <= achievements


async def test_achievement_evaluation_and_notifications_are_idempotent(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner)
    await contribution_factory(campaign, user=donor)

    await evaluate_user_achievements(db_session, donor.id)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()

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
    notification = await db_session.scalar(
        select(Notification).where(
            Notification.user_id == donor.id,
            Notification.type == NotificationType.achievement_unlocked,
        )
    )
    assert notification.action_url == "/profile#achievements"


async def test_patron_circle_notifications_open_community(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=1000000)
    await contribution_factory(campaign, user=donor, count=50)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()

    notifications = list(
        await db_session.scalars(
            select(Notification).where(
                Notification.user_id == donor.id,
                Notification.type.in_(
                    (NotificationType.achievement_unlocked, NotificationType.patron_unlocked)
                ),
            )
        )
    )
    patron_notifications = [
        item for item in notifications
        if item.type == NotificationType.patron_unlocked or "Круг" in item.body
    ]
    assert patron_notifications
    assert {item.action_url for item in patron_notifications} == {"/community/patrons"}
