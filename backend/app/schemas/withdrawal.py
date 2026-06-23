from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class WithdrawalInfoOut(BaseModel):
    campaign_id: UUID
    available: bool
    mode: Literal["demo"] = "demo"
