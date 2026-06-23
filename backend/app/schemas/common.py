from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OwnerOut(BaseModel):
    id: UUID
    username: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ContributionPublicOut(BaseModel):
    id: UUID
    amount: Decimal
    donor_name: str | None = None
    created_at: datetime


class AmountMixin(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
