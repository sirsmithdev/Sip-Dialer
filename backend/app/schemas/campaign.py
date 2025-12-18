"""
Campaign Pydantic schemas.
"""
from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class CampaignStatus(str, Enum):
    """Campaign status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DialingMode(str, Enum):
    """Dialing mode enumeration."""
    PROGRESSIVE = "progressive"
    PREDICTIVE = "predictive"


class ContactStatus(str, Enum):
    """Status of a contact within a campaign."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DNC = "dnc"
    SKIPPED = "skipped"


class CallDisposition(str, Enum):
    """Call disposition/outcome."""
    ANSWERED_HUMAN = "answered_human"
    ANSWERED_MACHINE = "answered_machine"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    INVALID_NUMBER = "invalid_number"
    DNC = "dnc"


class AMDAction(str, Enum):
    """AMD action options."""
    PLAY_IVR = "play_ivr"
    LEAVE_MESSAGE = "leave_message"
    HANGUP = "hangup"
    TRANSFER = "transfer"


# ============================================================================
# Campaign Schemas
# ============================================================================

class CampaignCreate(BaseModel):
    """Schema for creating a campaign."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    # Contact list (required)
    contact_list_id: str = Field(..., description="ID of the contact list to use")

    # IVR Flow (optional)
    ivr_flow_id: Optional[str] = Field(None, description="ID of the IVR flow to use")

    # Audio files
    greeting_audio_id: Optional[str] = Field(None, description="ID of the greeting audio")
    voicemail_audio_id: Optional[str] = Field(None, description="ID of the voicemail audio")

    # Dialing settings
    dialing_mode: DialingMode = Field(default=DialingMode.PROGRESSIVE)
    max_concurrent_calls: int = Field(default=5, ge=1, le=100)
    calls_per_minute: Optional[int] = Field(None, ge=1, le=1000)

    # Retry settings
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_delay_minutes: int = Field(default=30, ge=1, le=1440)
    retry_on_no_answer: bool = Field(default=True)
    retry_on_busy: bool = Field(default=True)
    retry_on_failed: bool = Field(default=False)

    # Call timing
    ring_timeout_seconds: int = Field(default=30, ge=10, le=120)

    # AMD settings
    amd_enabled: bool = Field(default=True)
    amd_action_human: AMDAction = Field(default=AMDAction.PLAY_IVR)
    amd_action_machine: AMDAction = Field(default=AMDAction.LEAVE_MESSAGE)

    # Scheduling
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

    # Calling hours (TCPA)
    calling_hours_start: time = Field(default=time(9, 0))
    calling_hours_end: time = Field(default=time(21, 0))
    respect_timezone: bool = Field(default=True)


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    # Contact list (can only change in DRAFT status)
    contact_list_id: Optional[str] = None

    # IVR Flow
    ivr_flow_id: Optional[str] = None

    # Audio files
    greeting_audio_id: Optional[str] = None
    voicemail_audio_id: Optional[str] = None

    # Dialing settings
    dialing_mode: Optional[DialingMode] = None
    max_concurrent_calls: Optional[int] = Field(None, ge=1, le=100)
    calls_per_minute: Optional[int] = Field(None, ge=1, le=1000)

    # Retry settings
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_minutes: Optional[int] = Field(None, ge=1, le=1440)
    retry_on_no_answer: Optional[bool] = None
    retry_on_busy: Optional[bool] = None
    retry_on_failed: Optional[bool] = None

    # Call timing
    ring_timeout_seconds: Optional[int] = Field(None, ge=10, le=120)

    # AMD settings
    amd_enabled: Optional[bool] = None
    amd_action_human: Optional[AMDAction] = None
    amd_action_machine: Optional[AMDAction] = None

    # Scheduling
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

    # Calling hours (TCPA)
    calling_hours_start: Optional[time] = None
    calling_hours_end: Optional[time] = None
    respect_timezone: Optional[bool] = None


class CampaignResponse(BaseModel):
    """Schema for campaign response."""
    id: str
    name: str
    description: Optional[str]
    organization_id: str
    status: CampaignStatus

    # Related entities
    contact_list_id: str
    ivr_flow_id: Optional[str]
    greeting_audio_id: Optional[str]
    voicemail_audio_id: Optional[str]

    # Dialing settings
    dialing_mode: DialingMode
    max_concurrent_calls: int
    calls_per_minute: Optional[int]

    # Retry settings
    max_retries: int
    retry_delay_minutes: int
    retry_on_no_answer: bool
    retry_on_busy: bool
    retry_on_failed: bool

    # Call timing
    ring_timeout_seconds: int

    # AMD settings
    amd_enabled: bool
    amd_action_human: str
    amd_action_machine: str

    # Scheduling
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]

    # Calling hours
    calling_hours_start: time
    calling_hours_end: time
    respect_timezone: bool

    # Statistics
    total_contacts: int
    contacts_called: int
    contacts_answered: int
    contacts_completed: int

    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str]

    model_config = {"from_attributes": True}


class CampaignListItem(BaseModel):
    """Simplified campaign for list views."""
    id: str
    name: str
    description: Optional[str]
    status: CampaignStatus
    dialing_mode: DialingMode
    total_contacts: int
    contacts_called: int
    contacts_answered: int
    contacts_completed: int
    scheduled_start: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list response."""
    items: List[CampaignListItem]
    total: int
    page: int
    page_size: int


# ============================================================================
# Campaign Contact Schemas
# ============================================================================

class CampaignContactResponse(BaseModel):
    """Schema for campaign contact response."""
    id: str
    campaign_id: str
    contact_id: str
    status: ContactStatus
    attempts: int
    last_attempt_at: Optional[datetime]
    next_attempt_at: Optional[datetime]
    last_disposition: Optional[CallDisposition]
    priority: int

    # Include contact info
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignContactsResponse(BaseModel):
    """Schema for paginated campaign contacts response."""
    items: List[CampaignContactResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Campaign Statistics Schemas
# ============================================================================

class CampaignStatsResponse(BaseModel):
    """Detailed campaign statistics."""
    campaign_id: str
    status: CampaignStatus

    # Contact counts
    total_contacts: int
    contacts_pending: int
    contacts_in_progress: int
    contacts_completed: int
    contacts_failed: int
    contacts_dnc: int
    contacts_skipped: int

    # Call counts
    total_calls: int
    answered_human: int
    answered_machine: int
    no_answer: int
    busy: int
    failed: int
    invalid_number: int

    # Rates
    answer_rate: float  # percentage
    completion_rate: float  # percentage
    human_rate: float  # percentage of answered calls

    # Timing
    average_call_duration: Optional[float]  # seconds
    total_talk_time: float  # seconds

    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_call_at: Optional[datetime]


# ============================================================================
# Campaign Action Schemas
# ============================================================================

class CampaignStatusUpdate(BaseModel):
    """Schema for campaign status update."""
    status: CampaignStatus


class CampaignScheduleRequest(BaseModel):
    """Schema for scheduling a campaign."""
    scheduled_start: datetime
    scheduled_end: Optional[datetime] = None
