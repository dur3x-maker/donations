from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class CampaignCompletionReport(UUIDMixin, Base):
    __tablename__ = "campaign_completion_reports"
    __table_args__ = (
        UniqueConstraint("campaign_id"),
        Index("ix_campaign_completion_reports_campaign_id", "campaign_id"),
    )

    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gratitude_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    campaign = relationship("Campaign", back_populates="completion_report")
    author = relationship("User")
    photos = relationship("CampaignCompletionPhoto", back_populates="report", cascade="all, delete-orphan", order_by="CampaignCompletionPhoto.created_at")


class CampaignCompletionPhoto(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaign_completion_photos"

    report_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaign_completion_reports.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    report = relationship("CampaignCompletionReport", back_populates="photos")
