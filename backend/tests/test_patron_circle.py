import pytest

from app.db.base import utcnow
from app.models.notification import Notification, NotificationType
from app.models.user_achievement import UserAchievement
from app.services.achievement_service import evaluate_user_achievements
from tests.helpers import count_rows


@pytest.mark.parametrize(("count", "is_patron"), [(49, False), (50, True), (51, True)])
async def test_patron_boundary(
    db_session, user_factory, campaign_factory, contribution_factory, count, is_patron
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=1000000)
    await contribution_factory(campaign, user=donor, count=count)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()
    await db_session.refresh(donor)

    assert (donor.patron_since is not None) is is_patron
    assert await count_rows(
        db_session,
        UserAchievement,
        UserAchievement.user_id == donor.id,
        UserAchievement.achievement_code == "PATRON_CIRCLE",
    ) == int(is_patron)
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor.id,
        Notification.type == NotificationType.patron_unlocked,
    ) == int(is_patron)


async def test_patron_notifications_do_not_duplicate_at_51(
    db_session, user_factory, campaign_factory, contribution_factory
):
    owner = await user_factory()
    donor = await user_factory()
    campaign = await campaign_factory(owner, target_amount=1000000)
    await contribution_factory(campaign, user=donor, count=50)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()
    await contribution_factory(campaign, user=donor, count=1)
    await evaluate_user_achievements(db_session, donor.id)
    await db_session.commit()
    assert await count_rows(
        db_session,
        Notification,
        Notification.user_id == donor.id,
        Notification.type == NotificationType.patron_unlocked,
    ) == 1


async def test_patron_circle_shows_support_impact_without_ranking(
    client, db_session, user_factory, campaign_factory, contribution_factory
):
    donor = await user_factory(username="steady_helper")
    campaigns = []
    for index in range(4):
        owner = await user_factory()
        campaigns.append(await campaign_factory(owner, title=f"Supported story {index}", target_amount=100000))

    await contribution_factory(campaigns[0], user=donor, count=47, amount=100)
    for campaign in campaigns[1:]:
        await contribution_factory(campaign, user=donor, amount=100)
    donor.patron_since = utcnow()
    await db_session.commit()

    response = await client.get("/api/v1/community/patrons")

    assert response.status_code == 200
    assert len(response.json()) == 1
    patron = response.json()[0]
    assert patron["username"] == "steady_helper"
    assert patron["confirmed_contributions_count"] == 50
    assert patron["supported_campaigns_count"] == 4
    assert patron["total_donated_amount"] == "5000.00"
    assert len(patron["recent_supported_campaigns"]) == 3
