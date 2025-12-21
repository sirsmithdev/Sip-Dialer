"""
Email Settings model for storing email provider configuration.
Supports per-organization email settings with multiple providers (SMTP, Resend).
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization


class EmailProvider(str, PyEnum):
    """Email provider types."""
    SMTP = "smtp"
    RESEND = "resend"


class EmailSettings(Base, UUIDMixin, TimestampMixin):
    """
    Email Settings model for email provider configuration.

    Stores email provider settings for sending reports and notifications.
    Each organization can have their own email configuration.
    Supports both SMTP and Resend API providers.
    """

    __tablename__ = "email_settings"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, unique=True
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="email_settings"
    )

    # Provider Selection
    provider: Mapped[str] = mapped_column(
        Enum(EmailProvider, name="email_provider", create_type=False),
        default=EmailProvider.RESEND,
        server_default="resend"
    )

    # Resend API Configuration
    resend_api_key_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # SMTP Server Connection (for SMTP provider)
    smtp_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)

    # SMTP Credentials (for SMTP provider)
    smtp_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    smtp_password_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Sender Information (used by all providers)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str] = mapped_column(String(100), default="CallFlow")

    # TLS/SSL (for SMTP provider)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_test_success: Mapped[Optional[bool]] = mapped_column(nullable=True)
    last_test_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        if self.provider == EmailProvider.RESEND:
            return f"<EmailSettings Resend ({self.from_email})>"
        return f"<EmailSettings SMTP {self.smtp_host}:{self.smtp_port} ({self.from_email})>"
