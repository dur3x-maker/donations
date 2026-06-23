from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.business_rules import MIN_DONATION_AMOUNT
from app.schemas.common import AmountMixin


class DonateIn(AmountMixin):
    amount: Decimal = Field(ge=MIN_DONATION_AMOUNT, max_digits=12, decimal_places=2)
    anonymous_token: str | None = Field(default=None, max_length=128)


class DonateOut(BaseModel):
    payment_id: UUID
    status: str
    anonymous_token: str | None
    subscription_created: bool = False


class RecentDonationOut(BaseModel):
    id: UUID
    amount: Decimal
    username: str
    created_at: datetime


class RecentDonationsPageOut(BaseModel):
    items: list[RecentDonationOut]
    has_more: bool


class CampaignUpdatedEvent(BaseModel):
    type: str = "campaign_updated"
    campaign_id: UUID
    current_amount: Decimal
    goal_amount: Decimal
    progress_percentage: int
    contributors_count: int
    donation: RecentDonationOut


class CampaignLifecycleChangedEvent(BaseModel):
    type: str = "campaign_lifecycle_changed"
    campaign_id: UUID
    status: str
