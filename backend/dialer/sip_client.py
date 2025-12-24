"""
Direct SIP Client Implementation.

This module provides a full SIP User Agent (UA) implementation that:
- Registers with PBX as a SIP extension
- Originates calls using SIP INVITE
- Handles RTP media streams
- Supports codec negotiation (G.711, G.722, etc.)
- Implements answering machine detection (AMD)
"""
import asyncio
import hashlib
import logging
import random
import socket
import struct
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Callable, Any
from urllib.parse import urlparse

import numpy as np
from scipy import signal as scipy_signal

from dialer.rtp_handler import RTPSession, G711Codec, AudioBuffer

logger = logging.getLogger(__name__)


class SIPMethod(str, Enum):
    """SIP request methods."""
    REGISTER = "REGISTER"
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    OPTIONS = "OPTIONS"


class CallState(str, Enum):
    """Call state machine."""
    IDLE = "IDLE"
    CALLING = "CALLING"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    ENDED = "ENDED"
    FAILED = "FAILED"


class AMDResult(str, Enum):
    """AMD detection results."""
    UNKNOWN = "UNKNOWN"
    HUMAN = "HUMAN"
    MACHINE = "MACHINE"
    BEEP = "BEEP"
    SILENCE = "SILENCE"


@dataclass
class SIPCredentials:
    """SIP registration credentials."""
    username: str
    password: str
    realm: str = ""
    domain: str = ""


@dataclass
class SIPMessage:
    """Parsed SIP message."""
    method: Optional[str] = None  # For requests
    status_code: Optional[int] = None  # For responses
    status_text: Optional[str] = None
    headers: Dict[str, str] = None
    body: str = ""
    raw: str = ""

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class CallInfo:
    """Information about an active call."""
    call_id: str
    from_tag: str
    to_tag: Optional[str]
    state: CallState
    destination: str
    local_sdp: Optional[str] = None
    remote_sdp: Optional[str] = None
    rtp_session: Optional[RTPSession] = None
    rtp_port: Optional[int] = None
    remote_rtp_addr: Optional[tuple] = None
    start_time: Optional[float] = None
    answer_time: Optional[float] = None
    amd_result: AMDResult = AMDResult.UNKNOWN
    audio_buffer: Optional[AudioBuffer] = None


