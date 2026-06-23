from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class SuspiciousFlag(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "suspicious_flags"

    type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User")
    campaign = relationship("Campaign")
