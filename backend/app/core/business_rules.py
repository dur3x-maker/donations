from decimal import Decimal

from app.models.campaign import Campaign, CampaignStatus

MIN_DONATION_AMOUNT = Decimal("100")
UNFINISHED_CAMPAIGN_STATUSES = (
    CampaignStatus.active,
    CampaignStatus.pending_review,
    CampaignStatus.revision_required,
    CampaignStatus.goal_reached,
    CampaignStatus.awaiting_report,
)

CAMPAIGN_CLOSED_FOR_DONATIONS_MESSAGE = "Сбор уже достиг цели и больше не принимает поддержку."
MIN_DONATION_AMOUNT_MESSAGE = "Минимальная сумма поддержки — 100 ₽."
UNFINISHED_CAMPAIGN_MESSAGE = "У вас уже есть незавершенный сбор. Завершите текущую историю перед созданием новой."


def can_accept_donation(campaign: Campaign) -> bool:
    return campaign.status == CampaignStatus.active and campaign.current_amount < campaign.target_amount
