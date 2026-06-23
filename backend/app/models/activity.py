import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ActivityType(str, enum.Enum):
    campaign_created = "campaign_created"
    donation_made = "donation_made"
    campaign_completed = "campaign_completed"
    unlock_achieved = "unlock_achieved"


class Activity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "activities"

    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType, name="activity_type"), nullable=False, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    actor = relationship("User")
    campaign = relationship("Campaign")
