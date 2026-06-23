import enum
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ContributionStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class Contribution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contributions"

    campaign_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    anonymous_token: Mapped[str | None] = mapped_column(String(128), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[ContributionStatus] = mapped_column(
        Enum(ContributionStatus, name="contribution_status"),
        default=ContributionStatus.pending,
        nullable=False,
    )

    campaign = relationship("Campaign", back_populates="contributions")
    user = relationship("User", back_populates="contributions")
    payment = relationship("Payment", back_populates="contribution", uselist=False)
