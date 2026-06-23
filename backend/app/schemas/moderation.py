from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportCreateIn(BaseModel):
    reason: str = Field(min_length=2, max_length=64)
    details: str | None = Field(default=None, max_length=2000)


class ReportOut(BaseModel):
    id: UUID
    reporter_user_id: UUID | None
    campaign_id: UUID
    reason: str
    details: str | None
    status: str
    created_at: datetime


class SuspiciousFlagOut(BaseModel):
    id: UUID
    type: str
    user_id: UUID | None
    campaign_id: UUID | None
    metadata_json: dict | None
    created_at: datetime
    resolved_at: datetime | None
