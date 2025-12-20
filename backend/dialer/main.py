"""
Dialer Engine Main Entry Point.

This module starts the dialer engine that manages outbound calls
by connecting directly as a PJSIP extension to the UCM6302/PBX.

The dialer acts like a SIP softphone - it registers with the PBX,
then originates calls using SIP INVITE with full RTP media support.
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from minio import Minio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.sip_settings import SIPSettings
from app.models.audio import AudioFile

# Import SIP engine components
try:
    from dialer.sip_engine import SIPEngine, SIPCall, MediaHandler
    from dialer.sip_engine.pjsua_client import PJSUA2_AVAILABLE, RegistrationState, CallState
    SIP_ENGINE_AVAILABLE = True
except ImportError:
    try:
        # Try relative import if running as module
        from .sip_engine import SIPEngine, SIPCall, MediaHandler
        from .sip_engine.pjsua_client import PJSUA2_AVAILABLE, RegistrationState, CallState
        SIP_ENGINE_AVAILABLE = True
    except ImportError as e:
        SIP_ENGINE_AVAILABLE = False
        PJSUA2_AVAILABLE = False
        SIPCall = None  # Define for type hints
        MediaHandler = None
        SIPEngine = None
        RegistrationState = None
        CallState = None
        logging.warning(f"SIP engine not available: {e}")

# Import IVR executor
try:
    from dialer.ivr.ivr_executor import IVRExecutor, IVRContext
    IVR_AVAILABLE = True
except ImportError:
    try:
        from .ivr.ivr_executor import IVRExecutor, IVRContext
        IVR_AVAILABLE = True
    except ImportError:
        IVR_AVAILABLE = False
        IVRExecutor = None
        IVRContext = None

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DialerEngine:
    """
    Main dialer engine class using PJSUA2 SIP engine.

    This engine manages:
    - SIP registration with UCM/PBX
    - Outbound call origination
    - Campaign processing
    - IVR execution
    """

    def __init__(self):
        self.running = False
        self.sip_engine: Optional[SIPEngine] = None
        self.active_calls: Dict[str, SIPCall] = {}

        # Database configuration
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://autodialer:autodialer_secret@localhost:5432/autodialer"
        )

        # Local SIP port (different from UCM's 5060)
        self.local_sip_port = int(os.getenv("LOCAL_SIP_PORT", "5061"))

        # Audio file base path (local cache)
        self.audio_base_path = os.getenv("AUDIO_BASE_PATH", "/var/lib/autodialer/audio")

        # MinIO configuration
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.minio_bucket = os.getenv("MINIO_BUCKET_AUDIO", "audio-files")
        self.minio_client = None

        # Audio file cache (maps audio_file_id to local path)
        self._audio_cache: Dict[str, str] = {}

    async def _get_sip_settings(self) -> Optional[SIPSettings]:
        """Load SIP settings from database."""
        engine = create_async_engine(self.db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(
                select(SIPSettings).where(SIPSettings.is_active == True).limit(1)
            )
            settings = result.scalar_one_or_none()

            if settings:
                # Decrypt password
                try:
                    from app.core.security import decrypt_value
                    settings._decrypted_password = decrypt_value(settings.sip_password_encrypted)
                except Exception as e:
                    logger.error(f"Failed to decrypt SIP password: {e}")
                    settings._decrypted_password = ""

            return settings

        await engine.dispose()

    def _resolve_audio_file(self, audio_file_id: str) -> str:
        """Resolve audio file ID to filesystem path, downloading from MinIO if needed."""
        # Check cache first
        if audio_file_id in self._audio_cache:
            cached_path = self._audio_cache[audio_file_id]
            if os.path.exists(cached_path):
                return cached_path

        # Ensure cache directory exists
        os.makedirs(self.audio_base_path, exist_ok=True)

        local_path = os.path.join(self.audio_base_path, f"{audio_file_id}.wav")

        # If already downloaded, use it
        if os.path.exists(local_path):
            self._audio_cache[audio_file_id] = local_path
            return local_path

        # Initialize MinIO client if needed
        if not self.minio_client:
            self.minio_client = Minio(
                self.minio_endpoint,
                access_key=self.minio_access_key,
                secret_key=self.minio_secret_key,
                secure=False
            )

        # Look up audio file in database to get MinIO path (synchronous)
        try:
            minio_path = self._get_audio_minio_path_sync(audio_file_id)

            if minio_path:
                logger.info(f"Downloading audio file {audio_file_id} from MinIO: {minio_path}")
                self.minio_client.fget_object(self.minio_bucket, minio_path, local_path)
                self._audio_cache[audio_file_id] = local_path
                logger.info(f"Audio file downloaded to {local_path}")
                return local_path
            else:
                logger.error(f"Audio file {audio_file_id} not found in database")
        except Exception as e:
            logger.error(f"Failed to download audio file {audio_file_id}: {e}")
            import traceback
            traceback.print_exc()

        return local_path

    def _get_audio_minio_path_sync(self, audio_file_id: str) -> Optional[str]:
        """Get the MinIO path for an audio file from the database (synchronous)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        # Convert async URL to sync URL
        sync_db_url = self.db_url.replace("+asyncpg", "")

        engine = create_engine(sync_db_url)
        try:
            with Session(engine) as session:
                result = session.execute(
                    select(AudioFile).where(AudioFile.id == audio_file_id)
                )
                audio = result.scalar_one_or_none()

                if audio:
                    # Prefer transcoded WAV, fall back to original
                    if audio.transcoded_paths and "wav" in audio.transcoded_paths:
                        return audio.transcoded_paths["wav"]
                    return audio.storage_path
                return None
        finally:
            engine.dispose()

    async def start(self):
        """Start the dialer engine."""
        self.running = True
        logger.info("Starting Dialer Engine (PJSUA2 SIP Mode)...")

        # Check if SIP engine is available
        if not SIP_ENGINE_AVAILABLE:
            logger.error(
                "SIP engine not available. Please ensure the sip_engine module is properly installed."
            )
            return

        if not PJSUA2_AVAILABLE:
            logger.warning(
                "PJSUA2 not available. The dialer will not be able to make calls. "
                "Install PJSIP with Python bindings to enable full SIP support. "
                "On Windows, you may need to build from source: https://github.com/pjsip/pjproject"
            )
            # Continue running but won't be able to make calls
            await self._wait_for_shutdown()
            return

        # Load SIP settings from database
        settings = await self._get_sip_settings()

        if not settings:
            logger.error("No SIP settings found in database. Configure SIP settings in the UI.")
            logger.info("Dialer engine will wait for SIP settings to be configured...")

            # Wait for settings to be configured
            while self.running and not settings:
                await asyncio.sleep(30)
                settings = await self._get_sip_settings()
                if settings:
                    logger.info("SIP settings found, initializing...")

        if not self.running:
            return

        # Initialize SIP engine
        self.sip_engine = SIPEngine()

        try:
            # Initialize PJSIP library
            self.sip_engine.initialize(
                sip_server=settings.sip_server,
                sip_port=settings.sip_port,
                local_port=self.local_sip_port,
                rtp_port_start=settings.rtp_port_start,
                rtp_port_end=settings.rtp_port_end,
                codecs=self._map_codecs(settings.codecs),
                log_level=3 if os.getenv("DEBUG") else 2
            )

            # Register with UCM
            self.sip_engine.register(
                username=settings.sip_username,
                password=settings._decrypted_password,
                transport=settings.sip_transport.value if hasattr(settings.sip_transport, 'value') else str(settings.sip_transport)
            )

            # Wait for registration
            await self._wait_for_registration(timeout=30)

            if self.sip_engine.is_registered:
                logger.info("Dialer engine ready - registered with SIP server")
                # Update database status
                await self._update_connection_status("REGISTERED")
            else:
                logger.warning(f"Registration state: {self.sip_engine.registration_state}")
                await self._update_connection_status("FAILED")

            # Process campaigns
            await self.process_campaigns()

        except Exception as e:
            logger.error(f"Dialer engine error: {e}")
            await self._update_connection_status("FAILED", str(e))
            raise

    def _map_codecs(self, codec_list: list) -> list:
        """Map codec names to PJSUA2 format."""
        codec_map = {
            "ulaw": "PCMU/8000",
            "alaw": "PCMA/8000",
            "g722": "G722/16000",
            "g729": "G729/8000",
            "gsm": "GSM/8000",
        }
        return [codec_map.get(c, c) for c in codec_list]

    async def _wait_for_registration(self, timeout: float = 30):
        """Wait for SIP registration to complete."""
        start_time = asyncio.get_event_loop().time()

        while self.running:
            if self.sip_engine.is_registered:
                return True

            if self.sip_engine.registration_state == RegistrationState.FAILED:
                logger.error("SIP registration failed")
                return False

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.error(f"SIP registration timeout after {timeout}s")
                return False

            await asyncio.sleep(0.5)

        return False

    async def _update_connection_status(self, status: str, error: str = None):
        """Update connection status in database and publish to WebSocket."""
        extension = None
        server = None

        try:
            engine = create_async_engine(self.db_url)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with async_session() as session:
                result = await session.execute(
                    select(SIPSettings).where(SIPSettings.is_active == True).limit(1)
                )
                settings = result.scalar_one_or_none()

                if settings:
                    from app.models.sip_settings import ConnectionStatus
                    settings.connection_status = ConnectionStatus(status)
                    extension = settings.sip_username
                    server = settings.sip_server
                    if error:
                        settings.last_error = error
                    if status == "REGISTERED":
                        from datetime import datetime
                        settings.last_connected_at = datetime.utcnow()
                        settings.last_error = None

                    await session.commit()

            await engine.dispose()
        except Exception as e:
            logger.error(f"Failed to update connection status: {e}")

        # Publish SIP status to WebSocket clients via Redis
        await self._publish_sip_status(status, extension, server, error)

    async def _publish_sip_status(
        self,
        status: str,
        extension: str = None,
        server: str = None,
        error: str = None
    ):
        """Publish SIP status to WebSocket clients via Redis."""
        import redis.asyncio as redis
        import json
        from datetime import datetime

        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)

            active_calls = len(self.active_calls) if self.active_calls else 0

            message = json.dumps({
                "type": "sip.status",
                "data": {
                    "status": status.lower(),
                    "extension": extension,
                    "server": server,
                    "active_calls": active_calls,
                    "error": error,
                    "last_updated": datetime.utcnow().isoformat()
                }
            })

            # Publish to WebSocket subscribers
            await r.publish("ws:sip_status", message)

            # Also store in a key for direct access (e.g., connection test service)
            status_data = json.dumps({
                "status": status.lower(),
                "extension": extension,
                "server": server,
                "active_calls": active_calls,
                "error": error,
                "last_updated": datetime.utcnow().isoformat()
            })
            await r.set("dialer:sip_status", status_data, ex=60)  # Expire after 60 seconds

            logger.debug(f"Published SIP status: {status}")
            await r.aclose()

        except Exception as e:
            logger.error(f"Failed to publish SIP status: {e}")

    async def _wait_for_shutdown(self):
        """Wait for shutdown signal when SIP is not available."""
        while self.running:
            await asyncio.sleep(1)

    async def process_campaigns(self):
        """Process active campaigns and initiate calls."""
        logger.info("Starting campaign processing loop...")

        # Start Redis listener for test calls
        asyncio.create_task(self._listen_for_test_calls())

        while self.running:
            try:
                # Check if still registered
                if not self.sip_engine.is_registered:
                    logger.warning("Lost SIP registration, waiting for reconnect...")
                    await asyncio.sleep(5)
                    continue

                # TODO: Implement campaign processing
                # 1. Query database for active campaigns
                # 2. Get contacts to dial based on campaign settings
                # 3. Check concurrent call limits
                # 4. Initiate calls

                # For now, just sleep
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing campaigns: {e}")
                await asyncio.sleep(5)

    async def _listen_for_test_calls(self):
        """Listen for test call requests via Redis."""
        import redis.asyncio as redis
        import json

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        logger.info(f"Listening for test calls on Redis: {redis_url}")

        try:
            r = redis.from_url(redis_url)
            pubsub = r.pubsub()
            await pubsub.subscribe("dialer:test_call")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        destination = data.get("destination")
                        caller_id = data.get("caller_id", "")
                        audio_file = data.get("audio_file")  # Optional audio file to play

                        if destination:
                            logger.info(f"Received test call request: {destination}")

                            # If audio file specified, create a simple IVR flow
                            ivr_flow = None
                            if audio_file:
                                ivr_flow = {
                                    "nodes": [
                                        {"id": "start", "type": "start", "data": {}},
                                        {"id": "play", "type": "play_audio", "data": {"audio_file_id": audio_file}},
                                        {"id": "hangup", "type": "hangup", "data": {}}
                                    ],
                                    "edges": [
                                        {"source": "start", "target": "play"},
                                        {"source": "play", "target": "hangup"}
                                    ],
                                    "start_node": "start"
                                }

                            call = await self.make_call(destination, caller_id, ivr_flow)
                            if call:
                                asyncio.create_task(self._monitor_test_call(call, r))
                    except Exception as e:
                        logger.error(f"Error processing test call request: {e}")

        except Exception as e:
            logger.error(f"Redis listener error: {e}")

    async def _monitor_test_call(self, call, redis_client):
        """Monitor a test call and publish status updates."""
        import json
        from datetime import datetime

        try:
            start_time = asyncio.get_event_loop().time()
            max_duration = 120  # 2 minutes max

            while self.running:
                state = call.state
                elapsed = asyncio.get_event_loop().time() - start_time
                state_str = state.value if hasattr(state, 'value') else str(state)

                # Publish status update to legacy channel
                status = {
                    "call_id": call.call_id,
                    "state": state_str,
                    "elapsed": round(elapsed, 1)
                }
                await redis_client.publish("dialer:call_status", json.dumps(status))

                # Also publish to WebSocket channel for frontend
                ws_message = json.dumps({
                    "type": "call.update",
                    "data": {
                        "call_id": call.call_id,
                        "phone_number": getattr(call, 'destination', 'unknown'),
                        "status": state_str,
                        "direction": "outbound",
                        "duration_seconds": int(elapsed),
                        "started_at": datetime.utcnow().isoformat()
                    }
                })
                await redis_client.publish("ws:calls", ws_message)

                if state in (CallState.DISCONNECTED, CallState.FAILED):
                    logger.info(f"Test call {call.call_id} ended: {state}")
                    break

                if elapsed > max_duration:
                    logger.info(f"Test call {call.call_id} timeout, hanging up")
                    call.hangup()
                    break

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error monitoring test call: {e}")

    async def make_call(
        self,
        destination: str,
        caller_id: str = "",
        ivr_flow_definition: Optional[Dict] = None,
        campaign_id: Optional[str] = None,
        contact_id: Optional[str] = None
    ) -> Optional["SIPCall"]:
        """
        Initiate an outbound call.

        Args:
            destination: Phone number to call
            caller_id: Caller ID to display
            ivr_flow_definition: Optional IVR flow to execute on answer
            campaign_id: Associated campaign ID
            contact_id: Associated contact ID

        Returns:
            SIPCall object or None if failed
        """
        if not self.sip_engine or not self.sip_engine.is_registered:
            logger.error("Cannot make call - not registered")
            return None

        try:
            # Make the call
            call = self.sip_engine.make_call(destination, caller_id)
            self.active_calls[call.info.call_id] = call

            logger.info(f"Call initiated to {destination} (ID: {call.info.call_id})")

            # If IVR flow provided, execute it when call is answered
            if ivr_flow_definition and IVR_AVAILABLE:
                asyncio.create_task(
                    self._execute_ivr_on_answer(
                        call,
                        ivr_flow_definition,
                        campaign_id,
                        contact_id
                    )
                )

            return call

        except Exception as e:
            logger.error(f"Failed to make call: {e}")
            return None

    async def _execute_ivr_on_answer(
        self,
        call: "SIPCall",
        ivr_flow_definition: Dict,
        campaign_id: Optional[str],
        contact_id: Optional[str]
    ):
        """Wait for call to be answered, then execute IVR."""
        # Wait for call to be answered
        while call.info.state not in (CallState.CONFIRMED, CallState.DISCONNECTED, CallState.FAILED):
            await asyncio.sleep(0.1)

        if call.info.state != CallState.CONFIRMED:
            logger.info(f"Call {call.info.call_id} not answered, skipping IVR")
            return

        logger.info(f"Call {call.info.call_id} answered, starting IVR")

        try:
            # Create media handler
            media = MediaHandler(call)

            # Create IVR executor
            executor = IVRExecutor(
                call=call,
                media_handler=media,
                audio_file_resolver=self._resolve_audio_file
            )

            # Create context
            context = IVRContext(
                call_id=call.info.call_id,
                campaign_id=campaign_id,
                contact_id=contact_id
            )

            # Execute IVR flow
            result = await executor.execute_flow(ivr_flow_definition, context)

            logger.info(
                f"IVR completed for call {call.info.call_id}: "
                f"state={result.state.value}, "
                f"responses={result.survey_responses}"
            )

            # TODO: Save IVR results to database

        except Exception as e:
            logger.error(f"IVR execution error: {e}")

        finally:
            # Clean up call if still active
            if call.info.call_id in self.active_calls:
                del self.active_calls[call.info.call_id]

    async def hangup_call(self, call_id: str):
        """Hang up a call by ID."""
        call = self.active_calls.get(call_id)
        if call:
            call.hangup()
            del self.active_calls[call_id]
        elif self.sip_engine:
            self.sip_engine.hangup_call(call_id)

    async def stop(self):
        """Stop the dialer engine."""
        logger.info("Stopping Dialer Engine...")
        self.running = False

        # Hang up all active calls
        for call_id in list(self.active_calls.keys()):
            await self.hangup_call(call_id)

        # Shutdown SIP engine
        if self.sip_engine:
            self.sip_engine.shutdown()
            self.sip_engine = None

        # Update status
        await self._update_connection_status("DISCONNECTED")

        logger.info("Dialer Engine stopped")


async def main():
    """Main entry point."""
    engine = DialerEngine()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(engine.stop())

    # Windows doesn't support add_signal_handler, use different approach
    if sys.platform != 'win32':
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

    try:
        await engine.start()
    except KeyboardInterrupt:
        await engine.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await engine.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
