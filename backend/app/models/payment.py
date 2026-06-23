import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class Payment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    contribution_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contributions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_payment_id: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    contribution = relationship("Contribution", back_populates="payment")
