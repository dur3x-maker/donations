import enum
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class NotificationType(str, enum.Enum):
    donation_received = "donation_received"
    campaign_funded = "campaign_funded"
    unlock_achieved = "unlock_achieved"
    campaign_goal_reached = "campaign_goal_reached"
    campaign_report_published = "campaign_report_published"
    campaign_photos_added = "campaign_photos_added"
    campaign_author_update_created = "campaign_author_update_created"
    achievement_unlocked = "achievement_unlocked"
    patron_unlocked = "patron_unlocked"
    campaign_report_reminder = "campaign_report_reminder"
    campaign_subscription_created = "campaign_subscription_created"
    campaign_moderation = "campaign_moderation"


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(1024))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    user = relationship("User")
    campaign = relationship("Campaign")
