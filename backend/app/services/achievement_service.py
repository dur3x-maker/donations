from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.campaign import Campaign
from app.models.contribution import Contribution, ContributionStatus
from app.models.notification import NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.schemas.user import ProfileImpactOut, UserAchievementOut
from app.services.level_service import current_level_for, next_level_for, progress_percent_for
from app.services.notification_service import create_notification


@dataclass(frozen=True)
class AchievementDefinition:
    code: str
    title: str
    description: str


ACHIEVEMENTS = (
    AchievementDefinition("FIRST_CONTRIBUTION", "Первый вклад", "Вы сделали свой первый вклад в сообщество."),
    AchievementDefinition("FIVE_CONTRIBUTIONS", "Пять шагов добра", "Поддержано 5 историй."),
    AchievementDefinition("TEN_SUPPORTED_PEOPLE", "Помогать людям", "Вы поддержали 10 историй."),
    AchievementDefinition("FOLLOWED_TO_COMPLETION", "До самого финала", "Вы поддержали историю и дождались ее завершения."),
    AchievementDefinition("PATRON_CIRCLE", "Круг меценатов", "Вы достигли уровня Меценат и стали частью Круга меценатов."),
)
ACHIEVEMENTS_BY_CODE = {definition.code: definition for definition in ACHIEVEMENTS}
PATRON_THRESHOLD = 50


async def get_profile_impact(session: AsyncSession, user_id: UUID) -> ProfileImpactOut:
    confirmed_count, supported_count, total_amount = await _impact_counts(session, user_id)
    user = await session.get(User, user_id)
    current_level = current_level_for(confirmed_count)
    next_level = next_level_for(confirmed_count)
    return ProfileImpactOut(
        current_level=current_level.title if current_level else None,
        next_level=next_level.title if next_level else None,
        confirmed_contributions_count=confirmed_count,
        supported_campaigns_count=supported_count,
        completed_supported_campaigns=await _supported_campaigns_count(session, user_id, completed=True),
        active_supported_campaigns=await _supported_campaigns_count(session, user_id, completed=False, reached=True),
        fundraising_supported_campaigns=await _supported_campaigns_count(session, user_id, completed=False, reached=False),
        total_supported_amount=str(total_amount),
        progress_percent=progress_percent_for(confirmed_count),
        is_patron=confirmed_count >= PATRON_THRESHOLD,
        patron_since=user.patron_since if user else None,
    )


async def get_user_achievements(session: AsyncSession, user_id: UUID) -> list[UserAchievementOut]:
    rows = await session.scalars(
        select(UserAchievement)
        .where(UserAchievement.user_id == user_id)
        .order_by(UserAchievement.unlocked_at)
    )
    result = []
    for achievement in rows:
        definition = ACHIEVEMENTS_BY_CODE.get(achievement.achievement_code)
        if definition is None:
            continue
        result.append(
            UserAchievementOut(
                code=definition.code,
                title=definition.title,
                description=definition.description,
                unlocked_at=achievement.unlocked_at,
            )
        )
    return result


async def evaluate_user_achievements(session: AsyncSession, user_id: UUID | None) -> list[UserAchievement]:
    if user_id is None:
        return []

    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
    )
    confirmed_count, supported_count, _ = await _impact_counts(session, user_id)
    followed_to_completion = await _has_followed_to_completion(session, user_id)
    unlocked_codes = set(
        await session.scalars(select(UserAchievement.achievement_code).where(UserAchievement.user_id == user_id))
    )

    candidates = []
    if confirmed_count >= 1:
        candidates.append("FIRST_CONTRIBUTION")
    if confirmed_count >= 5:
        candidates.append("FIVE_CONTRIBUTIONS")
    if supported_count >= 10:
        candidates.append("TEN_SUPPORTED_PEOPLE")
    if followed_to_completion:
        candidates.append("FOLLOWED_TO_COMPLETION")
    if confirmed_count >= PATRON_THRESHOLD:
        candidates.append("PATRON_CIRCLE")

    if confirmed_count >= PATRON_THRESHOLD and user is not None and user.patron_since is None:
        user.patron_since = utcnow()
        await create_notification(
            session,
            user_id,
            NotificationType.patron_unlocked,
            "Вы вошли в Круг меценатов",
            "Спасибо за вклад в развитие сообщества.",
            action_url="/community/patrons",
        )

    created = []
    for code in candidates:
        if code in unlocked_codes:
            continue
        definition = ACHIEVEMENTS_BY_CODE[code]
        achievement = UserAchievement(user_id=user_id, achievement_code=code)
        session.add(achievement)
        await session.flush()
        await create_notification(
            session,
            user_id,
            NotificationType.achievement_unlocked,
            "Новое достижение",
            f"Вы получили достижение «{definition.title}».",
            action_url="/community/patrons" if code == "PATRON_CIRCLE" else "/profile#achievements",
        )
        created.append(achievement)
    return created


async def _impact_counts(session: AsyncSession, user_id: UUID) -> tuple[int, int, Decimal]:
    valid_conditions = (
        Contribution.user_id == user_id,
        Contribution.status == ContributionStatus.confirmed,
        Payment.status == PaymentStatus.succeeded,
        Contribution.amount > 0,
        Campaign.owner_id != user_id,
    )
    confirmed_count, supported_count, total_amount = (
        await session.execute(
            select(
                func.count(Contribution.id),
                func.count(distinct(Contribution.campaign_id)),
                func.coalesce(func.sum(Contribution.amount), 0),
            )
            .select_from(Contribution)
            .join(Payment, Payment.contribution_id == Contribution.id)
            .join(Campaign, Campaign.id == Contribution.campaign_id)
            .where(*valid_conditions)
        )
    ).one()
    return int(confirmed_count or 0), int(supported_count or 0), Decimal(total_amount or 0)


async def _has_followed_to_completion(session: AsyncSession, user_id: UUID) -> bool:
    completed_campaign_id = await session.scalar(
        select(Contribution.campaign_id)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .join(Campaign, Campaign.id == Contribution.campaign_id)
        .where(
            Contribution.user_id == user_id,
            Contribution.status == ContributionStatus.confirmed,
            Payment.status == PaymentStatus.succeeded,
            Contribution.amount > 0,
            Campaign.owner_id != user_id,
            Campaign.has_completion_report.is_(True),
        )
        .limit(1)
    )
    return completed_campaign_id is not None


async def _supported_campaigns_count(
    session: AsyncSession,
    user_id: UUID,
    *,
    completed: bool,
    reached: bool | None = None,
) -> int:
    conditions = [
        Contribution.user_id == user_id,
        Contribution.status == ContributionStatus.confirmed,
        Payment.status == PaymentStatus.succeeded,
        Contribution.amount > 0,
        Campaign.owner_id != user_id,
        Campaign.has_completion_report.is_(completed),
    ]
    if reached is True:
        conditions.append(Campaign.current_amount >= Campaign.target_amount)
    if reached is False:
        conditions.append(Campaign.current_amount < Campaign.target_amount)

    count = await session.scalar(
        select(func.count(distinct(Contribution.campaign_id)))
        .select_from(Contribution)
        .join(Payment, Payment.contribution_id == Contribution.id)
        .join(Campaign, Campaign.id == Contribution.campaign_id)
        .where(*conditions)
    )
    return int(count or 0)
