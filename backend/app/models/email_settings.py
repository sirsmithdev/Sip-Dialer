"""
Email Settings model for storing SMTP configuration.
Supports per-organization email settings with encrypted credentials.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization


class EmailSettings(Base, UUIDMixin, TimestampMixin):
    """
    Email Settings model for SMTP configuration.

    Stores SMTP server settings for sending email reports and notifications.
    Each organization can have their own email configuration.
    """

    __tablename__ = "email_settings"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, unique=True
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="email_settings"
    )

    # SMTP Server Connection
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)

    # SMTP Credentials
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_password_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)

    # Sender Information
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str] = mapped_column(String(100), default="SIP Auto-Dialer")

    # TLS/SSL
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_test_success: Mapped[Optional[bool]] = mapped_column(nullable=True)
    last_test_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailSettings {self.smtp_host}:{self.smtp_port} ({self.from_email})>"
