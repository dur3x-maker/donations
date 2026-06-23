from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_moderator
from app.db.session import get_session
from app.models.report import Report
from app.models.suspicious_flag import SuspiciousFlag
from app.models.user import User
from app.schemas.campaign import CampaignDetail
from app.schemas.moderation import ReportOut, SuspiciousFlagOut
from app.services.campaign_service import get_campaign_detail, set_campaign_active

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/reports", response_model=list[ReportOut])
async def moderation_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
) -> list[ReportOut]:
    reports = await session.scalars(
        select(Report).order_by(desc(Report.created_at)).offset((page - 1) * page_size).limit(page_size)
    )
    return [
        ReportOut(
            id=report.id,
            reporter_user_id=report.reporter_user_id,
            campaign_id=report.campaign_id,
            reason=report.reason,
            details=report.details,
            status=report.status.value,
            created_at=report.created_at,
        )
        for report in reports
    ]


@router.get("/flags", response_model=list[SuspiciousFlagOut])
async def moderation_flags(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
) -> list[SuspiciousFlagOut]:
    flags = await session.scalars(
        select(SuspiciousFlag).order_by(desc(SuspiciousFlag.created_at)).offset((page - 1) * page_size).limit(page_size)
    )
    return [
        SuspiciousFlagOut(
            id=flag.id,
            type=flag.type,
            user_id=flag.user_id,
            campaign_id=flag.campaign_id,
            metadata_json=flag.metadata_json,
            created_at=flag.created_at,
            resolved_at=flag.resolved_at,
        )
        for flag in flags
    ]


@router.post("/campaigns/{campaign_id}/hide", response_model=CampaignDetail)
async def hide_campaign(
    campaign_id: UUID,
    _: User = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    await set_campaign_active(session, campaign_id, False)
    return await get_campaign_detail(session, campaign_id)


@router.post("/campaigns/{campaign_id}/restore", response_model=CampaignDetail)
async def restore_campaign(
    campaign_id: UUID,
    _: User = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    await set_campaign_active(session, campaign_id, True)
    return await get_campaign_detail(session, campaign_id)
