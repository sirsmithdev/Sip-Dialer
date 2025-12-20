"""
PJSUA2 SIP Client for Grandstream UCM PJSIP Integration.

This module provides a complete SIP User Agent implementation that registers
with Grandstream UCM6302 as a PJSIP extension and handles outbound calling
with full RTP media support.

The implementation uses PJSUA2 (Python bindings for PJSIP) which provides:
- Complete SIP stack with digest authentication
- RTP media handling for audio playback
- DTMF detection (RFC 2833 and in-band)
- Full codec support (G.711, G.722, etc.)
"""

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Callable, Any, List
from queue import Queue

logger = logging.getLogger(__name__)

# Try to import pjsua2, provide fallback if not available
try:
    import pjsua2 as pj
    PJSUA2_AVAILABLE = True
except ImportError:
    PJSUA2_AVAILABLE = False
    logger.warning(
        "PJSUA2 not available. Install PJSIP with Python bindings to enable full SIP support. "
        "On Windows, you may need to build from source: https://github.com/pjsip/pjproject"
    )
    pj = None


class CallState(Enum):
    """SIP call states."""
    IDLE = "idle"
    CALLING = "calling"
    RINGING = "ringing"
    CONFIRMED = "confirmed"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class RegistrationState(Enum):
    """SIP registration states."""
    UNREGISTERED = "unregistered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    UNREGISTERING = "unregistering"
    FAILED = "failed"


@dataclass
class SIPCallInfo:
    """Information about an active SIP call."""
    call_id: str
    destination: str
    caller_id: str
    state: CallState = CallState.IDLE
    created_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None
    ended_at: Optional[float] = None
    hangup_reason: str = ""
    dtmf_buffer: List[str] = field(default_factory=list)


class SIPAccount:
    """
    PJSUA2 Account for UCM registration.

    Handles SIP REGISTER requests and maintains registration state
    with the Grandstream UCM.
    """

    def __init__(self, engine: 'SIPEngine'):
        self.engine = engine
        self.state = RegistrationState.UNREGISTERED
        self.last_error = ""
        self._pj_account: Optional[Any] = None

    def create(self, server: str, port: int, username: str, password: str, transport: str = "UDP"):
        """Create and configure the PJSUA2 account."""
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        # Create account config
        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{username}@{server}"
        acc_cfg.regConfig.registrarUri = f"sip:{server}:{port}"
        acc_cfg.regConfig.timeoutSec = 3600

        # Add authentication credentials
        cred = pj.AuthCredInfo("digest", "*", username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)

        # Create the account with callback handler
        self._pj_account = _PJAccount(self)
        self._pj_account.create(acc_cfg)

        self.state = RegistrationState.REGISTERING
        logger.info(f"Created SIP account: {username}@{server}:{port}")

    def on_reg_state(self, info):
        """Callback when registration state changes."""
        # PJSUA2 AccountInfo uses regStatus and regStatusText
        code = info.regStatus
        reason = info.regStatusText

        if code == 200:
            self.state = RegistrationState.REGISTERED
            logger.info(f"SIP registration successful: {reason}")
        elif code == 401 or code == 407:
            # Authentication challenge - PJSUA2 handles this automatically
            self.state = RegistrationState.REGISTERING
            logger.debug(f"SIP authentication challenge received")
        elif code >= 400:
            self.state = RegistrationState.FAILED
            self.last_error = f"{code} {reason}"
            logger.error(f"SIP registration failed: {code} {reason}")
        else:
            logger.info(f"SIP registration state: {code} {reason}")

    def unregister(self):
        """Unregister from the SIP server."""
        if self._pj_account and self.state == RegistrationState.REGISTERED:
            self.state = RegistrationState.UNREGISTERING
            self._pj_account.setRegistration(False)

    def shutdown(self):
        """Shutdown the account."""
        if self._pj_account:
            self._pj_account.shutdown()
            self._pj_account = None


