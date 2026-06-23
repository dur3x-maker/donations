import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class CampaignStatus(str, enum.Enum):
    active = "ACTIVE"
    goal_reached = "GOAL_REACHED"
    awaiting_report = "AWAITING_REPORT"
    completed = "COMPLETED"


class Campaign(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_created_at", "created_at"),
        Index(
            "uq_campaigns_owner_unfinished",
            "owner_id",
            unique=True,
            postgresql_where=text(
                "is_active IS TRUE AND status IN ('ACTIVE', 'GOAL_REACHED', 'AWAITING_REPORT')"
            ),
            sqlite_where=text(
                "is_active = 1 AND status IN ('ACTIVE', 'GOAL_REACHED', 'AWAITING_REPORT')"
            ),
        ),
    )

    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(1024))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_lifecycle_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        default=CampaignStatus.active,
        nullable=False,
        index=True,
    )
    has_completion_report: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    goal_reached_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_reminder_30_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_reminder_60_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_reminder_90_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    owner = relationship("User", back_populates="campaigns")
    contributions = relationship("Contribution", back_populates="campaign")
    updates = relationship("CampaignUpdate", back_populates="campaign", cascade="all, delete-orphan")
    completion_report = relationship("CampaignCompletionReport", back_populates="campaign", cascade="all, delete-orphan", uselist=False)
