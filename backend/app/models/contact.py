"""
Contact, ContactList, and DNC models.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization
    from app.models.campaign import CampaignContact


class ContactList(Base, UUIDMixin, TimestampMixin):
    """Contact list model for grouping contacts."""

    __tablename__ = "contact_lists"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="contact_lists"
    )

    # Statistics
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    valid_contacts: Mapped[int] = mapped_column(Integer, default=0)
    invalid_contacts: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Upload info
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact", back_populates="contact_list", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ContactList {self.name}>"


class Contact(Base, UUIDMixin, TimestampMixin):
    """Individual contact model."""

    __tablename__ = "contacts"

    # Contact list
    contact_list_id: Mapped[str] = mapped_column(
        ForeignKey("contact_lists.id"), nullable=False, index=True
    )
    contact_list: Mapped["ContactList"] = relationship(
        "ContactList", back_populates="contacts"
    )

    # Contact info
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phone_number_e164: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    # Custom fields stored as JSON
    custom_fields: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Validation
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_error: Mapped[Optional[str]] = mapped_column(String(255))

    # Timezone for calling hours compliance
    timezone: Mapped[Optional[str]] = mapped_column(String(50))

    # Campaign contacts (for tracking calls across campaigns)
    campaign_contacts: Mapped[List["CampaignContact"]] = relationship(
        "CampaignContact", back_populates="contact"
    )

    @property
    def full_name(self) -> str:
        """Return full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return ""

    def __repr__(self) -> str:
        return f"<Contact {self.phone_number}>"


class DNCEntry(Base, UUIDMixin, TimestampMixin):
    """Do-Not-Call list entry."""

    __tablename__ = "dnc_entries"

    # Phone number in E.164 format
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Organization (None = global DNC)
    organization_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )

    # Source of DNC entry
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, opt-out, import
    reason: Mapped[Optional[str]] = mapped_column(Text)

    # Added by
    added_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<DNCEntry {self.phone_number}>"


class DNCCheckLog(Base, UUIDMixin, TimestampMixin):
    """Log of DNC checks performed for compliance tracking."""

    __tablename__ = "dnc_check_logs"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Campaign reference
    campaign_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True, index=True
    )

    # Phone number checked
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Contact reference (if available)
    contact_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("contacts.id"), nullable=True
    )

    # Check result
    is_on_dnc: Mapped[bool] = mapped_column(Boolean, default=False)

    # DNC entry matched (if any)
    dnc_entry_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("dnc_entries.id"), nullable=True
    )

    # Whether a call was blocked due to this check
    call_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source of check (dialer, api, manual)
    check_source: Mapped[str] = mapped_column(String(50), default="dialer")

    def __repr__(self) -> str:
        return f"<DNCCheckLog {self.phone_number} on_dnc={self.is_on_dnc}>"


class ComplianceViolation(Base, UUIDMixin, TimestampMixin):
    """Record of compliance violations for audit purposes."""

    __tablename__ = "compliance_violations"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )

    # Campaign reference
    campaign_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True, index=True
    )

    # Call reference
    call_log_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("call_logs.id"), nullable=True
    )

    # Contact phone
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Violation type: dnc_call, outside_hours, no_consent, etc.
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Description of violation
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Severity: low, medium, high, critical
    severity: Mapped[str] = mapped_column(String(20), default="medium")

    # Whether this has been reviewed
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ComplianceViolation {self.violation_type} {self.phone_number}>"
