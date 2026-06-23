from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import OwnerOut


class ActivityCampaignOut(BaseModel):
    id: UUID
    title: str


class ActivityOut(BaseModel):
    id: UUID
    type: str
    actor: OwnerOut | None
    campaign: ActivityCampaignOut | None
    metadata_json: dict | None
    created_at: datetime
