from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import CampaignStatus
from app.models.user import User
from app.schemas.withdrawal import WithdrawalInfoOut
from app.services.campaign_service import get_campaign_or_404


WITHDRAWAL_STATUSES = {
    CampaignStatus.goal_reached,
    CampaignStatus.awaiting_report,
    CampaignStatus.completed,
}


async def get_withdrawal_info(
    session: AsyncSession,
    campaign_id: UUID,
    current_user: User,
) -> WithdrawalInfoOut:
    campaign = await get_campaign_or_404(session, campaign_id)
    if campaign.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Withdrawal information is available only to the campaign author",
        )

    return WithdrawalInfoOut(
        campaign_id=campaign.id,
        available=(
            campaign.current_amount >= campaign.target_amount
            and campaign.status in WITHDRAWAL_STATUSES
        ),
    )
