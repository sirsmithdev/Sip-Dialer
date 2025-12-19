"""
Dialer Engine Main Entry Point.

This module starts the dialer engine that manages outbound calls
by connecting directly as a PJSIP extension to the UCM6302/PBX.

The dialer acts like a SIP softphone - it registers with the PBX,
then originates calls using SIP INVITE.
"""
import asyncio
import logging
import os
import signal
import socket
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Callable, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.sip_settings import SIPSettings

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CallState(Enum):
    """SIP call states."""
    IDLE = "idle"
    INVITING = "inviting"
    RINGING = "ringing"
    CONNECTED = "connected"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


class RegistrationState(Enum):
    """SIP registration states."""
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    FAILED = "failed"


@dataclass
class SIPCall:
    """Represents an active SIP call."""
    call_id: str
    destination: str
    caller_id: str
    state: CallState = CallState.IDLE
    local_tag: str = field(default_factory=lambda: f"local-{uuid.uuid4().hex[:8]}")
    remote_tag: Optional[str] = None
    cseq: int = 1
    branch: str = field(default_factory=lambda: f"z9hG4bK-{uuid.uuid4().hex[:16]}")
    created_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None
    ended_at: Optional[float] = None


class SIPClient:
    """
    Simple SIP UAC (User Agent Client) for making outbound calls.

    This client registers with the SIP server as a PJSIP extension
    and originates calls using SIP INVITE requests.
    """

    def __init__(
        self,
        sip_server: str,
        sip_port: int,
        username: str,
        password: str,
        local_port: int = 5061,
        transport: str = "UDP"
    ):
        self.sip_server = sip_server
        self.sip_port = sip_port
        self.username = username
        self.password = password
        self.local_port = local_port
        self.transport = transport.upper()

        self.local_ip: Optional[str] = None
        self.socket: Optional[socket.socket] = None
        self.registration_state = RegistrationState.UNREGISTERED
        self.register_expires = 3600
        self.register_cseq = 1
        self.calls: Dict[str, SIPCall] = {}

        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._response_handlers: Dict[str, Callable] = {}

    def _get_local_ip(self) -> str:
        """Get local IP address that can reach the SIP server."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.sip_server, self.sip_port))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "0.0.0.0"

    async def start(self):
        """Start the SIP client."""
        logger.info(f"Starting SIP client for {self.username}@{self.sip_server}:{self.sip_port}")

        self.local_ip = self._get_local_ip()
        logger.info(f"Local IP: {self.local_ip}, Local port: {self.local_port}")

        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("0.0.0.0", self.local_port))
        self.socket.setblocking(False)

        self._running = True

        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())

        # Register with SIP server
        await self.register()

        # Start keepalive
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    async def stop(self):
        """Stop the SIP client."""
        logger.info("Stopping SIP client...")
        self._running = False

        # Cancel tasks
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Unregister
        await self.unregister()

        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None

        logger.info("SIP client stopped")

    def _build_via(self, branch: str) -> str:
        """Build Via header."""
        return f"SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={branch};rport"

    def _build_from(self, tag: str, display_name: Optional[str] = None) -> str:
        """Build From header."""
        if display_name:
            return f'"{display_name}" <sip:{self.username}@{self.sip_server}>;tag={tag}'
        return f"<sip:{self.username}@{self.sip_server}>;tag={tag}"

    def _build_to(self, uri: str, tag: Optional[str] = None) -> str:
        """Build To header."""
        if tag:
            return f"<{uri}>;tag={tag}"
        return f"<{uri}>"

    def _build_contact(self) -> str:
        """Build Contact header."""
        return f"<sip:{self.username}@{self.local_ip}:{self.local_port}>"

    async def _send_request(self, request: str):
        """Send SIP request via UDP."""
        if not self.socket:
            raise RuntimeError("Socket not initialized")

        try:
            await asyncio.get_event_loop().sock_sendto(
                self.socket,
                request.encode('utf-8'),
                (self.sip_server, self.sip_port)
            )
            logger.debug(f"Sent SIP request:\n{request[:200]}...")
        except Exception as e:
            logger.error(f"Failed to send SIP request: {e}")
            raise

    async def _receive_loop(self):
        """Receive and process SIP messages."""
        loop = asyncio.get_event_loop()

        while self._running:
            try:
                data, addr = await asyncio.wait_for(
                    loop.sock_recvfrom(self.socket, 4096),
                    timeout=1.0
                )
                message = data.decode('utf-8', errors='ignore')
                await self._handle_message(message, addr)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error receiving SIP message: {e}")
                    await asyncio.sleep(0.1)

    async def _handle_message(self, message: str, addr: tuple):
        """Handle incoming SIP message."""
        lines = message.split('\r\n')
        if not lines:
            return

        first_line = lines[0]
        logger.debug(f"Received from {addr}: {first_line}")

        # Parse headers
        headers = {}
        for line in lines[1:]:
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()

        # Check if it's a response
        if first_line.startswith('SIP/2.0'):
            parts = first_line.split(' ', 2)
            status_code = int(parts[1]) if len(parts) > 1 else 0
            await self._handle_response(status_code, headers, message)
        else:
            # It's a request
            await self._handle_request(first_line, headers, message)

    async def _handle_response(self, status_code: int, headers: dict, message: str):
        """Handle SIP response."""
        cseq = headers.get('cseq', '')
        call_id = headers.get('call-id', '')

        logger.info(f"SIP Response: {status_code} for {cseq}")

        # Handle registration responses
        if 'REGISTER' in cseq:
            await self._handle_register_response(status_code, headers)
            return

        # Handle INVITE responses
        if 'INVITE' in cseq:
            await self._handle_invite_response(status_code, headers, call_id)
            return

    async def _handle_register_response(self, status_code: int, headers: dict):
        """Handle REGISTER response."""
        if status_code == 200:
            self.registration_state = RegistrationState.REGISTERED
            logger.info("Successfully registered with SIP server")
        elif status_code == 401:
            # Need authentication - handle WWW-Authenticate
            logger.info("Registration requires authentication (401)")
            self.registration_state = RegistrationState.REGISTERING
            # TODO: Implement digest authentication
            # For now, mark as failed
            self.registration_state = RegistrationState.FAILED
            logger.warning("Digest authentication not yet implemented")
        elif status_code == 403:
            self.registration_state = RegistrationState.FAILED
            logger.error("Registration forbidden (403)")
        else:
            self.registration_state = RegistrationState.FAILED
            logger.error(f"Registration failed with status {status_code}")

    async def _handle_invite_response(self, status_code: int, headers: dict, call_id: str):
        """Handle INVITE response."""
        call = self.calls.get(call_id)
        if not call:
            logger.warning(f"Received response for unknown call: {call_id}")
            return

        if status_code == 100:
            logger.info(f"Call {call_id}: Trying...")
        elif status_code == 180 or status_code == 183:
            call.state = CallState.RINGING
            logger.info(f"Call {call_id}: Ringing")
        elif status_code == 200:
            call.state = CallState.CONNECTED
            call.answered_at = time.time()
            # Extract remote tag from To header
            to_header = headers.get('to', '')
            if 'tag=' in to_header:
                call.remote_tag = to_header.split('tag=')[1].split(';')[0]
            logger.info(f"Call {call_id}: Answered!")
            # TODO: Send ACK
        elif status_code >= 400:
            call.state = CallState.FAILED
            call.ended_at = time.time()
            logger.error(f"Call {call_id}: Failed with status {status_code}")

    async def _handle_request(self, request_line: str, headers: dict, message: str):
        """Handle incoming SIP request."""
        method = request_line.split(' ')[0]

        if method == 'BYE':
            await self._handle_bye(headers)
        elif method == 'OPTIONS':
            await self._send_options_response(headers)

    async def _handle_bye(self, headers: dict):
        """Handle incoming BYE request."""
        call_id = headers.get('call-id', '')
        call = self.calls.get(call_id)

        if call:
            call.state = CallState.TERMINATED
            call.ended_at = time.time()
            logger.info(f"Call {call_id}: Terminated by remote")
            # TODO: Send 200 OK response

    async def _send_options_response(self, headers: dict):
        """Send 200 OK response to OPTIONS."""
        # Basic keepalive response
        pass

    async def register(self):
        """Send REGISTER request to SIP server."""
        logger.info(f"Registering {self.username}@{self.sip_server}...")
        self.registration_state = RegistrationState.REGISTERING

        call_id = f"register-{uuid.uuid4().hex[:8]}"
        branch = f"z9hG4bK-{uuid.uuid4().hex[:16]}"
        tag = f"reg-{uuid.uuid4().hex[:8]}"

        request = (
            f"REGISTER sip:{self.sip_server}:{self.sip_port} SIP/2.0\r\n"
            f"Via: {self._build_via(branch)}\r\n"
            f"From: {self._build_from(tag)}\r\n"
            f"To: <sip:{self.username}@{self.sip_server}>\r\n"
            f"Call-ID: {call_id}@{self.local_ip}\r\n"
            f"CSeq: {self.register_cseq} REGISTER\r\n"
            f"Contact: {self._build_contact()};expires={self.register_expires}\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: SIP-AutoDialer/1.0\r\n"
            f"Expires: {self.register_expires}\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )

        self.register_cseq += 1
        await self._send_request(request)

    async def unregister(self):
        """Unregister from SIP server."""
        if self.registration_state != RegistrationState.REGISTERED:
            return

        logger.info("Unregistering from SIP server...")

        call_id = f"unregister-{uuid.uuid4().hex[:8]}"
        branch = f"z9hG4bK-{uuid.uuid4().hex[:16]}"
        tag = f"unreg-{uuid.uuid4().hex[:8]}"

        request = (
            f"REGISTER sip:{self.sip_server}:{self.sip_port} SIP/2.0\r\n"
            f"Via: {self._build_via(branch)}\r\n"
            f"From: {self._build_from(tag)}\r\n"
            f"To: <sip:{self.username}@{self.sip_server}>\r\n"
            f"Call-ID: {call_id}@{self.local_ip}\r\n"
            f"CSeq: {self.register_cseq} REGISTER\r\n"
            f"Contact: {self._build_contact()};expires=0\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: SIP-AutoDialer/1.0\r\n"
            f"Expires: 0\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )

        self.register_cseq += 1
        await self._send_request(request)
        self.registration_state = RegistrationState.UNREGISTERED

    async def _keepalive_loop(self):
        """Send periodic keepalive/re-registration."""
        while self._running:
            try:
                # Re-register before expiry (at 80% of expiry time)
                await asyncio.sleep(self.register_expires * 0.8)

                if self._running and self.registration_state == RegistrationState.REGISTERED:
                    logger.debug("Sending keepalive re-registration")
                    await self.register()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keepalive error: {e}")

    async def make_call(
        self,
        destination: str,
        caller_id: str = "AutoDialer"
    ) -> SIPCall:
        """
        Initiate an outbound call via SIP INVITE.

        Args:
            destination: Phone number or SIP URI to call
            caller_id: Caller ID name to display

        Returns:
            SIPCall object representing the call
        """
        if self.registration_state != RegistrationState.REGISTERED:
            raise RuntimeError("Not registered with SIP server")

        call_id = f"call-{uuid.uuid4().hex[:12]}"
        call = SIPCall(
            call_id=call_id,
            destination=destination,
            caller_id=caller_id,
            state=CallState.INVITING
        )
        self.calls[call_id] = call

        logger.info(f"Initiating call to {destination} (Call-ID: {call_id})")

        # Build SIP URI for destination
        if '@' in destination:
            dest_uri = f"sip:{destination}"
        else:
            dest_uri = f"sip:{destination}@{self.sip_server}"

        # Build INVITE request
        request = (
            f"INVITE {dest_uri} SIP/2.0\r\n"
            f"Via: {self._build_via(call.branch)}\r\n"
            f"From: {self._build_from(call.local_tag, caller_id)}\r\n"
            f"To: {self._build_to(dest_uri)}\r\n"
            f"Call-ID: {call_id}@{self.local_ip}\r\n"
            f"CSeq: {call.cseq} INVITE\r\n"
            f"Contact: {self._build_contact()}\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: SIP-AutoDialer/1.0\r\n"
            f"Allow: INVITE, ACK, CANCEL, BYE, OPTIONS\r\n"
            f"Content-Type: application/sdp\r\n"
        )

        # Build minimal SDP body
        sdp = self._build_sdp()
        request += f"Content-Length: {len(sdp)}\r\n\r\n{sdp}"

        await self._send_request(request)
        return call

    def _build_sdp(self) -> str:
        """Build SDP body for INVITE."""
        session_id = str(int(time.time()))
        # Use a port in the RTP range
        rtp_port = 10000

        sdp = (
            f"v=0\r\n"
            f"o=autodialer {session_id} {session_id} IN IP4 {self.local_ip}\r\n"
            f"s=SIP Call\r\n"
            f"c=IN IP4 {self.local_ip}\r\n"
            f"t=0 0\r\n"
            f"m=audio {rtp_port} RTP/AVP 0 8 101\r\n"
            f"a=rtpmap:0 PCMU/8000\r\n"
            f"a=rtpmap:8 PCMA/8000\r\n"
            f"a=rtpmap:101 telephone-event/8000\r\n"
            f"a=fmtp:101 0-16\r\n"
            f"a=ptime:20\r\n"
            f"a=sendrecv\r\n"
        )
        return sdp

    async def hangup_call(self, call_id: str):
        """Hang up an active call using BYE."""
        call = self.calls.get(call_id)
        if not call:
            logger.warning(f"Cannot hangup unknown call: {call_id}")
            return

        if call.state not in (CallState.RINGING, CallState.CONNECTED):
            logger.warning(f"Call {call_id} not in active state: {call.state}")
            return

        call.state = CallState.TERMINATING
        call.cseq += 1
        branch = f"z9hG4bK-{uuid.uuid4().hex[:16]}"

        if '@' in call.destination:
            dest_uri = f"sip:{call.destination}"
        else:
            dest_uri = f"sip:{call.destination}@{self.sip_server}"

        to_tag = f";tag={call.remote_tag}" if call.remote_tag else ""

        request = (
            f"BYE {dest_uri} SIP/2.0\r\n"
            f"Via: {self._build_via(branch)}\r\n"
            f"From: {self._build_from(call.local_tag, call.caller_id)}\r\n"
            f"To: <{dest_uri}>{to_tag}\r\n"
            f"Call-ID: {call_id}@{self.local_ip}\r\n"
            f"CSeq: {call.cseq} BYE\r\n"
            f"Max-Forwards: 70\r\n"
            f"User-Agent: SIP-AutoDialer/1.0\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )

        await self._send_request(request)
        call.state = CallState.TERMINATED
        call.ended_at = time.time()
        logger.info(f"Sent BYE for call {call_id}")


class DialerEngine:
    """Main dialer engine class using direct SIP calling."""

    def __init__(self):
        self.running = False
        self.sip_client: Optional[SIPClient] = None
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://autodialer:autodialer_secret@localhost:5432/autodialer"
        )
        self.local_sip_port = int(os.getenv("LOCAL_SIP_PORT", "5061"))

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
                from app.core.security import decrypt_value
                settings._decrypted_password = decrypt_value(settings.sip_password_encrypted)

            return settings

    async def start(self):
        """Start the dialer engine."""
        self.running = True
        logger.info("Starting Dialer Engine (Direct SIP Mode)...")

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

        # Initialize SIP client
        self.sip_client = SIPClient(
            sip_server=settings.sip_server,
            sip_port=settings.sip_port,
            username=settings.sip_username,
            password=settings._decrypted_password,
            local_port=self.local_sip_port,
            transport=settings.sip_transport.value if hasattr(settings.sip_transport, 'value') else str(settings.sip_transport)
        )

        try:
            await self.sip_client.start()

            # Wait for registration
            await asyncio.sleep(2)

            if self.sip_client.registration_state == RegistrationState.REGISTERED:
                logger.info("Dialer engine ready - registered with SIP server")
            else:
                logger.warning(f"Registration state: {self.sip_client.registration_state}")

            # Process campaigns
            await self.process_campaigns()

        except Exception as e:
            logger.error(f"Dialer engine error: {e}")
            raise

    async def process_campaigns(self):
        """Process active campaigns and initiate calls."""
        while self.running:
            try:
                # TODO: Check for active campaigns from database
                # TODO: Get contacts to dial
                # TODO: Initiate calls via SIP client
                # Example:
                # call = await self.sip_client.make_call("1234567890", "AutoDialer")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error processing campaigns: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the dialer engine."""
        logger.info("Stopping Dialer Engine...")
        self.running = False

        if self.sip_client:
            await self.sip_client.stop()
            self.sip_client = None


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
