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
    username: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.user, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    patron_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    campaigns = relationship("Campaign", back_populates="owner")
    contributions = relationship("Contribution", back_populates="user")
