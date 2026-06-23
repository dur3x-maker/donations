import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    dismissed = "dismissed"
    action_taken = "action_taken"


class Report(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    reporter_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus, name="report_status"), default=ReportStatus.pending, nullable=False, index=True)

    reporter = relationship("User")
    campaign = relationship("Campaign")