class SIPCall:
    """
    PJSUA2 Call with media handling.

    Manages an individual SIP call including:
    - Call setup and teardown
    - Media negotiation and RTP handling
    - DTMF reception
    """

    def __init__(self, account: SIPAccount, call_id: str):
        self.account = account
        self.info = SIPCallInfo(
            call_id=call_id,
            destination="",
            caller_id=""
        )
        self._pj_call: Optional[Any] = None
        self._media_handler: Optional[Any] = None
        self._dtmf_callback: Optional[Callable[[str], None]] = None

    @property
    def call_id(self) -> str:
        """Get the call ID."""
        return self.info.call_id

    @property
    def state(self) -> CallState:
        """Get the current call state."""
        return self.info.state

    def make_call(self, destination: str, caller_id: str = ""):
        """Initiate an outbound call."""
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        self.info.destination = destination
        self.info.caller_id = caller_id
        self.info.state = CallState.CALLING

        # Build destination URI
        server = self.account.engine.sip_server
        dest_uri = f"sip:{destination}@{server}"

        # Create call with callback handler
        self._pj_call = _PJCall(self, self.account._pj_account)

        # Set up call options
        call_prm = pj.CallOpParam()
        call_prm.opt.audioCount = 1
        call_prm.opt.videoCount = 0

        # Make the call
        self._pj_call.makeCall(dest_uri, call_prm)
        logger.info(f"Initiating call to {destination} (Call-ID: {self.info.call_id})")

    def on_call_state(self, info):
        """Callback when call state changes."""
        state = info.state
        reason = info.lastReason

        if state == pj.PJSIP_INV_STATE_CALLING:
            self.info.state = CallState.CALLING
            logger.info(f"Call {self.info.call_id}: Calling...")
        elif state == pj.PJSIP_INV_STATE_EARLY:
            self.info.state = CallState.RINGING
            logger.info(f"Call {self.info.call_id}: Ringing")
        elif state == pj.PJSIP_INV_STATE_CONFIRMED:
            self.info.state = CallState.CONFIRMED
            self.info.answered_at = time.time()
            logger.info(f"Call {self.info.call_id}: Answered!")
        elif state == pj.PJSIP_INV_STATE_DISCONNECTED:
            self.info.state = CallState.DISCONNECTED
            self.info.ended_at = time.time()
            self.info.hangup_reason = reason
            logger.info(f"Call {self.info.call_id}: Disconnected - {reason}")

    def on_call_media_state(self, info):
        """Callback when call media state changes."""
        if not self._pj_call:
            return

        # Connect audio media to speaker/mic for monitoring (optional)
        # For auto-dialer, we primarily play audio files
        call_info = self._pj_call.getInfo()

        for mi in call_info.media:
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                # Audio media is active - can play/record audio
                logger.debug(f"Call {self.info.call_id}: Audio media active")

    def on_dtmf_digit(self, digit: str):
        """Callback when DTMF digit is received."""
        self.info.dtmf_buffer.append(digit)
        logger.debug(f"Call {self.info.call_id}: DTMF digit received: {digit}")

        if self._dtmf_callback:
            self._dtmf_callback(digit)

    def set_dtmf_callback(self, callback: Callable[[str], None]):
        """Set callback for DTMF digit reception."""
        self._dtmf_callback = callback

    def hangup(self):
        """Hang up the call."""
        if self._pj_call:
            prm = pj.CallOpParam()
            prm.statusCode = 200
            try:
                self._pj_call.hangup(prm)
            except Exception as e:
                logger.warning(f"Error hanging up call: {e}")
            finally:
                self.info.state = CallState.DISCONNECTED
                self.info.ended_at = time.time()

    def get_audio_media(self):
        """Get the audio media for this call."""
        if not self._pj_call:
            return None

        call_info = self._pj_call.getInfo()
        for i, mi in enumerate(call_info.media):
            if mi.type == pj.PJMEDIA_TYPE_AUDIO and mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                return self._pj_call.getAudioMedia(i)
        return None


