from decimal import Decimal

from pydantic import BaseModel


class PlatformStatsOut(BaseModel):
    users_count: int
    campaigns_total: int
    campaigns_active: int
    campaigns_completed: int
    successful_reports: int
    confirmed_contributions: int
    total_donated_amount: Decimal
