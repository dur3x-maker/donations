from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class TelegramModerationSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "telegram_moderation_sessions"

    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_telegram_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    admin_name: Mapped[str] = mapped_column(String(160), nullable=False)

    campaign = relationship("Campaign")
