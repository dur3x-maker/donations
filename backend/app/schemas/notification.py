from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    campaign_id: UUID | None = None
    action_url: str | None = None
    is_read: bool
    created_at: datetime


class NotificationCreatedEvent(BaseModel):
    type: str = "notification_created"
    notification: NotificationOut


class NotificationsReadIn(BaseModel):
    notification_ids: list[UUID] = Field(min_length=1, max_length=50)


class NotificationsReadOut(BaseModel):
    updated_count: int
