"""
Email Log model for tracking sent emails.
Provides audit trail and retry capability for email delivery.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Integer, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization
    from app.models.campaign import Campaign


class EmailType(str, enum.Enum):
    """Type of email sent."""
    CAMPAIGN_REPORT = "campaign_report"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    CAMPAIGN_COMPLETED = "campaign_completed"
    SYSTEM_ALERT = "system_alert"
    TEST = "test"


class EmailStatus(str, enum.Enum):
    """Email delivery status."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


class EmailLog(Base, UUIDMixin, TimestampMixin):
    """
    Email Log model for tracking all sent emails.

    Records every email send attempt with status, errors, and metadata.
    Used for auditing, debugging, and retry logic.
    """

    __tablename__ = "email_logs"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    organization: Mapped["Organization"] = relationship("Organization")

    # Recipient
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Email details
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_type: Mapped[EmailType] = mapped_column(
        SQLEnum(EmailType, name='emailtype'), nullable=False, index=True
    )

    # Status
    status: Mapped[EmailStatus] = mapped_column(
        SQLEnum(EmailStatus, name='emailstatus'), default=EmailStatus.PENDING, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Related entities (optional)
    campaign_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True, index=True
    )
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign")

    report_schedule_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("report_schedules.id"), nullable=True
    )

    # Message ID from SMTP server (for tracking)
    smtp_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<EmailLog {self.email_type.value} to {self.recipient_email} ({self.status.value})>"
