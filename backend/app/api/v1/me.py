from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.notification import NotificationOut, NotificationsReadIn, NotificationsReadOut
from app.schemas.user import ContributionProgressOut, LinkAnonymousContributions, OwnerDashboardOut, ProfileImpactOut, ProfileSummaryOut, UserAchievementOut, UserOut
from app.services.achievement_service import get_profile_impact, get_user_achievements
from app.services.notification_service import get_notifications, mark_notification_read, mark_notifications_read
from app.services.user_service import (
    REQUIRED_CONFIRMED_DONATIONS,
    can_create_campaign,
    get_confirmed_donation_count,
    get_owner_dashboard,
    get_profile_summary,
    link_anonymous_contributions,
    has_unfinished_campaign,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
async def me(current_user: User = Depends(require_current_user)) -> User:
    return current_user


@router.post("/link-anonymous-contributions")
async def link_anonymous(
    payload: LinkAnonymousContributions,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    linked_count = await link_anonymous_contributions(session, current_user, payload.anonymous_token)
    return {"linked_count": linked_count}


@router.get("/contribution-progress", response_model=ContributionProgressOut)
async def contribution_progress(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> ContributionProgressOut:
    count = await get_confirmed_donation_count(session, current_user.id)
    unfinished = await has_unfinished_campaign(session, current_user.id)
    return ContributionProgressOut(
        confirmed_contributions_count=count,
        required_contributions_count=REQUIRED_CONFIRMED_DONATIONS,
        can_create_campaign=await can_create_campaign(session, current_user.id),
        has_unfinished_campaign=unfinished,
    )


@router.get("/dashboard", response_model=OwnerDashboardOut)
async def owner_dashboard(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> OwnerDashboardOut:
    return await get_owner_dashboard(session, current_user.id)


@router.get("/profile-summary", response_model=ProfileSummaryOut)
async def profile_summary(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileSummaryOut:
    return await get_profile_summary(session, current_user.id)


@router.get("/profile-impact", response_model=ProfileImpactOut)
async def profile_impact(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileImpactOut:
    return await get_profile_impact(session, current_user.id)


@router.get("/achievements", response_model=list[UserAchievementOut])
async def my_achievements(
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[UserAchievementOut]:
    return await get_user_achievements(session, current_user.id)


@router.get("/notifications", response_model=list[NotificationOut])
async def my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationOut]:
    return await get_notifications(session, current_user.id, page=page, page_size=page_size)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def read_my_notification(
    notification_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationOut:
    notification = await mark_notification_read(session, notification_id, current_user.id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/notifications/read", response_model=NotificationsReadOut)
async def read_my_notifications(
    payload: NotificationsReadIn,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationsReadOut:
    updated_count = await mark_notifications_read(session, payload.notification_ids, current_user.id)
    return NotificationsReadOut(updated_count=updated_count)
