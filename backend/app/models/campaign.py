"""
Campaign and CampaignContact models.
"""
from datetime import datetime, time
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Boolean, ForeignKey, Text, Integer, JSON,
    Enum as SQLEnum, Time, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization
    from app.models.contact import Contact, ContactList
    from app.models.audio import AudioFile
    from app.models.ivr import IVRFlow
    from app.models.call_log import CallLog


class CampaignStatus(str, enum.Enum):
    """Campaign status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DialingMode(str, enum.Enum):
    """Dialing mode enumeration."""
    PROGRESSIVE = "progressive"  # One call at a time per available line
    PREDICTIVE = "predictive"    # Adjusts rate based on answer rate


class ContactStatus(str, enum.Enum):
    """Status of a contact within a campaign."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DNC = "dnc"
    SKIPPED = "skipped"


class CallDisposition(str, enum.Enum):
    """Call disposition/outcome."""
    ANSWERED_HUMAN = "answered_human"
    ANSWERED_MACHINE = "answered_machine"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    INVALID_NUMBER = "invalid_number"
    DNC = "dnc"


class Campaign(Base, UUIDMixin, TimestampMixin):
    """Campaign model for managing outbound calling campaigns."""

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="campaigns"
    )

    # Status
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT
    )

    # Contact list
    contact_list_id: Mapped[str] = mapped_column(
        ForeignKey("contact_lists.id"), nullable=False
    )
    contact_list: Mapped["ContactList"] = relationship("ContactList")

    # IVR Flow
    ivr_flow_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ivr_flows.id"), nullable=True
    )
    ivr_flow: Mapped[Optional["IVRFlow"]] = relationship("IVRFlow")

    # Audio files
    greeting_audio_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("audio_files.id"), nullable=True
    )
    greeting_audio: Mapped[Optional["AudioFile"]] = relationship(
        "AudioFile", foreign_keys=[greeting_audio_id]
    )

    voicemail_audio_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("audio_files.id"), nullable=True
    )
    voicemail_audio: Mapped[Optional["AudioFile"]] = relationship(
        "AudioFile", foreign_keys=[voicemail_audio_id]
    )

    # Dialing settings
    dialing_mode: Mapped[DialingMode] = mapped_column(
        SQLEnum(DialingMode), default=DialingMode.PROGRESSIVE
    )
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, default=5)
    calls_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Retry settings
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, default=30)
    retry_on_no_answer: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_on_busy: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_on_failed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Call timing settings
    ring_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)

    # AMD settings
    amd_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    amd_action_human: Mapped[str] = mapped_column(String(50), default="play_ivr")
    amd_action_machine: Mapped[str] = mapped_column(String(50), default="leave_message")

    # Scheduling
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Calling hours (for TCPA compliance)
    calling_hours_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    calling_hours_end: Mapped[time] = mapped_column(Time, default=time(21, 0))
    respect_timezone: Mapped[bool] = mapped_column(Boolean, default=True)

    # Statistics (denormalized for quick access)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    contacts_called: Mapped[int] = mapped_column(Integer, default=0)
    contacts_answered: Mapped[int] = mapped_column(Integer, default=0)
    contacts_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Created by
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    campaign_contacts: Mapped[List["CampaignContact"]] = relationship(
        "CampaignContact", back_populates="campaign", cascade="all, delete-orphan"
    )
    call_logs: Mapped[List["CallLog"]] = relationship(
        "CallLog", back_populates="campaign"
    )

    def __repr__(self) -> str:
        return f"<Campaign {self.name}>"


class CampaignContact(Base, UUIDMixin, TimestampMixin):
    """Junction table for campaign-contact relationship with call status."""

    __tablename__ = "campaign_contacts"

    # Campaign
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False, index=True
    )
    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="campaign_contacts"
    )

    # Contact
    contact_id: Mapped[str] = mapped_column(
        ForeignKey("contacts.id"), nullable=False, index=True
    )
    contact: Mapped["Contact"] = relationship(
        "Contact", back_populates="campaign_contacts"
    )

    # Status
    status: Mapped[ContactStatus] = mapped_column(
        SQLEnum(ContactStatus), default=ContactStatus.PENDING, index=True
    )

    # Call tracking
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # Last call result
    last_disposition: Mapped[Optional[CallDisposition]] = mapped_column(
        SQLEnum(CallDisposition), nullable=True
    )

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    def __repr__(self) -> str:
        return f"<CampaignContact campaign={self.campaign_id} contact={self.contact_id}>"
