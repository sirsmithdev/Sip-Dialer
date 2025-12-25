"""
Voice Agent module for AI-powered inbound call handling.

Uses OpenAI APIs:
- Whisper for speech-to-text
- GPT-4o for conversation processing
- TTS for text-to-speech
"""
from dialer.voice_agent.session import VoiceAgentSession
from dialer.voice_agent.transcriber import WhisperTranscriber
from dialer.voice_agent.synthesizer import TTSSynthesizer
from dialer.voice_agent.llm_processor import ConversationProcessor
from dialer.voice_agent.vad import SimpleVAD
from dialer.voice_agent.inbound_handler import (
    VoiceAgentInboundHandler,
    get_inbound_handler,
    init_inbound_handler
)

__all__ = [
    "VoiceAgentSession",
    "WhisperTranscriber",
    "TTSSynthesizer",
    "ConversationProcessor",
    "SimpleVAD",
    "VoiceAgentInboundHandler",
    "get_inbound_handler",
    "init_inbound_handler",
]
