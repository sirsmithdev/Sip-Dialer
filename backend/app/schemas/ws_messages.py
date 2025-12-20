"""
WebSocket message schemas for real-time updates.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel


class WSMessageType(str, Enum):
    """WebSocket message types."""
    # Dashboard
    DASHBOARD_STATS = "dashboard.stats"

    # Campaign
    CAMPAIGN_PROGRESS = "campaign.progress"
    CAMPAIGN_STATUS_CHANGED = "campaign.status_changed"

    # SIP
    SIP_STATUS = "sip.status"

    # Calls
    CALL_UPDATE = "call.update"
    CALL_STARTED = "call.started"
    CALL_ANSWERED = "call.answered"
    CALL_ENDED = "call.ended"

    # System
    PING = "ping"
    PONG = "pong"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    ERROR = "error"


class WSMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str
    data: Optional[dict] = None
    channel: Optional[str] = None
    timestamp: Optional[datetime] = None


# Dashboard Stats
class DashboardStatsData(BaseModel):
    """Dashboard statistics data."""
    active_campaigns: int = 0
    calls_today: int = 0
    calls_answered: int = 0
    answer_rate: float = 0.0
    total_contacts: int = 0
    completed_campaigns: int = 0
    avg_call_duration: float = 0.0
    sip_status: str = "disconnected"
    sip_extension: Optional[str] = None


# Campaign Progress
class CampaignProgressData(BaseModel):
    """Campaign progress data."""
    campaign_id: str
    campaign_name: Optional[str] = None
    status: str
    total_contacts: int = 0
    contacts_called: int = 0
    contacts_answered: int = 0
    contacts_completed: int = 0
    contacts_failed: int = 0
    contacts_pending: int = 0
    answer_rate: float = 0.0
    calls_per_minute: float = 0.0


class CampaignStatusChangedData(BaseModel):
    """Campaign status change event."""
    campaign_id: str
    campaign_name: Optional[str] = None
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None


# SIP Status
class SIPStatusData(BaseModel):
    """SIP connection status data."""
    status: str  # disconnected, connecting, registered, failed
    extension: Optional[str] = None
    server: Optional[str] = None
    active_calls: int = 0
    error: Optional[str] = None
    last_updated: Optional[datetime] = None


# Call Updates
class CallUpdateData(BaseModel):
    """Individual call update data."""
    call_id: str
    campaign_id: Optional[str] = None
    contact_id: Optional[str] = None
    phone_number: str
    status: str  # dialing, ringing, connected, ivr, completed, failed
    direction: str = "outbound"
    duration_seconds: int = 0
    amd_result: Optional[str] = None
    ivr_node: Optional[str] = None
    can_transfer: bool = False
    started_at: Optional[datetime] = None


# Helper functions for creating messages
def create_dashboard_stats_message(data: DashboardStatsData) -> dict:
    """Create a dashboard stats message."""
    return {
        "type": WSMessageType.DASHBOARD_STATS,
        "data": data.model_dump()
    }


def create_campaign_progress_message(data: CampaignProgressData) -> dict:
    """Create a campaign progress message."""
    return {
        "type": WSMessageType.CAMPAIGN_PROGRESS,
        "data": data.model_dump()
    }


def create_sip_status_message(data: SIPStatusData) -> dict:
    """Create a SIP status message."""
    return {
        "type": WSMessageType.SIP_STATUS,
        "data": data.model_dump()
    }


def create_call_update_message(data: CallUpdateData) -> dict:
    """Create a call update message."""
    return {
        "type": WSMessageType.CALL_UPDATE,
        "data": data.model_dump()
    }
