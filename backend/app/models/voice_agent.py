"""
Voice Agent models for AI-powered inbound call handling.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Boolean, ForeignKey, Text, Integer, JSON,
    Enum as SQLEnum, Float
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization
    from app.models.call_log import CallLog


class VoiceAgentStatus(str, enum.Enum):
    """Voice agent configuration status."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ResolutionStatus(str, enum.Enum):
    """Conversation resolution status."""
    RESOLVED = "resolved"
    TRANSFERRED = "transferred"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"
    ERROR = "error"


class VoiceAgentConfig(Base, UUIDMixin, TimestampMixin):
    """Configuration for AI voice agent."""

    __tablename__ = "voice_agent_configs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship("Organization")

    # Status
    status: Mapped[VoiceAgentStatus] = mapped_column(
        SQLEnum(VoiceAgentStatus), default=VoiceAgentStatus.DRAFT
    )

    # OpenAI API settings (encrypted key stored separately or in env)
    openai_api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str] = mapped_column(String(50), default="gpt-4o-mini")
    tts_voice: Mapped[str] = mapped_column(String(50), default="nova")
    tts_model: Mapped[str] = mapped_column(String(50), default="tts-1")
    whisper_model: Mapped[str] = mapped_column(String(50), default="whisper-1")

    # System prompt and behavior
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    greeting_message: Mapped[str] = mapped_column(
        Text,
        default="Hello, thank you for calling. How can I help you today?"
    )
    fallback_message: Mapped[str] = mapped_column(
        Text,
        default="I'm sorry, I didn't understand that. Could you please repeat?"
    )
    goodbye_message: Mapped[str] = mapped_column(
        Text,
        default="Thank you for calling. Goodbye!"
    )

    # Conversation settings
    max_turns: Mapped[int] = mapped_column(Integer, default=20)
    silence_timeout_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    max_call_duration_seconds: Mapped[int] = mapped_column(Integer, default=600)

    # VAD settings
    vad_energy_threshold: Mapped[float] = mapped_column(Float, default=0.02)
    vad_silence_duration: Mapped[float] = mapped_column(Float, default=0.8)
    vad_min_speech_duration: Mapped[float] = mapped_column(Float, default=0.3)

    # LLM settings
    llm_temperature: Mapped[float] = mapped_column(Float, default=0.7)
    llm_max_tokens: Mapped[int] = mapped_column(Integer, default=150)

    # Plugin configuration (JSON list of enabled plugins with settings)
    plugins_config: Mapped[Optional[dict]] = mapped_column(JSON, default=list)

    # Transfer settings
    default_transfer_extension: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transfer_message: Mapped[str] = mapped_column(
        Text,
        default="Please hold while I transfer you to an agent."
    )

    # Relationships
    inbound_routes: Mapped[List["InboundRoute"]] = relationship(
        "InboundRoute", back_populates="agent_config", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["VoiceAgentConversation"]] = relationship(
        "VoiceAgentConversation", back_populates="agent_config"
    )

    def __repr__(self) -> str:
        return f"<VoiceAgentConfig {self.name}>"


class InboundRoute(Base, UUIDMixin, TimestampMixin):
    """Routes inbound calls to voice agents based on DID/extension."""

    __tablename__ = "inbound_routes"

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship("Organization")

    # DID pattern (e.g., "+1555*" or "1001" or exact number)
    did_pattern: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Agent configuration
    agent_config_id: Mapped[str] = mapped_column(
        ForeignKey("voice_agent_configs.id"), nullable=False
    )
    agent_config: Mapped["VoiceAgentConfig"] = relationship(
        "VoiceAgentConfig", back_populates="inbound_routes"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Priority (lower = higher priority, for overlapping patterns)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    def __repr__(self) -> str:
        return f"<InboundRoute {self.did_pattern} -> {self.agent_config_id}>"


class VoiceAgentConversation(Base, UUIDMixin, TimestampMixin):
    """Stores conversation logs for voice agent calls."""

    __tablename__ = "voice_agent_conversations"

    # Link to call log
    call_log_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("call_logs.id"), nullable=True
    )
    call_log: Mapped[Optional["CallLog"]] = relationship("CallLog")

    # Agent configuration used
    agent_config_id: Mapped[str] = mapped_column(
        ForeignKey("voice_agent_configs.id"), nullable=False
    )
    agent_config: Mapped["VoiceAgentConfig"] = relationship(
        "VoiceAgentConfig", back_populates="conversations"
    )

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )

    # Call metadata
    caller_number: Mapped[str] = mapped_column(String(50), nullable=False)
    called_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    call_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Conversation timing
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Conversation data
    # Format: [{"role": "user"|"assistant", "content": "...", "timestamp": "..."}, ...]
    transcript: Mapped[list] = mapped_column(JSON, default=list)

    # Number of conversation turns
    turn_count: Mapped[int] = mapped_column(Integer, default=0)

    # AI-generated summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Detected sentiment (positive/neutral/negative)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Detected intent/topic
    detected_intent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Outcome
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        SQLEnum(ResolutionStatus), default=ResolutionStatus.RESOLVED
    )
    transfer_destination: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transfer_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Plugin data (results from external API calls)
    # Format: {"plugin_name": {"request": {...}, "response": {...}}, ...}
    plugin_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Error information if any
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cost tracking (for billing/monitoring)
    whisper_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    tts_characters: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    def __repr__(self) -> str:
        return f"<VoiceAgentConversation {self.caller_number} @ {self.started_at}>"

    def calculate_cost(self) -> float:
        """Calculate estimated cost based on usage."""
        # OpenAI pricing (as of 2024)
        whisper_cost = self.whisper_seconds / 60 * 0.006  # $0.006/min
        llm_input_cost = self.llm_input_tokens / 1000 * 0.00015  # GPT-4o-mini input
        llm_output_cost = self.llm_output_tokens / 1000 * 0.0006  # GPT-4o-mini output
        tts_cost = self.tts_characters / 1000 * 0.015  # TTS-1

        return whisper_cost + llm_input_cost + llm_output_cost + tts_cost
