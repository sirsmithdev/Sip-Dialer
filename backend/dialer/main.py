"""
Dialer Engine Main Entry Point.

This module starts the dialer engine that manages outbound calls
by connecting directly as a PJSIP extension to the UCM6302/PBX.

The dialer acts like a SIP softphone - it registers with the PBX,
then originates calls using SIP INVITE with full RTP media support.

Version: 2.0.3 - Add task references to prevent GC during shutdown (2025-12-22)
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Dict, Any, List

import ssl
from urllib.parse import urlparse

from sqlalchemy import select, and_, or_, text, cast, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from minio import Minio
import boto3
from botocore.config import Config as BotoConfig

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.sip_settings import SIPSettings
from app.models.audio import AudioFile
from app.models.campaign import Campaign, CampaignContact, CampaignStatus, ContactStatus, CallDisposition
from app.models.contact import Contact
from app.models.ivr import IVRFlow, IVRFlowVersion

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

# Import call manager
try:
    from dialer.call_manager import ConcurrentCallManager, PendingContact
    CALL_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from .call_manager import ConcurrentCallManager, PendingContact
        CALL_MANAGER_AVAILABLE = True
    except ImportError:
        CALL_MANAGER_AVAILABLE = False
        ConcurrentCallManager = None
        PendingContact = None

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

        # S3/Spaces configuration (supports MinIO, DO Spaces, AWS S3)
        self.s3_endpoint = os.getenv("S3_ENDPOINT", os.getenv("MINIO_ENDPOINT", "localhost:9000"))
        self.s3_access_key = os.getenv("S3_ACCESS_KEY", os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
        self.s3_secret_key = os.getenv("S3_SECRET_KEY", os.getenv("MINIO_SECRET_KEY", "minioadmin"))
        self.s3_bucket = os.getenv("S3_BUCKET", os.getenv("MINIO_BUCKET_AUDIO", "audio-files"))
        self.s3_secure = os.getenv("S3_SECURE", "false").lower() == "true"
        self.s3_region = os.getenv("S3_REGION", "us-east-1")
        self.s3_client = None
        self.minio_client = None  # Legacy support

        # Audio file cache (maps audio_file_id to local path)
        self._audio_cache: Dict[str, str] = {}

        # Call manager for concurrent calls
        self.call_manager: Optional[ConcurrentCallManager] = None
        self.global_max_concurrent = int(os.getenv("GLOBAL_MAX_CONCURRENT_CALLS", "50"))

        # Campaign processing interval (seconds)
        self.campaign_poll_interval = float(os.getenv("CAMPAIGN_POLL_INTERVAL", "2.0"))

        # Map call_id to campaign_contact info for result tracking
        self._call_contacts: Dict[str, Dict[str, str]] = {}

        # Redis URL
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Background task references (prevents garbage collection)
        self._test_call_listener_task: Optional[asyncio.Task] = None
        self._call_monitor_task: Optional[asyncio.Task] = None

    def _task_done_callback(self, task: asyncio.Task):
        """Callback for when a background task completes or fails."""
        task_name = task.get_name() if hasattr(task, 'get_name') else str(task)
        try:
            # Check if task raised an exception
            exc = task.exception()
            if exc:
                logger.error(f"Background task {task_name} failed with exception: {exc}")
        except asyncio.CancelledError:
            logger.info(f"Background task {task_name} was cancelled (normal during shutdown)")
        except asyncio.InvalidStateError:
            # Task is still running or hasn't started
            logger.debug(f"Background task {task_name} state check: still pending")

    def _get_redis_client(self):
        """Get Redis client with SSL support for DO Managed Redis."""
        import redis.asyncio as redis

        if self.redis_url.startswith("rediss://"):
            # DO Managed Redis uses self-signed certs
            return redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                ssl_cert_reqs=None  # Disable cert verification for DO
            )
        else:
            return redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    def _get_async_db_url_and_connect_args(self):
        """Get async database URL and connect_args with SSL support for DO."""
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        db_url = self.db_url
        connect_args = {}

        # Ensure asyncpg driver
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://") and "+asyncpg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        parsed = urlparse(db_url)

        # Check if this is a DO managed database (requires SSL)
        is_do_db = "db.ondigitalocean.com" in db_url or ":25060/" in db_url

        if is_do_db:
            # Create SSL context for DO managed database
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_context

        # Remove sslmode from URL (asyncpg doesn't support it)
        if parsed.query:
            params = parse_qs(parsed.query)
            params.pop("sslmode", None)
            params.pop("ssl", None)
            new_query = urlencode({k: v[0] for k, v in params.items()}, doseq=False) if params else ""
            db_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

        return db_url, connect_args

    async def _get_sip_settings(self) -> Optional[SIPSettings]:
        """Load SIP settings from database."""
        db_url, connect_args = self._get_async_db_url_and_connect_args()
        engine = create_async_engine(db_url, connect_args=connect_args)
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

    def _get_s3_client(self):
        """Get or create S3 client (supports MinIO, DO Spaces, AWS S3)."""
        if self.s3_client is None:
            # Check if using DO Spaces or AWS S3 (vs local MinIO)
            is_spaces = "digitaloceanspaces.com" in self.s3_endpoint
            is_aws = "amazonaws.com" in self.s3_endpoint

            if is_spaces or is_aws:
                # Use boto3 for DO Spaces / AWS S3
                endpoint_url = f"https://{self.s3_endpoint}" if self.s3_secure else f"http://{self.s3_endpoint}"
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key,
                    region_name=self.s3_region,
                    config=BotoConfig(signature_version="s3v4")
                )
                logger.info(f"Initialized S3 client for {self.s3_endpoint}")
            else:
                # Use MinIO client for local development
                self.minio_client = Minio(
                    self.s3_endpoint,
                    access_key=self.s3_access_key,
                    secret_key=self.s3_secret_key,
                    secure=self.s3_secure
                )
                logger.info(f"Initialized MinIO client for {self.s3_endpoint}")

        return self.s3_client or self.minio_client

    def _download_from_s3(self, s3_path: str, local_path: str) -> bool:
        """Download a file from S3/Spaces/MinIO."""
        try:
            client = self._get_s3_client()

            if isinstance(client, Minio):
                # MinIO client
                client.fget_object(self.s3_bucket, s3_path, local_path)
            else:
                # boto3 client (DO Spaces / AWS S3)
                client.download_file(self.s3_bucket, s3_path, local_path)

            return True
        except Exception as e:
            logger.error(f"Failed to download {s3_path}: {e}")
            return False

    def _resolve_audio_file(self, audio_file_id: str) -> str:
        """Resolve audio file ID to filesystem path, downloading from S3/Spaces if needed."""
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

        # Look up audio file in database to get S3 path (synchronous)
        try:
            s3_path = self._get_audio_s3_path_sync(audio_file_id)

            if s3_path:
                logger.info(f"Downloading audio file {audio_file_id} from S3: {s3_path}")
                if self._download_from_s3(s3_path, local_path):
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

    def _get_audio_s3_path_sync(self, audio_file_id: str) -> Optional[str]:
        """Get the S3 path for an audio file from the database (synchronous)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        # Convert async URL to sync URL and handle SSL for DO managed DB
        sync_db_url = self.db_url.replace("+asyncpg", "")
        if sync_db_url.startswith("postgres://"):
            sync_db_url = sync_db_url.replace("postgres://", "postgresql://", 1)

        # Add sslmode for DO managed databases
        is_do_db = "db.ondigitalocean.com" in sync_db_url or ":25060/" in sync_db_url
        if is_do_db and "sslmode" not in sync_db_url:
            sync_db_url += "&sslmode=require" if "?" in sync_db_url else "?sslmode=require"

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
            # Get transport type from settings
            transport_type = settings.sip_transport.value if hasattr(settings.sip_transport, 'value') else str(settings.sip_transport)

            # Initialize PJSIP library with correct transport
            self.sip_engine.initialize(
                sip_server=settings.sip_server,
                sip_port=settings.sip_port,
                local_port=self.local_sip_port,
                rtp_port_start=settings.rtp_port_start,
                rtp_port_end=settings.rtp_port_end,
                codecs=self._map_codecs(settings.codecs),
                log_level=3 if os.getenv("DEBUG") else 2,
                transport=transport_type
            )

            # Register with UCM
            self.sip_engine.register(
                username=settings.sip_username,
                password=settings._decrypted_password,
                transport=transport_type
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
            db_url, connect_args = self._get_async_db_url_and_connect_args()
            engine = create_async_engine(db_url, connect_args=connect_args)
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
        import json
        from datetime import datetime

        try:
            r = self._get_redis_client()
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
            await r.set("dialer:sip_status", status_data, ex=120)  # Expire after 120 seconds

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

        # Initialize call manager
        if CALL_MANAGER_AVAILABLE:
            self.call_manager = ConcurrentCallManager(
                global_max_concurrent=self.global_max_concurrent,
                call_initiator=self._make_campaign_call
            )
            await self.call_manager.start_processing()
            logger.info(f"Call manager initialized with max {self.global_max_concurrent} concurrent calls")
        else:
            logger.warning("Call manager not available, concurrent call management disabled")

        # Start Redis listener for test calls (keep reference to prevent GC)
        self._test_call_listener_task = asyncio.create_task(self._listen_for_test_calls())
        self._test_call_listener_task.add_done_callback(self._task_done_callback)

        # Start call monitor task (keep reference to prevent GC)
        self._call_monitor_task = asyncio.create_task(self._monitor_active_calls())
        self._call_monitor_task.add_done_callback(self._task_done_callback)

        status_publish_counter = 0
        while self.running:
            try:
                # Check if still registered
                if not self.sip_engine.is_registered:
                    logger.warning("Lost SIP registration, waiting for reconnect...")
                    await asyncio.sleep(5)
                    continue

                # Process active campaigns
                await self._process_active_campaigns()

                # Publish call manager status periodically (every 5 iterations)
                status_publish_counter += 1
                if status_publish_counter >= 5:
                    await self._publish_call_manager_status()
                    status_publish_counter = 0

                # Wait before next poll
                await asyncio.sleep(self.campaign_poll_interval)

            except Exception as e:
                logger.error(f"Error processing campaigns: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

    async def _process_active_campaigns(self):
        """Query and process all active campaigns."""
        db_url, connect_args = self._get_async_db_url_and_connect_args()
        engine = create_async_engine(db_url, connect_args=connect_args)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with async_session() as session:
                # Get all running campaigns
                # Use text() cast to avoid asyncpg enum type issues when enum doesn't exist
                # This works whether the column is VARCHAR or ENUM
                result = await session.execute(
                    select(Campaign)
                    .where(cast(Campaign.status, String) == 'running')
                    .options(selectinload(Campaign.ivr_flow))
                )
                campaigns = result.scalars().all()

                for campaign in campaigns:
                    await self._process_single_campaign(session, campaign)

        except Exception as e:
            logger.error(f"Error querying campaigns: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

    async def _process_single_campaign(self, session: AsyncSession, campaign: Campaign):
        """Process a single campaign - fetch contacts and queue calls."""
        if not self.call_manager:
            return

        # Register campaign with call manager (updates settings if already registered)
        self.call_manager.register_campaign(
            campaign_id=campaign.id,
            max_concurrent_calls=campaign.max_concurrent_calls,
            calls_per_minute=campaign.calls_per_minute
        )

        # Check if we have available slots for this campaign
        available_slots = self.call_manager.get_available_slots(campaign.id)
        if available_slots <= 0:
            return

        # Check calling hours
        if not self._is_within_calling_hours(campaign):
            return

        # Get pending contacts that are ready to be called
        contacts_to_dial = await self._get_pending_contacts(
            session, campaign, limit=available_slots
        )

        if not contacts_to_dial:
            # Check if campaign is complete
            await self._check_campaign_completion(session, campaign)
            return

        # Get IVR flow definition if available
        ivr_flow_definition = None
        if campaign.ivr_flow and campaign.ivr_flow.active_version_id:
            # Get the active version's definition
            version_result = await session.execute(
                select(IVRFlowVersion).where(
                    IVRFlowVersion.id == campaign.ivr_flow.active_version_id
                )
            )
            active_version = version_result.scalar_one_or_none()
            if active_version:
                ivr_flow_definition = active_version.definition

        # Queue contacts for dialing
        from sqlalchemy import update
        pending_contacts = []
        cc_ids_to_update = []

        for cc, contact in contacts_to_dial:
            cc_ids_to_update.append(cc.id)

            pending_contact = PendingContact(
                campaign_id=campaign.id,
                campaign_contact_id=cc.id,
                contact_id=contact.id,
                phone_number=contact.phone_number_e164 or contact.phone_number,
                caller_id="",  # Use default caller ID from SIP settings
                ivr_flow_definition=ivr_flow_definition,
                priority=cc.priority,
                attempts=cc.attempts + 1
            )
            pending_contacts.append(pending_contact)

        # Mark contacts as in-progress using raw update to avoid enum type issues
        if cc_ids_to_update:
            await session.execute(
                update(CampaignContact)
                .where(CampaignContact.id.in_(cc_ids_to_update))
                .values(
                    status='in_progress',
                    attempts=CampaignContact.attempts + 1,
                    last_attempt_at=datetime.utcnow()
                )
            )
            await session.commit()

        # Add to call manager queue
        if pending_contacts:
            await self.call_manager.add_contacts_to_queue(pending_contacts)
            logger.info(
                f"Campaign {campaign.name}: Queued {len(pending_contacts)} contacts, "
                f"available slots: {available_slots}"
            )

    def _is_within_calling_hours(self, campaign: Campaign) -> bool:
        """Check if current time is within campaign calling hours."""
        now = datetime.utcnow()
        current_time = now.time()

        start_time = campaign.calling_hours_start
        end_time = campaign.calling_hours_end

        # Handle overnight calling windows (e.g., 22:00 to 06:00)
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return current_time >= start_time or current_time <= end_time

    async def _get_pending_contacts(
        self,
        session: AsyncSession,
        campaign: Campaign,
        limit: int
    ) -> List[tuple]:
        """Get pending contacts ready to be dialed."""
        now = datetime.utcnow()

        # Query for contacts that are:
        # 1. PENDING status, OR
        # 2. FAILED/IN_PROGRESS with retry scheduled (next_attempt_at <= now)
        # AND haven't exceeded max retries
        # Use cast(String) to avoid asyncpg enum type issues
        status_col = cast(CampaignContact.status, String)
        query = (
            select(CampaignContact, Contact)
            .join(Contact, CampaignContact.contact_id == Contact.id)
            .where(
                and_(
                    CampaignContact.campaign_id == campaign.id,
                    or_(
                        status_col == 'pending',
                        and_(
                            status_col.in_(['failed', 'in_progress']),
                            CampaignContact.next_attempt_at <= now,
                            CampaignContact.attempts < campaign.max_retries + 1
                        )
                    )
                )
            )
            .order_by(CampaignContact.priority, CampaignContact.created_at)
            .limit(limit)
        )

        result = await session.execute(query)
        return result.all()

    async def _check_campaign_completion(self, session: AsyncSession, campaign: Campaign):
        """Check if a campaign has completed all contacts."""
        from sqlalchemy import func

        # Count remaining contacts to process
        # Use cast(String) to avoid asyncpg enum type issues
        status_col = cast(CampaignContact.status, String)
        remaining = await session.execute(
            select(func.count())
            .where(
                and_(
                    CampaignContact.campaign_id == campaign.id,
                    status_col.in_(['pending', 'in_progress'])
                )
            )
        )
        remaining_count = remaining.scalar() or 0

        if remaining_count == 0:
            # Mark campaign as completed using string value
            # We set the raw value since the column may be VARCHAR or ENUM
            from sqlalchemy import update
            await session.execute(
                update(Campaign)
                .where(Campaign.id == campaign.id)
                .values(status='completed', completed_at=datetime.utcnow())
            )
            await session.commit()

            # Unregister from call manager
            if self.call_manager:
                self.call_manager.unregister_campaign(campaign.id)

            logger.info(f"Campaign {campaign.name} completed - all contacts processed")

            # Publish completion event
            await self._publish_campaign_event(campaign.id, "completed")

    async def _make_campaign_call(
        self,
        destination: str,
        caller_id: str,
        ivr_flow_definition: Optional[Dict],
        campaign_id: str,
        contact_id: str,
        campaign_contact_id: str
    ) -> Optional["SIPCall"]:
        """Make a call for a campaign contact (called by call manager)."""
        call = await self.make_call(
            destination=destination,
            caller_id=caller_id,
            ivr_flow_definition=ivr_flow_definition,
            campaign_id=campaign_id,
            contact_id=contact_id
        )

        if call:
            # Track this call for result updates
            self._call_contacts[call.info.call_id] = {
                "campaign_id": campaign_id,
                "contact_id": contact_id,
                "campaign_contact_id": campaign_contact_id
            }

        return call

    async def _monitor_active_calls(self):
        """Monitor active calls and update their status."""
        logger.info("Starting active call monitor...")

        while self.running:
            try:
                # Check each active call
                completed_calls = []

                for call_id, call in list(self.active_calls.items()):
                    try:
                        state = call.state if hasattr(call, 'state') else call.info.state

                        if state in (CallState.DISCONNECTED, CallState.FAILED):
                            completed_calls.append((call_id, call, state))
                    except Exception as e:
                        logger.error(f"Error checking call {call_id}: {e}")

                # Process completed calls
                for call_id, call, state in completed_calls:
                    await self._handle_call_completed(call_id, call, state)

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error in call monitor: {e}")
                await asyncio.sleep(1)

    async def _handle_call_completed(self, call_id: str, call: "SIPCall", state):
        """Handle a completed call - update database and call manager."""
        # Remove from active calls
        self.active_calls.pop(call_id, None)

        # Get contact info
        contact_info = self._call_contacts.pop(call_id, None)

        # Notify call manager
        if self.call_manager:
            success = state != CallState.FAILED
            await self.call_manager.record_call_end(call_id, success)

        # Update database
        if contact_info:
            await self._update_call_result(
                campaign_contact_id=contact_info["campaign_contact_id"],
                call_id=call_id,
                state=state,
                call=call
            )

        logger.debug(f"Call {call_id} completed with state {state}")

    async def _update_call_result(
        self,
        campaign_contact_id: str,
        call_id: str,
        state,
        call: "SIPCall"
    ):
        """Update the campaign contact with call result."""
        from sqlalchemy import update

        db_url, connect_args = self._get_async_db_url_and_connect_args()
        engine = create_async_engine(db_url, connect_args=connect_args)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with async_session() as session:
                # Get campaign contact and campaign info
                result = await session.execute(
                    select(CampaignContact)
                    .options(selectinload(CampaignContact.campaign))
                    .where(CampaignContact.id == campaign_contact_id)
                )
                cc = result.scalar_one_or_none()

                if not cc:
                    return

                campaign = cc.campaign
                campaign_id = campaign.id

                # Determine disposition and new status based on call state
                # Use string values to avoid enum type issues
                if state == CallState.DISCONNECTED:
                    # Call was answered and completed
                    disposition = 'answered_human'
                    new_status = 'completed'

                    # Update campaign stats
                    await session.execute(
                        update(Campaign)
                        .where(Campaign.id == campaign_id)
                        .values(
                            contacts_answered=Campaign.contacts_answered + 1,
                            contacts_completed=Campaign.contacts_completed + 1,
                            contacts_called=Campaign.contacts_called + 1
                        )
                    )

                elif state == CallState.FAILED:
                    # Call failed - determine reason
                    disposition = 'no_answer'

                    # Check if we should retry
                    if cc.attempts < campaign.max_retries + 1:
                        # Schedule retry based on settings
                        should_retry = campaign.retry_on_no_answer or campaign.retry_on_failed
                        if should_retry:
                            new_status = 'pending'
                            next_attempt = datetime.utcnow() + timedelta(
                                minutes=campaign.retry_delay_minutes
                            )
                        else:
                            new_status = 'failed'
                            next_attempt = None
                    else:
                        new_status = 'failed'
                        next_attempt = None

                    # Update campaign stats
                    stats_update = {"contacts_called": Campaign.contacts_called + 1}
                    if new_status == 'failed':
                        stats_update["contacts_completed"] = Campaign.contacts_completed + 1

                    await session.execute(
                        update(Campaign)
                        .where(Campaign.id == campaign_id)
                        .values(**stats_update)
                    )

                    # Update campaign contact with next_attempt if retrying
                    if new_status == 'pending' and next_attempt:
                        await session.execute(
                            update(CampaignContact)
                            .where(CampaignContact.id == campaign_contact_id)
                            .values(next_attempt_at=next_attempt)
                        )

                else:
                    disposition = 'failed'
                    new_status = 'failed'

                    await session.execute(
                        update(Campaign)
                        .where(Campaign.id == campaign_id)
                        .values(contacts_called=Campaign.contacts_called + 1)
                    )

                # Update campaign contact status and disposition
                await session.execute(
                    update(CampaignContact)
                    .where(CampaignContact.id == campaign_contact_id)
                    .values(status=new_status, last_disposition=disposition)
                )

                await session.commit()

        except Exception as e:
            logger.error(f"Error updating call result: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

    async def _publish_campaign_event(self, campaign_id: str, event_type: str):
        """Publish campaign event to Redis for WebSocket clients."""
        import json

        try:
            r = self._get_redis_client()

            message = json.dumps({
                "type": f"campaign.{event_type}",
                "data": {
                    "campaign_id": campaign_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

            await r.publish("ws:campaigns", message)
            await r.aclose()

        except Exception as e:
            logger.error(f"Failed to publish campaign event: {e}")

    async def _publish_call_manager_status(self):
        """Publish call manager status to Redis for API access."""
        if not self.call_manager:
            return

        import json

        try:
            r = self._get_redis_client()

            status = self.call_manager.get_status()
            status["last_updated"] = datetime.utcnow().isoformat()

            await r.set(
                "dialer:call_manager_status",
                json.dumps(status),
                ex=30  # Expire after 30 seconds
            )
            await r.aclose()

        except Exception as e:
            logger.error(f"Failed to publish call manager status: {e}")

    async def _listen_for_test_calls(self):
        """Listen for test call requests via Redis with automatic reconnection."""
        import json

        while self.running:
            r = None
            pubsub = None
            try:
                logger.info(f"Connecting to Redis for test calls: {self.redis_url}")
                r = self._get_redis_client()
                pubsub = r.pubsub()
                await pubsub.subscribe("dialer:test_call")
                logger.info("Listening for test calls on Redis channel: dialer:test_call")

                async for message in pubsub.listen():
                    if not self.running:
                        break
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

            except asyncio.CancelledError:
                logger.info("Test call listener cancelled")
                break
            except Exception as e:
                logger.error(f"Redis listener error: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            finally:
                # Clean up connections - use aclose() for async Redis clients
                try:
                    if pubsub:
                        await pubsub.unsubscribe("dialer:test_call")
                        await pubsub.aclose()
                    if r:
                        await r.aclose()
                except Exception as cleanup_err:
                    logger.debug(f"Cleanup error (safe to ignore): {cleanup_err}")

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

        # Stop call manager
        if self.call_manager:
            await self.call_manager.stop_processing()
            self.call_manager = None

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
