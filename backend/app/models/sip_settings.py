"""
SIP Settings model for storing PBX connection configuration.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization


class SIPTransport(str, enum.Enum):
    """SIP transport protocol."""
    UDP = "UDP"
    TCP = "TCP"
    TLS = "TLS"

    def _generate_next_value_(name, start, count, last_values):
        return name


class ConnectionStatus(str, enum.Enum):
    """Connection status."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    REGISTERED = "REGISTERED"
    FAILED = "FAILED"

    def _generate_next_value_(name, start, count, last_values):
        return name


class ChannelDriver(str, enum.Enum):
    """Asterisk SIP channel driver type."""
    PJSIP = "PJSIP"
    SIP = "SIP"

    def _generate_next_value_(name, start, count, last_values):
        return name


class SIPSettings(Base, UUIDMixin, TimestampMixin):
    """
    SIP Settings model for storing PBX connection configuration.

    Stores all settings needed to connect to the Grandstream UCM6302
    or other Asterisk-based PBX systems.
    """

    __tablename__ = "sip_settings"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, unique=True
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="sip_settings"
    )

    # SIP Server Connection
    sip_server: Mapped[str] = mapped_column(String(255), nullable=False)
    sip_port: Mapped[int] = mapped_column(Integer, default=5060)

    # SIP Credentials
    sip_username: Mapped[str] = mapped_column(String(100), nullable=False)
    sip_password_encrypted: Mapped[str] = mapped_column(String(255), nullable=False)

    # Transport
    sip_transport: Mapped[SIPTransport] = mapped_column(
        SQLEnum(SIPTransport, name='siptransport'), default=SIPTransport.UDP
    )

    # Registration
    registration_required: Mapped[bool] = mapped_column(Boolean, default=True)
    register_expires: Mapped[int] = mapped_column(Integer, default=3600)

    # Keep-Alive
    keepalive_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    keepalive_interval: Mapped[int] = mapped_column(Integer, default=30)

    # RTP/Media Settings
    rtp_port_start: Mapped[int] = mapped_column(Integer, default=10000)
    rtp_port_end: Mapped[int] = mapped_column(Integer, default=20000)

    # Codecs (ordered array of codec names)
    # Default: ["ulaw", "alaw", "g722", "g729"]
    codecs: Mapped[list] = mapped_column(
        JSON, default=["ulaw", "alaw", "g722"]
    )

    # Channel Driver (PJSIP vs SIP)
    channel_driver: Mapped[ChannelDriver] = mapped_column(
        SQLEnum(ChannelDriver, name='channeldriver'), default=ChannelDriver.PJSIP
    )

    # AMI Connection Settings
    ami_host: Mapped[Optional[str]] = mapped_column(String(255))
    ami_port: Mapped[int] = mapped_column(Integer, default=5038)
    ami_username: Mapped[Optional[str]] = mapped_column(String(100))
    ami_password_encrypted: Mapped[Optional[str]] = mapped_column(String(255))

    # Caller ID settings
    default_caller_id: Mapped[Optional[str]] = mapped_column(String(50))
    caller_id_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Connection status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus, name='connectionstatus'), default=ConnectionStatus.DISCONNECTED
    )
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"<SIPSettings {self.sip_server}:{self.sip_port}>"