class SIPEngine:
    """
    Main SIP engine using PJSUA2.

    Manages the PJSIP endpoint, transport, and coordinates
    account registration and call handling.
    """

    def __init__(self):
        self._endpoint: Optional[Any] = None
        self._transport: Optional[Any] = None
        self._account: Optional[SIPAccount] = None
        self._calls: Dict[str, SIPCall] = {}
        self._initialized = False
        self._pjsua_thread: Optional[threading.Thread] = None
        self._running = False

        # Configuration
        self.sip_server = ""
        self.sip_port = 5060
        self.local_port = 5061
        self.rtp_port_start = 10000
        self.rtp_port_end = 20000
        self.codecs = ["PCMU/8000", "PCMA/8000", "G722/16000"]

    @property
    def is_registered(self) -> bool:
        """Check if currently registered with SIP server."""
        return (self._account is not None and
                self._account.state == RegistrationState.REGISTERED)

    @property
    def registration_state(self) -> RegistrationState:
        """Get current registration state."""
        if self._account:
            return self._account.state
        return RegistrationState.UNREGISTERED

    def initialize(
        self,
        sip_server: str,
        sip_port: int = 5060,
        local_port: int = 5061,
        rtp_port_start: int = 10000,
        rtp_port_end: int = 20000,
        codecs: Optional[List[str]] = None,
        log_level: int = 3
    ):
        """
        Initialize the PJSIP library and endpoint.

        Args:
            sip_server: UCM server address
            sip_port: SIP port (default 5060)
            local_port: Local SIP port to bind (default 5061)
            rtp_port_start: Start of RTP port range
            rtp_port_end: End of RTP port range
            codecs: List of codecs to enable
            log_level: PJSIP log level (0-6)
        """
        if not PJSUA2_AVAILABLE:
            raise RuntimeError(
                "PJSUA2 not available. Install PJSIP with Python bindings. "
                "On Windows, build from source: https://github.com/pjsip/pjproject"
            )

        if self._initialized:
            logger.warning("SIP engine already initialized")
            return

        self.sip_server = sip_server
        self.sip_port = sip_port
        self.local_port = local_port
        self.rtp_port_start = rtp_port_start
        self.rtp_port_end = rtp_port_end
        if codecs:
            self.codecs = codecs

        logger.info(f"Initializing SIP engine for {sip_server}:{sip_port}")

        # Create endpoint
        self._endpoint = pj.Endpoint()
        self._endpoint.libCreate()

        # Configure endpoint
        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = log_level
        ep_cfg.logConfig.consoleLevel = log_level

        # Media config
        ep_cfg.medConfig.clockRate = 8000
        ep_cfg.medConfig.sndClockRate = 8000
        ep_cfg.medConfig.channelCount = 1
        ep_cfg.medConfig.audioFramePtime = 20
        ep_cfg.medConfig.noVad = True

        # RTP port range
        ep_cfg.medConfig.rtpPortStart = rtp_port_start
        ep_cfg.medConfig.rtpPortEnd = rtp_port_end

        # Initialize
        self._endpoint.libInit(ep_cfg)

        # Set null audio device (no physical audio device in Docker)
        # This allows calls to be made without a sound card
        try:
            self._endpoint.audDevManager().setNullDev()
            logger.info("Using null audio device")
        except Exception as e:
            logger.warning(f"Could not set null audio device: {e}")

        # Create UDP transport
        tp_cfg = pj.TransportConfig()
        tp_cfg.port = local_port
        self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)

        # Start the library
        self._endpoint.libStart()

        # Configure codec priority
        self._configure_codecs()

        self._initialized = True
        self._running = True

        logger.info("SIP engine initialized successfully")

    def _configure_codecs(self):
        """Configure codec priorities."""
        if not self._endpoint:
            return

        # Disable all codecs first
        codec_infos = self._endpoint.codecEnum2()
        for ci in codec_infos:
            self._endpoint.codecSetPriority(ci.codecId, 0)

        # Enable preferred codecs with priority
        priority = 255
        for codec in self.codecs:
            try:
                self._endpoint.codecSetPriority(codec, priority)
                priority -= 1
                logger.debug(f"Enabled codec: {codec}")
            except Exception as e:
                logger.warning(f"Could not enable codec {codec}: {e}")

    def register(
        self,
        username: str,
        password: str,
        server: Optional[str] = None,
        port: Optional[int] = None,
        transport: str = "UDP"
    ):
        """
        Register as a PJSIP extension with the UCM.

        Args:
            username: SIP extension/username
            password: SIP password
            server: SIP server (uses initialized server if not provided)
            port: SIP port (uses initialized port if not provided)
            transport: Transport protocol (UDP, TCP, TLS)
        """
        if not self._initialized:
            raise RuntimeError("SIP engine not initialized")

        server = server or self.sip_server
        port = port or self.sip_port

        logger.info(f"Registering as {username}@{server}:{port}")

        # Create account
        self._account = SIPAccount(self)
        self._account.create(server, port, username, password, transport)

    def make_call(self, destination: str, caller_id: str = "") -> SIPCall:
        """
        Initiate an outbound call.

        Args:
            destination: Phone number or SIP URI to call
            caller_id: Caller ID to display

        Returns:
            SIPCall object representing the call
        """
        if not self.is_registered:
            raise RuntimeError("Not registered with SIP server")

        call_id = f"call-{uuid.uuid4().hex[:12]}"
        call = SIPCall(self._account, call_id)
        call.make_call(destination, caller_id)

        self._calls[call_id] = call
        return call

    def hangup_call(self, call_id: str):
        """Hang up a call by ID."""
        call = self._calls.get(call_id)
        if call:
            call.hangup()

    def hangup_all(self):
        """Hang up all active calls."""
        for call in list(self._calls.values()):
            call.hangup()

    def get_call(self, call_id: str) -> Optional[SIPCall]:
        """Get a call by ID."""
        return self._calls.get(call_id)

    def unregister(self):
        """Unregister from the SIP server."""
        if self._account:
            self._account.unregister()

    def shutdown(self):
        """Shutdown the SIP engine."""
        logger.info("Shutting down SIP engine...")

        self._running = False

        # Hang up all calls
        self.hangup_all()

        # Unregister
        if self._account:
            self._account.shutdown()
            self._account = None

        # Destroy endpoint
        if self._endpoint:
            self._endpoint.libDestroy()
            self._endpoint = None

        self._initialized = False
        logger.info("SIP engine shutdown complete")


# PJSUA2 callback classes (internal)
if PJSUA2_AVAILABLE:

    class _PJAccount(pj.Account):
        """Internal PJSUA2 Account with callbacks."""

        def __init__(self, wrapper: SIPAccount):
            super().__init__()
            self._wrapper = wrapper

        def onRegState(self, prm):
            """Called when registration state changes."""
            info = self.getInfo()
            self._wrapper.on_reg_state(info)

    class _PJCall(pj.Call):
        """Internal PJSUA2 Call with callbacks."""

        def __init__(self, wrapper: SIPCall, account: _PJAccount):
            super().__init__(account)
            self._wrapper = wrapper

        def onCallState(self, prm):
            """Called when call state changes."""
            info = self.getInfo()
            self._wrapper.on_call_state(info)

        def onCallMediaState(self, prm):
            """Called when call media state changes."""
            info = self.getInfo()
            self._wrapper.on_call_media_state(info)

        def onDtmfDigit(self, prm):
            """Called when DTMF digit is received."""
            self._wrapper.on_dtmf_digit(prm.digit)
