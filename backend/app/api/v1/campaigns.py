from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_rate_limit, get_client_ip, get_optional_current_user, require_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.campaign import CampaignCompletionReportCreate, CampaignCompletionReportOut, CampaignCreate, CampaignDetail, CampaignListItem, CampaignUpdate, CampaignUpdateCreate, CampaignUpdateOut, CompletedCampaignListItem
from app.schemas.contribution import DonateIn, DonateOut, RecentDonationsPageOut
from app.schemas.moderation import ReportCreateIn, ReportOut
from app.schemas.subscription import CampaignSubscriptionOut
from app.schemas.withdrawal import WithdrawalInfoOut
from app.services.campaign_service import (
    create_campaign,
    delete_campaign,
    get_campaign_detail,
    get_campaigns,
    get_completed_campaigns,
    update_campaign,
)
from app.services.campaign_update_service import create_campaign_update, get_campaign_update, get_campaign_updates
from app.services.completion_report_service import create_completion_report, get_completion_report
from app.services.contribution_service import donate, get_recent_donations
from app.services.report_service import create_report
from app.services.follow_up_service import get_campaign_subscription, set_campaign_subscription
from app.services.withdrawal_service import get_withdrawal_info
from app.services.admin_event_service import AdminEventService, get_admin_event_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignListItem])
async def list_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    sort: str = Query(default="newest", pattern="^(newest|oldest|most_funded|least_funded)$"),
    q: str | None = Query(default=None, max_length=160),
    session: AsyncSession = Depends(get_session),
) -> list[CampaignListItem]:
    return await get_campaigns(session, page=page, page_size=page_size, sort=sort, query=q)


@router.get("/completed", response_model=list[CompletedCampaignListItem])
async def list_completed_campaigns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    q: str | None = Query(default=None, max_length=160),
    session: AsyncSession = Depends(get_session),
) -> list[CompletedCampaignListItem]:
    return await get_completed_campaigns(session, page=page, page_size=page_size, query=q)


@router.post("", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
async def create_campaign_endpoint(
    payload: CampaignCreate,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
    admin_events: AdminEventService = Depends(get_admin_event_service),
) -> CampaignDetail:
    campaign = await create_campaign(session, current_user, payload, admin_events)
    return await get_campaign_detail(session, campaign.id)


@router.get("/{campaign_id}/recent-donations", response_model=RecentDonationsPageOut)
async def recent_donations(
    campaign_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=3, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> RecentDonationsPageOut:
    return await get_recent_donations(session, campaign_id, offset=offset, limit=limit)


@router.get("/{campaign_id}/withdrawal-info", response_model=WithdrawalInfoOut)
async def withdrawal_info(
    campaign_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> WithdrawalInfoOut:
    return await get_withdrawal_info(session, campaign_id, current_user)


@router.get("/{campaign_id}/subscription", response_model=CampaignSubscriptionOut)
async def campaign_subscription(
    campaign_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignSubscriptionOut:
    await get_campaign_detail(session, campaign_id)
    subscription = await get_campaign_subscription(session, current_user.id, campaign_id)
    return CampaignSubscriptionOut(
        campaign_id=campaign_id,
        is_subscribed=bool(subscription and subscription.is_active and not subscription.muted),
    )


@router.post("/{campaign_id}/subscription", response_model=CampaignSubscriptionOut)
async def subscribe_to_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignSubscriptionOut:
    await get_campaign_detail(session, campaign_id)
    subscription = await set_campaign_subscription(session, current_user.id, campaign_id, is_active=True)
    return CampaignSubscriptionOut(campaign_id=campaign_id, is_subscribed=subscription.is_active)


@router.delete("/{campaign_id}/subscription", response_model=CampaignSubscriptionOut)
async def unsubscribe_from_campaign(
    campaign_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignSubscriptionOut:
    await get_campaign_detail(session, campaign_id)
    await set_campaign_subscription(session, current_user.id, campaign_id, is_active=False)
    return CampaignSubscriptionOut(campaign_id=campaign_id, is_subscribed=False)


@router.post("/{campaign_id}/updates", response_model=CampaignUpdateOut, status_code=status.HTTP_201_CREATED)
async def create_update(
    campaign_id: UUID,
    payload: CampaignUpdateCreate,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignUpdateOut:
    return await create_campaign_update(session, campaign_id, current_user, payload)


@router.get("/{campaign_id}/updates", response_model=list[CampaignUpdateOut])
async def list_updates(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[CampaignUpdateOut]:
    return await get_campaign_updates(session, campaign_id)


@router.get("/{campaign_id}/updates/{update_id}", response_model=CampaignUpdateOut)
async def update_detail(
    campaign_id: UUID,
    update_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CampaignUpdateOut:
    return await get_campaign_update(session, campaign_id, update_id)


@router.post("/{campaign_id}/completion-report", response_model=CampaignCompletionReportOut, status_code=status.HTTP_201_CREATED)
async def create_completion_report_endpoint(
    campaign_id: UUID,
    payload: CampaignCompletionReportCreate,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignCompletionReportOut:
    return await create_completion_report(session, campaign_id, current_user, payload)


@router.get("/{campaign_id}/completion-report", response_model=CampaignCompletionReportOut)
async def completion_report_detail(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CampaignCompletionReportOut:
    return await get_completion_report(session, campaign_id)


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def campaign_detail(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    return await get_campaign_detail(session, campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignDetail)
async def update_campaign_endpoint(
    campaign_id: UUID,
    payload: CampaignUpdate,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    campaign = await update_campaign(session, campaign_id, current_user, payload)
    return await get_campaign_detail(session, campaign.id)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_campaign(session, campaign_id, current_user)


@router.post("/{campaign_id}/donate", response_model=DonateOut)
async def donate_endpoint(
    campaign_id: UUID,
    payload: DonateIn,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_session),
) -> DonateOut:
    actor = str(current_user.id) if current_user else get_client_ip(request)
    enforce_rate_limit(f"donate:{actor}", 30, 60, "Слишком много попыток поддержки")
    payment, anonymous_token, subscription_created = await donate(session, campaign_id, payload, current_user)
    return DonateOut(
        payment_id=payment.id,
        status=payment.status.value,
        anonymous_token=anonymous_token,
        subscription_created=subscription_created,
    )


@router.post("/{campaign_id}/report", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def report_campaign(
    campaign_id: UUID,
    payload: ReportCreateIn,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_session),
    admin_events: AdminEventService = Depends(get_admin_event_service),
) -> ReportOut:
    actor = str(current_user.id) if current_user else get_client_ip(request)
    enforce_rate_limit(f"report:{actor}", 5, 3600, "Слишком много жалоб. Попробуйте позже.")
    report = await create_report(
        session,
        campaign_id,
        payload,
        current_user,
        request.client.host if request.client else "unknown",
        admin_events,
    )
    return ReportOut(
        id=report.id,
        reporter_user_id=report.reporter_user_id,
        campaign_id=report.campaign_id,
        reason=report.reason,
        details=report.details,
        status=report.status.value,
        created_at=report.created_at,
    )
