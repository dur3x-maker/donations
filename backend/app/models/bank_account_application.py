import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow


class BankAccountApplicationStatus(str, enum.Enum):
    pending = "PENDING"
    approved = "APPROVED"
    rejected = "REJECTED"


class BankAccountApplication(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "bank_account_applications"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[BankAccountApplicationStatus] = mapped_column(
        Enum(
            BankAccountApplicationStatus,
            name="bank_account_application_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=BankAccountApplicationStatus.pending,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="bank_account_application")