class SIPClient:
    """
    Async SIP User Agent Client.

    Implements RFC 3261 (SIP) with support for:
    - UDP transport
    - Digest authentication
    - RTP media (G.711μ-law)
    - Answering machine detection
    """

    def __init__(
        self,
        server: str,
        port: int = 5060,
        username: str = "",
        password: str = "",
        extension: str = "",
        local_ip: Optional[str] = None,
        channel_driver: str = "PJSIP"
    ):
        self.server = server
        self.port = port
        self.username = username or extension
        self.password = password
        self.extension = extension
        self.channel_driver = channel_driver

        # Auto-detect local IP if not provided
        if local_ip:
            self.local_ip = local_ip
        else:
            self.local_ip = self._get_local_ip()

        # SIP transport
        self.sip_socket: Optional[socket.socket] = None
        self.local_port: int = 0
        self.running = False

        # Registration
        self.registered = False
        self.register_expires = 300  # 5 minutes
        self.credentials = SIPCredentials(
            username=self.username,
            password=self.password
        )

        # Call tracking
        self.active_calls: Dict[str, CallInfo] = {}
        self.cseq = 1

        # Callbacks
        self.on_call_state_changed: Optional[Callable] = None
        self.on_amd_result: Optional[Callable] = None

        # RTP configuration
        self.rtp_port_range = (10000, 20000)
        self.codec_preference = ["PCMU", "PCMA", "G722"]  # G.711μ, G.711a, G.722

    def _get_local_ip(self) -> str:
        """Auto-detect local IP address."""
        try:
            # Connect to a public DNS to determine local interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def _generate_call_id(self) -> str:
        """Generate unique Call-ID."""
        return f"{uuid.uuid4().hex}@{self.local_ip}"

    def _generate_tag(self) -> str:
        """Generate random tag for From/To headers."""
        return str(random.randint(1000000, 9999999))

    def _generate_branch(self) -> str:
        """Generate branch parameter for Via header (RFC 3261)."""
        return f"z9hG4bK-{uuid.uuid4().hex[:16]}"

    async def start(self):
        """Start SIP client and bind UDP socket."""
        logger.info(f"Starting SIP client for extension {self.extension}")

        # Create UDP socket for SIP
        self.sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sip_socket.bind((self.local_ip, 0))  # Bind to random port
        self.sip_socket.setblocking(False)

        self.local_port = self.sip_socket.getsockname()[1]
        self.running = True

        logger.info(f"SIP client listening on {self.local_ip}:{self.local_port}")

        # Start receive loop
        asyncio.create_task(self._receive_loop())

    async def stop(self):
        """Stop SIP client."""
        logger.info("Stopping SIP client...")
        self.running = False

        # Unregister
        if self.registered:
            await self.unregister()

        # End all active calls
        for call_id in list(self.active_calls.keys()):
            await self.hangup(call_id)

        # Close sockets
        if self.sip_socket:
            self.sip_socket.close()

        logger.info("SIP client stopped")

    async def register(self) -> bool:
        """
        Register with SIP server.

        Returns:
            True if registration successful
        """
        logger.info(f"Registering extension {self.extension} with {self.server}:{self.port}")

        call_id = self._generate_call_id()
        from_tag = self._generate_tag()

        # Build REGISTER request
        request = self._build_register(call_id, from_tag)

        # Send initial REGISTER
        response = await self._send_request(request)

        if response and response.status_code == 401:
            # Unauthorized - need to authenticate
            logger.info("Received 401, sending authenticated REGISTER")

            # Extract authentication challenge
            www_auth = response.headers.get("WWW-Authenticate", "")
            realm, nonce = self._parse_www_authenticate(www_auth)

            # Update credentials
            self.credentials.realm = realm

            # Build authenticated REGISTER
            auth_request = self._build_register(call_id, from_tag, nonce=nonce)
            response = await self._send_request(auth_request)

        if response and response.status_code == 200:
            self.registered = True
            logger.info(f"✓ Successfully registered extension {self.extension}")

            # Schedule re-registration before expiry
            asyncio.create_task(self._auto_reregister())

            return True
        else:
            logger.error(f"Registration failed: {response.status_code if response else 'No response'}")
            return False

    async def unregister(self):
        """Unregister from SIP server."""
        if not self.registered:
            return

        logger.info(f"Unregistering extension {self.extension}")

        call_id = self._generate_call_id()
        from_tag = self._generate_tag()

        # REGISTER with Expires: 0 means unregister
        request = self._build_register(call_id, from_tag, expires=0)
        await self._send_request(request)

        self.registered = False
        logger.info("✓ Unregistered")

    async def _auto_reregister(self):
        """Auto re-register before expiration."""
        # Re-register at 80% of expiry time
        await asyncio.sleep(self.register_expires * 0.8)

        if self.running and self.registered:
            logger.info("Re-registering...")
            await self.register()

    def _build_register(
        self,
        call_id: str,
        from_tag: str,
        nonce: Optional[str] = None,
        expires: int = None
    ) -> str:
        """Build SIP REGISTER request."""
        if expires is None:
            expires = self.register_expires

        uri = f"sip:{self.server}"
        from_uri = f"sip:{self.username}@{self.server}"
        contact = f"<sip:{self.username}@{self.local_ip}:{self.local_port}>"

        request = f"REGISTER {uri} SIP/2.0\r\n"
        request += f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self._generate_branch()};rport\r\n"
        request += f"From: <{from_uri}>;tag={from_tag}\r\n"
        request += f"To: <{from_uri}>\r\n"
        request += f"Call-ID: {call_id}\r\n"
        request += f"CSeq: {self.cseq} REGISTER\r\n"
        request += f"Contact: {contact};expires={expires}\r\n"
        request += f"Max-Forwards: 70\r\n"
        request += f"User-Agent: SIP-AutoDialer/1.0\r\n"
        request += f"Expires: {expires}\r\n"

        # Add authentication if we have nonce
        if nonce and self.credentials.realm:
            auth_header = self._build_auth_header(
                method="REGISTER",
                uri=uri,
                nonce=nonce,
                realm=self.credentials.realm
            )
            request += f"Authorization: {auth_header}\r\n"

        request += f"Content-Length: 0\r\n"
        request += "\r\n"

        self.cseq += 1
        return request

    def _parse_www_authenticate(self, header: str) -> tuple[str, str]:
        """Parse WWW-Authenticate header to extract realm and nonce."""
        realm = ""
        nonce = ""

        if "Digest" in header:
            parts = header.split(",")
            for part in parts:
                if "realm=" in part:
                    realm = part.split("realm=")[1].strip().strip('"')
                elif "nonce=" in part:
                    nonce = part.split("nonce=")[1].strip().strip('"')

        return realm, nonce

    def _build_auth_header(self, method: str, uri: str, nonce: str, realm: str) -> str:
        """Build Digest Authentication header (RFC 2617)."""
        # Calculate HA1 = MD5(username:realm:password)
        ha1 = hashlib.md5(f"{self.username}:{realm}:{self.password}".encode()).hexdigest()

        # Calculate HA2 = MD5(method:uri)
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

        # Calculate response = MD5(HA1:nonce:HA2)
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

        auth = f'Digest username="{self.username}", '
        auth += f'realm="{realm}", '
        auth += f'nonce="{nonce}", '
        auth += f'uri="{uri}", '
        auth += f'response="{response}", '
        auth += 'algorithm=MD5'

        return auth

    async def _send_request(self, request: str, timeout: float = 5.0) -> Optional[SIPMessage]:
        """Send SIP request and wait for response."""
        if not self.sip_socket:
            raise RuntimeError("SIP socket not initialized")

        # Send request
        self.sip_socket.sendto(request.encode(), (self.server, self.port))
        logger.debug(f"→ Sent SIP request:\n{request[:200]}...")

        # Wait for response
        try:
            response_data = await asyncio.wait_for(
                self._wait_for_response(),
                timeout=timeout
            )
            return self._parse_sip_message(response_data)
        except asyncio.TimeoutError:
            logger.warning("SIP request timeout")
            return None

    async def _wait_for_response(self) -> bytes:
        """Wait for next SIP message."""
        while self.running:
            try:
                data, addr = self.sip_socket.recvfrom(4096)
                return data
            except BlockingIOError:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error receiving SIP message: {e}")
                await asyncio.sleep(0.1)

        return b""

    async def _receive_loop(self):
        """Main receive loop for incoming SIP messages."""
        logger.info("Started SIP receive loop")

        while self.running:
            try:
                data, addr = self.sip_socket.recvfrom(4096)
                message = self._parse_sip_message(data.decode())

                if message:
                    await self._handle_incoming_message(message, addr)

            except BlockingIOError:
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(0.1)

        logger.info("SIP receive loop ended")

    def _parse_sip_message(self, data: str) -> Optional[SIPMessage]:
        """Parse SIP message (request or response)."""
        if not data:
            return None

        lines = data.split("\r\n")
        if not lines:
            return None

        # Parse first line
        first_line = lines[0]
        message = SIPMessage(raw=data)

        if first_line.startswith("SIP/2.0"):
            # Response
            parts = first_line.split(" ", 2)
            if len(parts) >= 3:
                message.status_code = int(parts[1])
                message.status_text = parts[2]
        else:
            # Request
            parts = first_line.split(" ", 2)
            if len(parts) >= 1:
                message.method = parts[0]

        # Parse headers
        headers = {}
        body_start = 0

        for i, line in enumerate(lines[1:], 1):
            if line == "":
                body_start = i + 1
                break

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        message.headers = headers

        # Parse body
        if body_start < len(lines):
            message.body = "\r\n".join(lines[body_start:])

        return message

    async def _handle_incoming_message(self, message: SIPMessage, addr: tuple):
        """Handle incoming SIP message."""
        logger.debug(f"← Received SIP message from {addr}: {message.method or message.status_code}")

        # Handle responses to our requests
        if message.status_code:
            await self._handle_sip_response(message, addr)

        # Handle incoming requests (e.g., OPTIONS, incoming calls)
        elif message.method:
            if message.method == "OPTIONS":
                await self._handle_options(message, addr)
            # Add more handlers as needed

    async def _handle_sip_response(self, message: SIPMessage, addr: tuple):
        """Handle SIP responses (180, 200, etc.)."""
        call_id = message.headers.get('Call-ID')
        if not call_id:
            logger.warning("Received SIP response without Call-ID")
            return

        call_info = self.active_calls.get(call_id)
        if not call_info:
            logger.debug(f"Received response for unknown call {call_id}")
            return

        cseq = message.headers.get('CSeq', '')

        # Handle 100 Trying
        if message.status_code == 100:
            logger.info(f"Call {call_id}: Trying...")

        # Handle 180 Ringing
        elif message.status_code == 180:
            logger.info(f"Call {call_id}: Ringing")
            call_info.state = CallState.RINGING

            # Extract To tag if present
            to_header = message.headers.get('To', '')
            if 'tag=' in to_header:
                tag_start = to_header.index('tag=') + 4
                tag_end = to_header.find(';', tag_start)
                if tag_end == -1:
                    tag_end = to_header.find('>', tag_start)
                if tag_end == -1:
                    tag_end = len(to_header)
                call_info.to_tag = to_header[tag_start:tag_end].strip()
                logger.debug(f"Extracted To tag: {call_info.to_tag}")

        # Handle 200 OK
        elif message.status_code == 200:
            if 'INVITE' in cseq:
                logger.info(f"Call {call_id}: Answered (200 OK)")
                call_info.state = CallState.ANSWERED
                call_info.answer_time = time.time()

                # Extract To tag
                to_header = message.headers.get('To', '')
                if 'tag=' in to_header:
                    tag_start = to_header.index('tag=') + 4
                    tag_end = to_header.find(';', tag_start)
                    if tag_end == -1:
                        tag_end = to_header.find('>', tag_start)
                    if tag_end == -1:
                        tag_end = len(to_header)
                    call_info.to_tag = to_header[tag_start:tag_end].strip()

                # Parse SDP to get remote RTP endpoint
                if message.body:
                    sdp_info = self._parse_sdp(message.body)
                    call_info.remote_sdp = message.body

                    if sdp_info['ip'] and sdp_info['port']:
                        remote_ip = sdp_info['ip']
                        remote_port = sdp_info['port']
                        call_info.remote_rtp_addr = (remote_ip, remote_port)

                        # Set remote endpoint for RTP session
                        if call_info.rtp_session:
                            call_info.rtp_session.set_remote(remote_ip, remote_port)
                            logger.info(f"RTP session configured: {remote_ip}:{remote_port}")

                # Send ACK
                await self._send_ack(call_info)

            elif 'BYE' in cseq:
                logger.info(f"Call {call_id}: BYE acknowledged")
                call_info.state = CallState.ENDED

        # Handle error responses
        elif message.status_code >= 400:
            logger.warning(f"Call {call_id}: Failed with {message.status_code} {message.status_text}")
            call_info.state = CallState.FAILED

            # Clean up
            if call_info.rtp_session:
                await call_info.rtp_session.stop()

            # 486 Busy, 487 Request Terminated, 603 Decline
            if message.status_code in [486, 487, 603]:
                logger.info(f"Call declined/busy: {message.status_code}")

    async def _handle_options(self, message: SIPMessage, addr: tuple):
        """Respond to OPTIONS request."""
        # Send 200 OK
        response = "SIP/2.0 200 OK\r\n"
        # ... add headers
        response += "Content-Length: 0\r\n\r\n"

        self.sip_socket.sendto(response.encode(), addr)

    # =========================================================================
    # Call Origination
    # =========================================================================

    async def originate_call(self, destination: str, caller_id: Optional[str] = None) -> Optional[str]:
        """
        Originate outbound call.

        Args:
            destination: Phone number to call (with dial prefix if needed)
            caller_id: Caller ID to display (defaults to extension)

        Returns:
            Call ID if successful, None otherwise
        """
        if not self.registered:
            logger.error("Cannot originate call: not registered")
            return None

        caller_id = caller_id or self.extension

        call_id = self._generate_call_id()
        from_tag = self._generate_tag()

        # Create call info
        call_info = CallInfo(
            call_id=call_id,
            from_tag=from_tag,
            to_tag=None,
            state=CallState.CALLING,
            destination=destination,
            start_time=time.time()
        )

        # Allocate RTP session
        rtp_session = self._allocate_rtp_session()
        call_info.rtp_session = rtp_session
        call_info.rtp_port = rtp_session.local_port
        call_info.audio_buffer = AudioBuffer(size_ms=200, sample_rate=8000)

        # Set up audio callback
        rtp_session.on_audio_received = lambda audio: self._on_rtp_audio(call_id, audio)

        # Start RTP session
        await rtp_session.start()

        # Generate SDP
        sdp = self._build_sdp(call_info.rtp_port)
        call_info.local_sdp = sdp

        # Store call
        self.active_calls[call_id] = call_info

        # Build INVITE
        invite = self._build_invite(destination, call_id, from_tag, caller_id, sdp)

        # Send INVITE
        logger.info(f"Sending INVITE to {destination}")
        response = await self._send_request(invite, timeout=30.0)

        if response and response.status_code == 100:
            # Trying
            call_info.state = CallState.RINGING
            logger.info(f"Call to {destination} is ringing...")

        # Call state will be updated in receive loop as responses arrive

        return call_id

    def _allocate_rtp_session(self) -> RTPSession:
        """Allocate RTP session with available port."""
        for port in range(*self.rtp_port_range):
            try:
                # Try to create RTP session on this port
                rtp_session = RTPSession(
                    local_ip=self.local_ip,
                    local_port=port,
                    payload_type=0,  # PCMU (G.711 μ-law)
                    sample_rate=8000,
                    ptime=20
                )
                return rtp_session
            except OSError:
                continue

        raise RuntimeError("No available RTP ports")

    def _build_sdp(self, rtp_port: int) -> str:
        """Build SDP (Session Description Protocol) for media negotiation."""
        sdp = f"v=0\r\n"
        sdp += f"o={self.username} {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}\r\n"
        sdp += f"s=SIP Auto-Dialer\r\n"
        sdp += f"c=IN IP4 {self.local_ip}\r\n"
        sdp += f"t=0 0\r\n"
        sdp += f"m=audio {rtp_port} RTP/AVP 0 8 9\r\n"  # PCMU, PCMA, G722
        sdp += f"a=rtpmap:0 PCMU/8000\r\n"  # G.711 μ-law
        sdp += f"a=rtpmap:8 PCMA/8000\r\n"  # G.711 A-law
        sdp += f"a=rtpmap:9 G722/8000\r\n"  # G.722
        sdp += f"a=sendrecv\r\n"
        sdp += f"a=ptime:20\r\n"

        return sdp

    def _parse_sdp(self, sdp: str) -> dict:
        """
        Parse SDP from 200 OK response.

        Extracts:
        - Remote IP address (c=IN IP4 x.x.x.x)
        - Remote RTP port (m=audio port ...)
        - Supported codecs (m=audio ... RTP/AVP 0 8)

        Args:
            sdp: SDP body from SIP response

        Returns:
            dict with 'ip', 'port', 'codecs' keys
        """
        result = {
            'ip': None,
            'port': None,
            'codecs': []
        }

        if not sdp:
            return result

        lines = sdp.split('\r\n')

        for line in lines:
            line = line.strip()

            # c=IN IP4 192.168.1.100
            if line.startswith('c='):
                parts = line.split()
                if len(parts) >= 3:
                    result['ip'] = parts[2]

            # m=audio 10000 RTP/AVP 0 8 9
            elif line.startswith('m=audio'):
                parts = line.split()
                if len(parts) >= 2:
                    result['port'] = int(parts[1])
                # Extract codec payload types
                if len(parts) > 3:
                    result['codecs'] = [int(x) for x in parts[3:] if x.isdigit()]

        logger.debug(f"Parsed SDP: IP={result['ip']}, Port={result['port']}, Codecs={result['codecs']}")
        return result

    def _build_invite(
        self,
        destination: str,
        call_id: str,
        from_tag: str,
        caller_id: str,
        sdp: str
    ) -> str:
        """Build SIP INVITE request."""
        # For Grandstream, destination might need dial prefix (e.g., 9)
        uri = f"sip:{destination}@{self.server}"
        from_uri = f"sip:{caller_id}@{self.server}"
        contact = f"<sip:{self.username}@{self.local_ip}:{self.local_port}>"

        request = f"INVITE {uri} SIP/2.0\r\n"
        request += f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self._generate_branch()};rport\r\n"
        request += f"From: \"{caller_id}\" <{from_uri}>;tag={from_tag}\r\n"
        request += f"To: <{uri}>\r\n"
        request += f"Call-ID: {call_id}\r\n"
        request += f"CSeq: {self.cseq} INVITE\r\n"
        request += f"Contact: {contact}\r\n"
        request += f"Max-Forwards: 70\r\n"
        request += f"User-Agent: SIP-AutoDialer/1.0\r\n"
        request += f"Content-Type: application/sdp\r\n"
        request += f"Content-Length: {len(sdp)}\r\n"
        request += "\r\n"
        request += sdp

        self.cseq += 1
        return request

    async def _send_ack(self, call_info: CallInfo):
        """
        Send ACK message after receiving 200 OK.

        ACK completes the three-way handshake for INVITE.
        """
        if not call_info.to_tag:
            logger.warning(f"Cannot send ACK for {call_info.call_id}: missing To tag")
            return

        uri = f"sip:{call_info.destination}@{self.server}"
        from_uri = f"sip:{self.username}@{self.server}"
        contact = f"<sip:{self.username}@{self.local_ip}:{self.local_port}>"

        ack = f"ACK {uri} SIP/2.0\r\n"
        ack += f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self._generate_branch()};rport\r\n"
        ack += f"From: <{from_uri}>;tag={call_info.from_tag}\r\n"
        ack += f"To: <{uri}>;tag={call_info.to_tag}\r\n"
        ack += f"Call-ID: {call_info.call_id}\r\n"
        ack += f"CSeq: {self.cseq} ACK\r\n"
        ack += f"Contact: {contact}\r\n"
        ack += f"Max-Forwards: 70\r\n"
        ack += f"User-Agent: SIP-AutoDialer/1.0\r\n"
        ack += f"Content-Length: 0\r\n"
        ack += "\r\n"

        # Send ACK
        self.sip_socket.sendto(ack.encode(), (self.server, self.port))
        logger.info(f"→ Sent ACK for call {call_info.call_id}")

        # Note: ACK does not increment CSeq (uses same as INVITE)

    def _build_bye(self, call_info: CallInfo) -> str:
        """
        Build SIP BYE message for call termination.

        Args:
            call_info: Active call information

        Returns:
            BYE request string
        """
        if not call_info.to_tag:
            logger.warning(f"Cannot build BYE for {call_info.call_id}: missing To tag")
            return ""

        uri = f"sip:{call_info.destination}@{self.server}"
        from_uri = f"sip:{self.username}@{self.server}"
        contact = f"<sip:{self.username}@{self.local_ip}:{self.local_port}>"

        bye = f"BYE {uri} SIP/2.0\r\n"
        bye += f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self._generate_branch()};rport\r\n"
        bye += f"From: <{from_uri}>;tag={call_info.from_tag}\r\n"
        bye += f"To: <{uri}>;tag={call_info.to_tag}\r\n"
        bye += f"Call-ID: {call_info.call_id}\r\n"
        bye += f"CSeq: {self.cseq} BYE\r\n"
        bye += f"Contact: {contact}\r\n"
        bye += f"Max-Forwards: 70\r\n"
        bye += f"User-Agent: SIP-AutoDialer/1.0\r\n"
        bye += f"Content-Length: 0\r\n"
        bye += "\r\n"

        self.cseq += 1
        return bye

    def _on_rtp_audio(self, call_id: str, audio_payload: bytes):
        """Callback when RTP audio is received."""
        call_info = self.active_calls.get(call_id)
        if not call_info or not call_info.audio_buffer:
            return

        # Decode μ-law to PCM
        pcm_data = G711Codec.decode(audio_payload)

        # Store in buffer for AMD analysis
        call_info.audio_buffer.write(pcm_data)

    async def hangup(self, call_id: str):
        """
        Hangup active call by sending BYE.

        Args:
            call_id: Call ID to terminate
        """
        call_info = self.active_calls.get(call_id)
        if not call_info:
            logger.warning(f"Cannot hangup: call {call_id} not found")
            return

        logger.info(f"Hanging up call {call_id}")

        # Send BYE if call was established
        if call_info.state in [CallState.ANSWERED, CallState.RINGING]:
            bye_message = self._build_bye(call_info)
            if bye_message:
                try:
                    self.sip_socket.sendto(bye_message.encode(), (self.server, self.port))
                    logger.info(f"→ Sent BYE for call {call_id}")

                    # Wait briefly for 200 OK response
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error sending BYE: {e}")

        # Clean up RTP session
        if call_info.rtp_session:
            await call_info.rtp_session.stop()

        call_info.state = CallState.ENDED
        del self.active_calls[call_id]
        logger.info(f"Call {call_id} ended")

    # =========================================================================
    # Media & AMD
    # =========================================================================

    async def detect_amd(self, call_id: str, timeout: float = 5.0) -> AMDResult:
        """
        Detect if call was answered by human or machine.

        Uses audio analysis to detect:
        - Human: Short greeting, voice patterns
        - Machine: Long continuous audio, beep detection
        - Silence: No audio detected

        Args:
            call_id: Active call ID
            timeout: Maximum time to analyze (seconds)

        Returns:
            AMD result
        """
        call_info = self.active_calls.get(call_id)
        if not call_info or call_info.state != CallState.ANSWERED:
            return AMDResult.UNKNOWN

        logger.info(f"Starting AMD for call {call_id}")

        # Wait and collect audio in buffer (RTP callback fills it)
        start_time = time.time()
        await asyncio.sleep(timeout)

        if not call_info.audio_buffer or call_info.audio_buffer.available == 0:
            return AMDResult.SILENCE

        # Read collected audio from buffer
        audio_samples = []
        while True:
            chunk = call_info.audio_buffer.read(160)  # 20ms @ 8kHz
            if not chunk:
                break
            audio_samples.append(chunk)

        if not audio_samples:
            return AMDResult.SILENCE

        # Analyze collected audio
        result = self._analyze_audio_for_amd(audio_samples, time.time() - start_time)

        call_info.amd_result = result
        logger.info(f"AMD result for call {call_id}: {result}")

        # Trigger callback
        if self.on_amd_result:
            self.on_amd_result(call_id, result)

        return result

    def _analyze_audio_for_amd(self, audio_samples: list, duration: float) -> AMDResult:
        """
        Analyze audio to detect human vs machine.

        Heuristics:
        - Duration: Machines speak longer (>4s continuously)
        - Beep detection: FFT to find 800-2000 Hz tones
        - Energy patterns: Humans have pauses, machines don't
        - Initial silence: Humans answer faster
        """
        # Combine audio samples (PCM 16-bit)
        combined_audio = b"".join(audio_samples)

        if len(combined_audio) == 0:
            return AMDResult.SILENCE

        # Convert to numpy array
        audio_array = np.frombuffer(combined_audio, dtype=np.int16)

        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_array.astype(float) ** 2))

        # Energy threshold for silence
        if energy < 500:
            return AMDResult.SILENCE

        # Analyze speaking duration
        # Count frames with voice activity (energy > threshold)
        frame_size = 160  # 20ms @ 8kHz
        voice_frames = 0
        silence_frames = 0

        for i in range(0, len(audio_array), frame_size):
            frame = audio_array[i:i+frame_size]
            if len(frame) < frame_size:
                break

            frame_energy = np.sqrt(np.mean(frame.astype(float) ** 2))

            if frame_energy > 1000:
                voice_frames += 1
            else:
                silence_frames += 1

        # Calculate speaking ratio
        total_frames = voice_frames + silence_frames
        if total_frames == 0:
            return AMDResult.SILENCE

        speaking_ratio = voice_frames / total_frames

        # Beep detection using FFT
        # Look for sustained tone in 800-2400 Hz range
        beep_detected = False
        if len(audio_array) > 1024:
            # Perform FFT on first second
            sample_for_fft = audio_array[:8000]
            fft_result = np.fft.rfft(sample_for_fft)
            frequencies = np.fft.rfftfreq(len(sample_for_fft), 1.0/8000)

            # Find peak in beep range
            beep_range = (frequencies > 800) & (frequencies < 2400)
            if np.any(beep_range):
                beep_energy = np.abs(fft_result[beep_range]).max()
                total_energy = np.abs(fft_result).mean()

                if beep_energy > total_energy * 10:  # Peak is 10x average
                    beep_detected = True

        # Decision logic
        if beep_detected:
            return AMDResult.BEEP

        # Long continuous speech (high speaking ratio, long duration)
        if speaking_ratio > 0.8 and duration > 4.0:
            return AMDResult.MACHINE

        # Short greeting with pauses
        if speaking_ratio < 0.7 and duration < 3.0:
            return AMDResult.HUMAN

        # Default to human if uncertain
        return AMDResult.HUMAN

    async def play_audio(self, call_id: str, audio_file: str):
        """
        Play audio file to active call.

        Args:
            call_id: Active call ID
            audio_file: Path to audio file (WAV, MP3, etc.)
        """
        call_info = self.active_calls.get(call_id)
        if not call_info or call_info.state != CallState.ANSWERED:
            logger.error(f"Cannot play audio: call {call_id} not answered")
            return

        if not call_info.rtp_session:
            logger.error(f"Cannot play audio: no RTP session for call {call_id}")
            return

        logger.info(f"Playing audio file: {audio_file}")

        try:
            # Load audio file using pydub
            from pydub import AudioSegment

            # Load and convert to proper format
            audio = AudioSegment.from_file(audio_file)

            # Convert to 8kHz mono 16-bit PCM
            audio = audio.set_frame_rate(8000)
            audio = audio.set_channels(1)
            audio = audio.set_sample_width(2)  # 16-bit

            # Get raw PCM data
            pcm_data = audio.raw_data

            # Convert PCM to G.711 μ-law
            ulaw_data = G711Codec.encode(pcm_data)

            # Split into 20ms chunks (160 bytes for μ-law @ 8kHz)
            chunk_size = 160  # 20ms @ 8kHz in μ-law
            num_chunks = len(ulaw_data) // chunk_size

            logger.info(f"Playing {num_chunks} audio chunks ({len(ulaw_data)} bytes)")

            # Send each chunk as RTP packet
            for i in range(num_chunks):
                chunk = ulaw_data[i*chunk_size:(i+1)*chunk_size]

                # Mark first packet
                marker = (i == 0)

                # Send RTP
                await call_info.rtp_session.send_audio(chunk, marker=marker)

                # Wait 20ms between packets
                await asyncio.sleep(0.020)

            logger.info(f"Finished playing audio file: {audio_file}")

        except ImportError:
            logger.error("pydub not installed. Cannot play audio files.")
            logger.error("Install with: pip install pydub")
        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_call_state(self, call_id: str) -> Optional[CallState]:
        """Get current state of call."""
        call_info = self.active_calls.get(call_id)
        return call_info.state if call_info else None

    def get_active_calls(self) -> list[str]:
        """Get list of active call IDs."""
        return list(self.active_calls.keys())
