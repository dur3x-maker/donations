from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class CampaignSubscription(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "campaign_id", name="uq_campaign_subscriptions_user_campaign"),)

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User")
    campaign = relationship("Campaign")
