from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.campaign import CampaignListItem
from app.schemas.platform import PlatformStatsOut
from app.services.campaign_service import campaign_to_list_item
from app.services.featured_campaign_service import get_featured_campaign
from app.services.platform_stats_service import get_platform_stats

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/featured-campaign", response_model=CampaignListItem | None)
async def featured_campaign(session: AsyncSession = Depends(get_session)) -> CampaignListItem | None:
    campaign = await get_featured_campaign(session)
    return await campaign_to_list_item(session, campaign) if campaign else None


@router.get("/stats", response_model=PlatformStatsOut)
async def platform_stats(session: AsyncSession = Depends(get_session)) -> PlatformStatsOut:
    return await get_platform_stats(session)
