from collections import defaultdict, deque
from time import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.moderation import ReportCreateIn
from app.services.campaign_service import get_campaign_or_404
from app.services.moderation_alert_service import send_moderation_alert
from app.services.suspicious_flag_service import create_suspicious_flag

REPORT_LIMIT_PER_HOUR = 5
_report_hits: dict[str, deque[float]] = defaultdict(deque)


async def create_report(
    session: AsyncSession,
    campaign_id: UUID,
    payload: ReportCreateIn,
    reporter: User | None,
    client_ip: str,
) -> Report:
    _check_report_rate(reporter.id if reporter else None, client_ip)
    await get_campaign_or_404(session, campaign_id, include_inactive=True)

    report = Report(
        reporter_user_id=reporter.id if reporter else None,
        campaign_id=campaign_id,
        reason=payload.reason,
        details=payload.details,
        status=ReportStatus.pending,
    )
    session.add(report)
    await session.flush()

    pending_count = await session.scalar(
        select(func.count(Report.id)).where(Report.campaign_id == campaign_id, Report.status == ReportStatus.pending)
    )
    if int(pending_count or 0) >= 3:
        await create_suspicious_flag(
            session,
            "repeated_reports",
            campaign_id=campaign_id,
            metadata_json={"pending_reports": int(pending_count or 0)},
        )
        await send_moderation_alert("campaign_reported_many_times", {"campaign_id": str(campaign_id), "pending_reports": int(pending_count or 0)})

    await session.commit()
    await session.refresh(report)
    return report


def _check_report_rate(user_id: UUID | None, client_ip: str) -> None:
    key = f"user:{user_id}" if user_id else f"ip:{client_ip}"
    now = time()
    hits = _report_hits[key]
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(hits) >= REPORT_LIMIT_PER_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Слишком много жалоб. Попробуйте позже.")
    hits.append(now)
