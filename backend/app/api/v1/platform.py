from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.platform import PlatformStatsOut
from app.services.platform_stats_service import get_platform_stats

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/stats", response_model=PlatformStatsOut)
async def platform_stats(session: AsyncSession = Depends(get_session)) -> PlatformStatsOut:
    return await get_platform_stats(session)
