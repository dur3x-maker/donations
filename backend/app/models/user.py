import enum

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(80))
    last_name: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.user, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    bio: Mapped[str | None] = mapped_column(String(250))
    city: Mapped[str | None] = mapped_column(String(80))
    patron_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    campaigns = relationship("Campaign", back_populates="owner")
    contributions = relationship("Contribution", back_populates="user")
    bank_account_application = relationship("BankAccountApplication", back_populates="user", uselist=False)
