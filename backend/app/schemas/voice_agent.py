"""
Pydantic schemas for Voice Agent API.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ Voice Agent Config Schemas ============

class VoiceAgentConfigBase(BaseModel):
    """Base schema for voice agent configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    greeting_message: str = "Hello, thank you for calling. How can I help you today?"
    fallback_message: str = "I'm sorry, I didn't understand that. Could you please repeat?"
    goodbye_message: str = "Thank you for calling. Goodbye!"
    transfer_message: str = "Please hold while I transfer you to an agent."

    # OpenAI settings
    llm_model: str = "gpt-4o-mini"
    tts_voice: str = "nova"
    tts_model: str = "tts-1"
    whisper_model: str = "whisper-1"

    # Conversation settings
    max_turns: int = Field(20, ge=1, le=100)
    silence_timeout_seconds: float = Field(5.0, ge=1.0, le=30.0)
    max_call_duration_seconds: int = Field(600, ge=60, le=3600)

    # VAD settings
    vad_energy_threshold: float = Field(0.02, ge=0.001, le=0.5)
    vad_silence_duration: float = Field(0.8, ge=0.3, le=3.0)
    vad_min_speech_duration: float = Field(0.3, ge=0.1, le=2.0)

    # LLM settings
    llm_temperature: float = Field(0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(150, ge=50, le=500)

    # Plugin configuration
    plugins_config: Optional[List[Dict[str, Any]]] = []

    # Transfer settings
    default_transfer_extension: Optional[str] = None


class VoiceAgentConfigCreate(VoiceAgentConfigBase):
    """Schema for creating voice agent configuration."""
    openai_api_key: Optional[str] = None  # Will use org default if not provided


class VoiceAgentConfigUpdate(BaseModel):
    """Schema for updating voice agent configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    system_prompt: Optional[str] = None
    greeting_message: Optional[str] = None
    fallback_message: Optional[str] = None
    goodbye_message: Optional[str] = None
    transfer_message: Optional[str] = None
    llm_model: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_model: Optional[str] = None
    max_turns: Optional[int] = None
    silence_timeout_seconds: Optional[float] = None
    max_call_duration_seconds: Optional[int] = None
    llm_temperature: Optional[float] = None
    llm_max_tokens: Optional[int] = None
    plugins_config: Optional[List[Dict[str, Any]]] = None
    default_transfer_extension: Optional[str] = None


class VoiceAgentConfigResponse(VoiceAgentConfigBase):
    """Schema for voice agent configuration response."""
    id: str
    organization_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Inbound Route Schemas ============

class InboundRouteBase(BaseModel):
    """Base schema for inbound route."""
    did_pattern: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    is_active: bool = True
    priority: int = Field(100, ge=1, le=1000)


class InboundRouteCreate(InboundRouteBase):
    """Schema for creating inbound route."""
    agent_config_id: str


class InboundRouteUpdate(BaseModel):
    """Schema for updating inbound route."""
    did_pattern: Optional[str] = None
    description: Optional[str] = None
    agent_config_id: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class InboundRouteResponse(InboundRouteBase):
    """Schema for inbound route response."""
    id: str
    organization_id: str
    agent_config_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Conversation Schemas ============

class TranscriptEntry(BaseModel):
    """Single entry in conversation transcript."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str


class ConversationStats(BaseModel):
    """Statistics for a conversation."""
    whisper_seconds: float
    llm_input_tokens: int
    llm_output_tokens: int
    tts_characters: int
    estimated_cost_usd: float


class VoiceAgentConversationResponse(BaseModel):
    """Schema for voice agent conversation response."""
    id: str
    call_log_id: Optional[str]
    agent_config_id: str
    organization_id: str
    caller_number: str
    called_number: Optional[str]
    call_duration_seconds: int
    started_at: datetime
    ended_at: Optional[datetime]
    transcript: List[TranscriptEntry]
    turn_count: int
    summary: Optional[str]
    sentiment: Optional[str]
    detected_intent: Optional[str]
    resolution_status: str
    transfer_destination: Optional[str]
    transfer_reason: Optional[str]
    plugin_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    whisper_seconds: float
    llm_input_tokens: int
    llm_output_tokens: int
    tts_characters: int
    estimated_cost_usd: float
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Schema for paginated conversation list."""
    items: List[VoiceAgentConversationResponse]
    total: int
    page: int
    page_size: int


# ============ Dashboard/Stats Schemas ============

class VoiceAgentStats(BaseModel):
    """Voice agent usage statistics."""
    total_conversations: int
    total_duration_seconds: int
    avg_duration_seconds: float
    total_turns: int
    avg_turns: float
    resolution_breakdown: Dict[str, int]
    sentiment_breakdown: Dict[str, int]
    total_cost_usd: float
    period_start: datetime
    period_end: datetime


class ActiveCallInfo(BaseModel):
    """Information about an active voice agent call."""
    call_id: str
    agent_config_id: str
    agent_name: str
    caller_number: str
    started_at: datetime
    current_turn: int
    status: str
