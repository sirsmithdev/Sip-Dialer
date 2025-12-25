"""
Voice Agent Session - Main orchestrator for AI voice conversations.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
import logging

from dialer.voice_agent.vad import SimpleVAD
from dialer.voice_agent.transcriber import WhisperTranscriber
from dialer.voice_agent.llm_processor import ConversationProcessor
from dialer.voice_agent.synthesizer import TTSSynthesizer, InMemoryTTSCache
from dialer.voice_agent.audio_converter import convert_for_whisper, convert_from_tts

logger = logging.getLogger(__name__)


@dataclass
class VoiceAgentConfig:
    """Configuration for voice agent session."""
    # OpenAI settings
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    tts_voice: str = "nova"
    tts_model: str = "tts-1"
    whisper_model: str = "whisper-1"

    # System prompt
    system_prompt: str = "You are a helpful AI assistant handling phone calls."
    greeting_message: str = "Hello, thank you for calling. How can I help you today?"
    fallback_message: str = "I'm sorry, I didn't understand that. Could you please repeat?"
    goodbye_message: str = "Thank you for calling. Goodbye!"
    transfer_message: str = "Please hold while I transfer you to an agent."

    # Conversation limits
    max_turns: int = 20
    silence_timeout_seconds: float = 5.0
    max_call_duration_seconds: int = 600

    # VAD settings
    vad_energy_threshold: float = 0.02
    vad_silence_duration: float = 0.8
    vad_min_speech_duration: float = 0.3

    # LLM settings
    llm_temperature: float = 0.7
    llm_max_tokens: int = 150

    # Plugins
    plugins: List["ExternalPlugin"] = field(default_factory=list)

    # Audio settings
    input_format: str = "ulaw"
    input_sample_rate: int = 8000
    output_format: str = "ulaw"
    output_sample_rate: int = 8000


@dataclass
class SessionStats:
    """Statistics for a voice agent session."""
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    turn_count: int = 0
    whisper_seconds: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    tts_characters: int = 0

    def calculate_cost(self) -> float:
        """Calculate estimated cost."""
        whisper_cost = self.whisper_seconds / 60 * 0.006
        llm_input_cost = self.llm_input_tokens / 1000 * 0.00015
        llm_output_cost = self.llm_output_tokens / 1000 * 0.0006
        tts_cost = self.tts_characters / 1000 * 0.015
        return whisper_cost + llm_input_cost + llm_output_cost + tts_cost


class VoiceAgentSession:
    """
    Main orchestrator for a voice agent conversation.

    Handles the full conversation loop:
    1. Receive audio from caller
    2. Detect speech boundaries (VAD)
    3. Transcribe speech (Whisper)
    4. Process with LLM (GPT-4o)
    5. Synthesize response (TTS)
    6. Play audio to caller
    """

    def __init__(
        self,
        config: VoiceAgentConfig,
        play_audio_callback: Callable[[bytes], Awaitable[None]],
        get_audio_callback: Callable[[], Awaitable[Optional[bytes]]],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize voice agent session.

        Args:
            config: Voice agent configuration
            play_audio_callback: Async callback to play audio to caller
            get_audio_callback: Async callback to get audio from caller
            context: Optional context (caller info, etc.)
        """
        self.config = config
        self.play_audio = play_audio_callback
        self.get_audio = get_audio_callback
        self.context = context or {}

        # Initialize components
        self.vad = SimpleVAD(
            energy_threshold=config.vad_energy_threshold,
            silence_duration=config.vad_silence_duration,
            min_speech_duration=config.vad_min_speech_duration,
            sample_rate=config.input_sample_rate
        )

        self.transcriber = WhisperTranscriber(
            api_key=config.openai_api_key,
            model=config.whisper_model
        )

        self.llm = ConversationProcessor(
            api_key=config.openai_api_key,
            system_prompt=config.system_prompt,
            model=config.llm_model,
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
            plugins=config.plugins
        )

        self.tts = TTSSynthesizer(
            api_key=config.openai_api_key,
            voice=config.tts_voice,
            model=config.tts_model,
            cache_service=InMemoryTTSCache()
        )

        # Session state
        self.running = False
        self.stats = SessionStats()
        self.transcript: List[Dict[str, Any]] = []
        self._pending_action: Optional[Dict] = None

    async def start(self) -> Dict[str, Any]:
        """
        Start the voice agent session.

        Returns:
            Session result including transcript and statistics
        """
        self.running = True
        self.stats.started_at = datetime.utcnow()

        logger.info(f"Voice agent session started: {self.context}")

        try:
            # Play greeting
            await self._speak(self.config.greeting_message)

            # Main conversation loop
            while self.running:
                # Check limits
                if self.stats.turn_count >= self.config.max_turns:
                    logger.info("Max turns reached")
                    await self._speak("I apologize, but we've reached the conversation limit. Let me transfer you to an agent.")
                    self._pending_action = {"action": "transfer", "reason": "max_turns"}
                    break

                elapsed = (datetime.utcnow() - self.stats.started_at).total_seconds()
                if elapsed >= self.config.max_call_duration_seconds:
                    logger.info("Max duration reached")
                    await self._speak("I need to wrap up our call now. Is there anything else I can quickly help with?")
                    break

                # Get user speech
                user_text = await self._listen()

                if user_text is None:
                    # Timeout or no speech
                    continue

                if not user_text.strip():
                    continue

                # Log user input
                self._log_turn("user", user_text)
                self.stats.turn_count += 1

                # Process with LLM
                response_text = await self.llm.process(user_text, self.context)

                # Check for actions
                if self.llm.pending_action:
                    self._pending_action = self.llm.pending_action
                    self.llm.clear_pending_action()

                    # Handle action
                    if self._pending_action.get("action") == "transfer":
                        await self._speak(self.config.transfer_message)
                        break
                    elif self._pending_action.get("action") == "hangup":
                        await self._speak(self.config.goodbye_message)
                        break

                # Speak response
                if response_text:
                    self._log_turn("assistant", response_text)
                    await self._speak(response_text)

        except asyncio.CancelledError:
            logger.info("Voice agent session cancelled")
        except Exception as e:
            logger.error(f"Voice agent session error: {e}")
            try:
                await self._speak("I'm sorry, I encountered an error. Please try again or speak with an agent.")
            except:
                pass

        finally:
            await self._end_session()

        return self._get_result()

    async def stop(self):
        """Stop the voice agent session."""
        self.running = False

    async def _listen(self) -> Optional[str]:
        """
        Listen for and transcribe user speech.

        Returns:
            Transcribed text or None if timeout
        """
        start_time = asyncio.get_event_loop().time()
        self.vad.reset()

        while self.running:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self.config.silence_timeout_seconds:
                # Check if we have any speech buffered
                audio = self.vad.force_end()
                if audio:
                    return await self._transcribe(audio)
                return None

            # Get audio chunk
            try:
                audio_chunk = await asyncio.wait_for(
                    self.get_audio(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                continue

            if audio_chunk is None:
                continue

            # Process with VAD
            complete_utterance = self.vad.process_chunk(audio_chunk)
            if complete_utterance:
                return await self._transcribe(complete_utterance)

        return None

    async def _transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio to text."""
        # Convert audio format for Whisper
        pcm_bytes, sample_rate = convert_for_whisper(
            audio_bytes,
            source_format=self.config.input_format,
            source_rate=self.config.input_sample_rate
        )

        # Transcribe
        text = await self.transcriber.transcribe(
            pcm_bytes,
            sample_rate=sample_rate
        )

        # Update stats
        self.stats.whisper_seconds = self.transcriber.total_seconds_transcribed

        return text

    async def _speak(self, text: str):
        """Synthesize and play speech."""
        if not text:
            return

        # Synthesize
        audio_bytes = await self.tts.synthesize(text)

        if audio_bytes:
            # Convert for telephony
            telephony_audio = convert_from_tts(
                audio_bytes,
                target_format=self.config.output_format,
                target_rate=self.config.output_sample_rate
            )

            # Play
            await self.play_audio(telephony_audio)

        # Update stats
        self.stats.tts_characters = self.tts.total_characters_synthesized

    def _log_turn(self, role: str, content: str):
        """Log a conversation turn."""
        self.transcript.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _end_session(self):
        """Clean up session."""
        self.running = False
        self.stats.ended_at = datetime.utcnow()

        # Update final stats from components
        self.stats.whisper_seconds = self.transcriber.total_seconds_transcribed
        self.stats.llm_input_tokens = self.llm.total_input_tokens
        self.stats.llm_output_tokens = self.llm.total_output_tokens
        self.stats.tts_characters = self.tts.total_characters_synthesized

        logger.info(
            f"Voice agent session ended: turns={self.stats.turn_count}, "
            f"cost=${self.stats.calculate_cost():.4f}"
        )

    def _get_result(self) -> Dict[str, Any]:
        """Get session result."""
        return {
            "transcript": self.transcript,
            "stats": {
                "started_at": self.stats.started_at.isoformat(),
                "ended_at": self.stats.ended_at.isoformat() if self.stats.ended_at else None,
                "turn_count": self.stats.turn_count,
                "whisper_seconds": self.stats.whisper_seconds,
                "llm_input_tokens": self.stats.llm_input_tokens,
                "llm_output_tokens": self.stats.llm_output_tokens,
                "tts_characters": self.stats.tts_characters,
                "estimated_cost_usd": self.stats.calculate_cost()
            },
            "action": self._pending_action,
            "context": self.context
        }


# Import for type hints
from dialer.voice_agent.plugins.base import ExternalPlugin
