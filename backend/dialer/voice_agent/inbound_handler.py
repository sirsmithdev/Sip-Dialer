"""
Voice Agent Inbound Call Handler.

Integrates the VoiceAgentSession with the PJSUA2 SIP engine
to handle inbound calls with AI-powered conversation.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InboundCallContext:
    """Context for an inbound call."""
    call_id: str
    caller_number: str
    called_number: str
    agent_config_id: str
    organization_id: str
    started_at: datetime


class VoiceAgentInboundHandler:
    """
    Handles inbound calls by routing them to VoiceAgentSession.

    This handler:
    1. Receives incoming call notifications from SIP engine
    2. Matches the called DID to an InboundRoute
    3. Loads the appropriate VoiceAgentConfig
    4. Creates a VoiceAgentSession to handle the conversation
    5. Manages audio streaming between SIP and voice agent
    """

    def __init__(self, db_session_factory: Callable):
        """
        Initialize the inbound handler.

        Args:
            db_session_factory: Async factory for database sessions
        """
        self.db_session_factory = db_session_factory
        self.active_sessions: Dict[str, Any] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the event loop for async operations."""
        self._loop = loop

    async def handle_incoming_call(
        self,
        call_id: str,
        caller_number: str,
        called_number: str,
        sip_call: Any,  # SIPCall instance
        answer_callback: Callable,
        hangup_callback: Callable
    ) -> bool:
        """
        Handle an incoming call.

        Args:
            call_id: Unique call identifier
            caller_number: Caller's phone number
            called_number: Called DID
            sip_call: SIPCall instance from pjsua_client
            answer_callback: Callback to answer the call
            hangup_callback: Callback to hang up the call

        Returns:
            True if call was handled, False if no route matched
        """
        logger.info(f"Incoming call {call_id}: {caller_number} -> {called_number}")

        async with self.db_session_factory() as db:
            # Import here to avoid circular imports
            from sqlalchemy import select, and_
            from app.models.voice_agent import InboundRoute, VoiceAgentConfig, VoiceAgentStatus

            # Find matching route
            route = await self._find_matching_route(db, called_number)

            if not route:
                logger.info(f"No route found for {called_number}, rejecting call")
                return False

            # Get agent config
            result = await db.execute(
                select(VoiceAgentConfig).where(
                    and_(
                        VoiceAgentConfig.id == route.agent_config_id,
                        VoiceAgentConfig.status == VoiceAgentStatus.ACTIVE
                    )
                )
            )
            agent_config = result.scalar_one_or_none()

            if not agent_config:
                logger.warning(f"Agent config {route.agent_config_id} not found or inactive")
                return False

            # Answer the call
            logger.info(f"Answering call {call_id} with agent: {agent_config.name}")
            answer_callback()

            # Create context
            context = InboundCallContext(
                call_id=call_id,
                caller_number=caller_number,
                called_number=called_number,
                agent_config_id=agent_config.id,
                organization_id=agent_config.organization_id,
                started_at=datetime.utcnow()
            )

            # Start voice agent session in background
            asyncio.create_task(
                self._run_voice_agent_session(
                    context=context,
                    agent_config=agent_config,
                    sip_call=sip_call,
                    hangup_callback=hangup_callback,
                    db_session_factory=self.db_session_factory
                )
            )

            return True

    async def _find_matching_route(self, db, called_number: str):
        """Find a matching inbound route for the called number."""
        from sqlalchemy import select
        from app.models.voice_agent import InboundRoute

        # Get all active routes ordered by priority
        result = await db.execute(
            select(InboundRoute)
            .where(InboundRoute.is_active == True)
            .order_by(InboundRoute.priority)
        )
        routes = result.scalars().all()

        for route in routes:
            if self._matches_pattern(called_number, route.did_pattern):
                return route

        return None

    def _matches_pattern(self, number: str, pattern: str) -> bool:
        """
        Check if a phone number matches a DID pattern.

        Patterns can use * as a wildcard for any characters.
        Examples:
        - "+1555*" matches "+15551234567"
        - "*" matches any number
        - "+18001234567" matches exactly
        """
        import fnmatch
        return fnmatch.fnmatch(number, pattern)

    async def _run_voice_agent_session(
        self,
        context: InboundCallContext,
        agent_config: Any,
        sip_call: Any,
        hangup_callback: Callable,
        db_session_factory: Callable
    ):
        """Run the voice agent session for a call."""
        from dialer.voice_agent.session import VoiceAgentSession, VoiceAgentConfig as VAConfig
        from app.core.security import decrypt_value

        logger.info(f"Starting voice agent session for call {context.call_id}")

        try:
            # Get OpenAI API key
            api_key = None
            if agent_config.openai_api_key_encrypted:
                api_key = decrypt_value(agent_config.openai_api_key_encrypted)

            if not api_key:
                # Try to get from organization settings
                api_key = await self._get_org_api_key(
                    db_session_factory,
                    context.organization_id
                )

            if not api_key:
                logger.error("No OpenAI API key available")
                hangup_callback()
                return

            # Build plugins from config
            plugins = await self._build_plugins(agent_config.plugins_config or [])

            # Create voice agent config
            va_config = VAConfig(
                openai_api_key=api_key,
                llm_model=agent_config.llm_model,
                tts_voice=agent_config.tts_voice,
                tts_model=agent_config.tts_model,
                whisper_model=agent_config.whisper_model,
                system_prompt=agent_config.system_prompt,
                greeting_message=agent_config.greeting_message,
                fallback_message=agent_config.fallback_message,
                goodbye_message=agent_config.goodbye_message,
                transfer_message=agent_config.transfer_message,
                max_turns=agent_config.max_turns,
                silence_timeout_seconds=agent_config.silence_timeout_seconds,
                max_call_duration_seconds=agent_config.max_call_duration_seconds,
                vad_energy_threshold=agent_config.vad_energy_threshold,
                vad_silence_duration=agent_config.vad_silence_duration,
                vad_min_speech_duration=agent_config.vad_min_speech_duration,
                llm_temperature=agent_config.llm_temperature,
                llm_max_tokens=agent_config.llm_max_tokens,
                plugins=plugins
            )

            # Create audio callbacks for SIP call
            audio_queue = asyncio.Queue()

            async def play_audio(audio_bytes: bytes):
                """Play audio to the caller via SIP."""
                try:
                    audio_media = sip_call.get_audio_media()
                    if audio_media:
                        # This would use the media handler to play audio
                        # Implementation depends on pjsua2 audio port details
                        pass
                except Exception as e:
                    logger.error(f"Error playing audio: {e}")

            async def get_audio() -> Optional[bytes]:
                """Get audio from the caller via SIP."""
                try:
                    return await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    return None

            # Create session
            session = VoiceAgentSession(
                config=va_config,
                play_audio_callback=play_audio,
                get_audio_callback=get_audio,
                context={
                    "caller_number": context.caller_number,
                    "called_number": context.called_number,
                    "call_id": context.call_id
                }
            )

            self.active_sessions[context.call_id] = session

            # Run the session
            result = await session.start()

            # Save conversation to database
            await self._save_conversation(
                db_session_factory=db_session_factory,
                context=context,
                result=result
            )

        except Exception as e:
            logger.error(f"Voice agent session error: {e}", exc_info=True)
        finally:
            # Clean up
            self.active_sessions.pop(context.call_id, None)

            # Hang up if still connected
            try:
                hangup_callback()
            except:
                pass

    async def _get_org_api_key(self, db_session_factory, organization_id: str) -> Optional[str]:
        """Get OpenAI API key from organization settings."""
        # This would fetch from organization settings table
        # For now, try environment variable
        import os
        return os.getenv("OPENAI_API_KEY")

    async def _build_plugins(self, plugins_config: list) -> list:
        """Build plugin instances from config."""
        from dialer.voice_agent.plugins import (
            CustomerLookupPlugin,
            MockCustomerLookupPlugin,
            TransferCallPlugin,
            HangupCallPlugin,
            EscalatePlugin
        )

        plugins = []
        plugin_classes = {
            "customer_lookup": CustomerLookupPlugin,
            "mock_customer_lookup": MockCustomerLookupPlugin,
            "transfer_call": TransferCallPlugin,
            "hangup_call": HangupCallPlugin,
            "escalate": EscalatePlugin,
        }

        for config in plugins_config:
            plugin_type = config.get("type")
            if plugin_type in plugin_classes:
                plugin_cls = plugin_classes[plugin_type]
                plugin_args = config.get("config", {})
                try:
                    plugin = plugin_cls(**plugin_args)
                    plugins.append(plugin)
                except Exception as e:
                    logger.warning(f"Failed to create plugin {plugin_type}: {e}")

        return plugins

    async def _save_conversation(
        self,
        db_session_factory: Callable,
        context: InboundCallContext,
        result: Dict[str, Any]
    ):
        """Save the conversation to the database."""
        from app.models.voice_agent import VoiceAgentConversation, ResolutionStatus

        async with db_session_factory() as db:
            # Determine resolution status
            action = result.get("action", {})
            if action:
                if action.get("action") == "transfer":
                    resolution = ResolutionStatus.TRANSFERRED
                elif action.get("action") == "hangup":
                    resolution = ResolutionStatus.RESOLVED
                else:
                    resolution = ResolutionStatus.ABANDONED
            else:
                resolution = ResolutionStatus.ABANDONED

            stats = result.get("stats", {})

            conversation = VoiceAgentConversation(
                agent_config_id=context.agent_config_id,
                organization_id=context.organization_id,
                caller_number=context.caller_number,
                called_number=context.called_number,
                call_duration_seconds=int(
                    (datetime.utcnow() - context.started_at).total_seconds()
                ),
                started_at=context.started_at,
                ended_at=datetime.utcnow(),
                transcript=result.get("transcript", []),
                turn_count=stats.get("turn_count", 0),
                resolution_status=resolution,
                transfer_destination=action.get("destination"),
                transfer_reason=action.get("reason"),
                whisper_seconds=stats.get("whisper_seconds", 0),
                llm_input_tokens=stats.get("llm_input_tokens", 0),
                llm_output_tokens=stats.get("llm_output_tokens", 0),
                tts_characters=stats.get("tts_characters", 0),
                estimated_cost_usd=stats.get("estimated_cost_usd", 0)
            )

            db.add(conversation)
            await db.commit()

            logger.info(f"Saved conversation for call {context.call_id}")


# Global handler instance
_inbound_handler: Optional[VoiceAgentInboundHandler] = None


def get_inbound_handler() -> Optional[VoiceAgentInboundHandler]:
    """Get the global inbound handler instance."""
    return _inbound_handler


def init_inbound_handler(db_session_factory: Callable) -> VoiceAgentInboundHandler:
    """Initialize the global inbound handler."""
    global _inbound_handler
    _inbound_handler = VoiceAgentInboundHandler(db_session_factory)
    return _inbound_handler
