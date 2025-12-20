"""
User and Organization models.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization/tenant model for multi-tenancy."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Settings
    max_concurrent_calls: Mapped[int] = mapped_column(default=10)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    contact_lists: Mapped[List["ContactList"]] = relationship(
        "ContactList", back_populates="organization"
    )
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="organization"
    )
    audio_files: Mapped[List["AudioFile"]] = relationship(
        "AudioFile", back_populates="organization"
    )
    ivr_flows: Mapped[List["IVRFlow"]] = relationship(
        "IVRFlow", back_populates="organization"
    )
    sip_settings: Mapped[Optional["SIPSettings"]] = relationship(
        "SIPSettings", back_populates="organization", uselist=False
    )
    email_settings: Mapped[Optional["EmailSettings"]] = relationship(
        "EmailSettings", back_populates="organization", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Role - stored as string in DB, validated by UserRole enum
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.OPERATOR.value
    )

    # Organization
    organization_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="users"
    )

    # Auth tracking
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def full_name(self) -> str:
        """Return full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def __repr__(self) -> str:
        return f"<User {self.email}>"
