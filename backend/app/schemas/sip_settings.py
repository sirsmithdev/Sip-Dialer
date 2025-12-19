"""
SIP Settings schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.sip_settings import SIPTransport, ConnectionStatus, ChannelDriver


class SIPSettingsBase(BaseModel):
    """Base SIP settings schema."""
    sip_server: str = Field(..., description="SIP server hostname or IP")
    sip_port: int = Field(5060, description="SIP port")
    sip_username: str = Field(..., description="SIP username/extension")
    sip_transport: SIPTransport = Field(SIPTransport.UDP, description="SIP transport protocol")
    channel_driver: ChannelDriver = Field(ChannelDriver.PJSIP, description="Asterisk channel driver (PJSIP or SIP)")

    # Registration
    registration_required: bool = Field(True, description="Whether SIP registration is required")
    register_expires: int = Field(3600, description="Registration expiry in seconds")

    # Keep-Alive
    keepalive_enabled: bool = Field(True, description="Enable SIP keep-alive")
    keepalive_interval: int = Field(30, description="Keep-alive interval in seconds")

    # RTP Settings
    rtp_port_start: int = Field(10000, description="RTP port range start")
    rtp_port_end: int = Field(20000, description="RTP port range end")

    # Codecs (ordered by priority)
    codecs: List[str] = Field(
        default=["ulaw", "alaw", "g722"],
        description="Audio codecs in priority order"
    )

    # AMI Settings
    ami_host: Optional[str] = Field(None, description="AMI host (defaults to SIP server)")
    ami_port: int = Field(5038, description="AMI port")
    ami_username: Optional[str] = Field(None, description="AMI username")

    # Caller ID
    default_caller_id: Optional[str] = Field(None, description="Default outbound caller ID")
    caller_id_name: Optional[str] = Field(None, description="Caller ID name")


class SIPSettingsCreate(SIPSettingsBase):
    """SIP settings creation schema."""
    sip_password: str = Field(..., description="SIP password")
    ami_password: Optional[str] = Field(None, description="AMI password")


class SIPSettingsUpdate(BaseModel):
    """SIP settings update schema."""
    sip_server: Optional[str] = None
    sip_port: Optional[int] = None
    sip_username: Optional[str] = None
    sip_password: Optional[str] = None
    sip_transport: Optional[SIPTransport] = None
    channel_driver: Optional[ChannelDriver] = None
    registration_required: Optional[bool] = None
    register_expires: Optional[int] = None
    keepalive_enabled: Optional[bool] = None
    keepalive_interval: Optional[int] = None
    rtp_port_start: Optional[int] = None
    rtp_port_end: Optional[int] = None
    codecs: Optional[List[str]] = None
    ami_host: Optional[str] = None
    ami_port: Optional[int] = None
    ami_username: Optional[str] = None
    ami_password: Optional[str] = None
    default_caller_id: Optional[str] = None
    caller_id_name: Optional[str] = None


class SIPSettingsResponse(SIPSettingsBase):
    """SIP settings response schema (excludes passwords)."""
    id: str
    organization_id: str
    is_active: bool
    connection_status: ConnectionStatus
    last_connected_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SIPConnectionTestRequest(BaseModel):
    """Request schema for testing SIP connection."""
    test_type: str = Field("ami", description="Type of test: 'ami' or 'sip'")


class SIPConnectionTestResponse(BaseModel):
    """Response schema for SIP connection test."""
    success: bool
    message: str
    details: Optional[dict] = None

    # Enhanced diagnostics
    timing_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    resolved_ip: Optional[str] = Field(None, description="DNS resolved IP address")
    test_steps: Optional[List[str]] = Field(None, description="Step-by-step log of test")
    server_info: Optional[dict] = Field(None, description="Server version and capabilities")
    authenticated: Optional[bool] = Field(None, description="Whether authentication succeeded")
    diagnostic_hint: Optional[str] = Field(None, description="User-friendly troubleshooting tip")
