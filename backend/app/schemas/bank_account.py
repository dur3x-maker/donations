from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BankAccountApplicationOut(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankAccountApplicationStateOut(BaseModel):
    can_open_bank_account: bool
    has_bank_account: bool
    application_status: str | None = None
    application: BankAccountApplicationOut | None = None
