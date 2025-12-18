"""
Call log model for tracking all call activity.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, Float, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class CallDirection(str, enum.Enum):
    """Call direction."""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class CallResult(str, enum.Enum):
    """Final call result."""
    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    CONGESTION = "congestion"
    CANCELLED = "cancelled"


class AMDResult(str, enum.Enum):
    """AMD detection result."""
    HUMAN = "human"
    MACHINE = "machine"
    UNKNOWN = "unknown"
    NOT_USED = "not_used"


class CallLog(Base, UUIDMixin, TimestampMixin):
    """
    Call log model for recording all call details.

    This table should be partitioned by created_at for performance
    with large volumes of call data.
    """

    __tablename__ = "call_logs"

    # Campaign (optional - calls might not be part of a campaign)
    campaign_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True, index=True
    )
    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="call_logs"
    )

    # Contact reference
    contact_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("contacts.id"), nullable=True, index=True
    )

    # Call identifiers
    channel_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    unique_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)

    # Phone numbers
    caller_id: Mapped[str] = mapped_column(String(20), nullable=False)
    destination: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Direction
    direction: Mapped[CallDirection] = mapped_column(
        SQLEnum(CallDirection), default=CallDirection.OUTBOUND
    )

    # Timestamps
    initiated_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    answered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Duration
    ring_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    talk_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Result
    result: Mapped[CallResult] = mapped_column(
        SQLEnum(CallResult), nullable=False
    )
    hangup_cause: Mapped[Optional[str]] = mapped_column(String(50))
    hangup_cause_code: Mapped[Optional[int]] = mapped_column(Integer)

    # AMD
    amd_result: Mapped[AMDResult] = mapped_column(
        SQLEnum(AMDResult), default=AMDResult.NOT_USED
    )
    amd_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # IVR interaction
    ivr_flow_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ivr_flows.id"), nullable=True
    )
    ivr_completed: Mapped[bool] = mapped_column(default=False)

    # DTMF inputs collected (JSON array)
    dtmf_inputs: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Recording
    recording_path: Mapped[Optional[str]] = mapped_column(String(500))
    recording_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Additional call metadata
    call_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Asterisk/AMI specific
    asterisk_channel: Mapped[Optional[str]] = mapped_column(String(100))
    asterisk_linked_id: Mapped[Optional[str]] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"<CallLog {self.unique_id} {self.destination}>"
