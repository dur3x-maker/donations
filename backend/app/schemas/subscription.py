from uuid import UUID

from pydantic import BaseModel


class CampaignSubscriptionOut(BaseModel):
    campaign_id: UUID
    is_subscribed: bool
