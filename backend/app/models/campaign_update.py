from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class CampaignUpdate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_updates"
    __table_args__ = (
        Index("ix_campaign_updates_campaign_id", "campaign_id"),
        Index("ix_campaign_updates_created_at", "created_at"),
    )

    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="updates")
    author = relationship("User")
    photos = relationship("CampaignUpdatePhoto", back_populates="update", cascade="all, delete-orphan", order_by="CampaignUpdatePhoto.created_at")


class CampaignUpdatePhoto(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_update_photos"

    update_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_updates.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    update = relationship("CampaignUpdate", back_populates="photos")
