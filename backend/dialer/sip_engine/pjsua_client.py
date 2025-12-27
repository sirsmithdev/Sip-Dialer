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
    with the Grandstream UCM. Acts like a SIP handset - always
    registered and ready to receive/make calls.
    """

    def __init__(self, engine: 'SIPEngine'):
        self.engine = engine
        self.state = RegistrationState.UNREGISTERED
        self.last_error = ""
        self._pj_account: Optional[Any] = None
        self._inbound_call_handler: Optional[Callable] = None
        self._last_reg_time: float = 0

    def create(self, server: str, port: int, username: str, password: str, transport: str = "UDP", srtp_mode: int = 0):
        """Create and configure the PJSUA2 account."""
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        transport = transport.upper()

        # Create account config
        acc_cfg = pj.AccountConfig()

        # Use proper SIP URI format based on transport
        if transport == "TLS":
            # For TLS, we can use sips: scheme or specify transport parameter
            acc_cfg.idUri = f"sip:{username}@{server}"
            acc_cfg.regConfig.registrarUri = f"sip:{server}:{port};transport=tls"
        elif transport == "TCP":
            acc_cfg.idUri = f"sip:{username}@{server}"
            acc_cfg.regConfig.registrarUri = f"sip:{server}:{port};transport=tcp"
        else:
            # UDP (default)
            acc_cfg.idUri = f"sip:{username}@{server}"
            acc_cfg.regConfig.registrarUri = f"sip:{server}:{port}"

        acc_cfg.regConfig.timeoutSec = 3600
        # Retry registration every 60 seconds on failure
        acc_cfg.regConfig.retryIntervalSec = 60
        # First retry after 5 seconds
        acc_cfg.regConfig.firstRetryIntervalSec = 5

        # Add authentication credentials
        cred = pj.AuthCredInfo("digest", "*", username, 0, password)
        acc_cfg.sipConfig.authCreds.append(cred)

        # Configure SRTP (Secure RTP) for media encryption
        # srtpUse: 0=disabled, 1=optional, 2=mandatory
        acc_cfg.mediaConfig.srtpUse = srtp_mode
        # srtpSecureSignaling: 0=not required, 1=require TLS/SIPS, 2=end-to-end only
        # Set to 0 to avoid PJSIP_ESESSIONINSECURE errors - we already use TLS
        # but the strict check can fail due to certificate/security chain issues
        acc_cfg.mediaConfig.srtpSecureSignaling = 0  # Don't require TLS for SRTP key exchange

        srtp_mode_names = {0: "DISABLED", 1: "OPTIONAL", 2: "MANDATORY"}
        logger.info(f"Account SRTP config: srtpUse={srtp_mode_names.get(srtp_mode, 'UNKNOWN')}, srtpSecureSignaling=0")

        # DTMF configuration for Grandstream UCM compatibility
        # Grandstream default: RFC2833 (preferred), also supports SIP INFO and Inband
        # PJMEDIA_DTMF_METHOD_RFC2833 = 0 (default)
        # PJMEDIA_DTMF_METHOD_SIP_INFO = 1
        # PJMEDIA_DTMF_METHOD_INBAND = 2
        # acc_cfg.mediaConfig.dtmfMethod = 0  # RFC2833 is default

        # Enable ICE for NAT traversal (helps with Grandstream Direct Media)
        acc_cfg.natConfig.iceEnabled = False  # Disabled by default, Grandstream may not support
        # Disable TURN (requires external TURN server)
        acc_cfg.natConfig.turnEnabled = False

        # Contact rewrite for NAT - update Contact header with actual public address
        # This helps when behind NAT - PJSIP will rewrite Contact with learned address
        acc_cfg.natConfig.contactRewriteUse = 1
        acc_cfg.natConfig.contactRewriteMethod = 2  # PJSUA_CONTACT_REWRITE_ALWAYS

        # Via header rewrite for NAT
        acc_cfg.natConfig.viaRewriteUse = True

        # SDP NAT rewrite - update SDP with public IP
        acc_cfg.natConfig.sdpNatRewriteUse = True

        logger.info("Account NAT config: contactRewrite=ON, viaRewrite=ON, sdpNatRewrite=ON")

        # Create the account with callback handler
        self._pj_account = _PJAccount(self)
        self._pj_account.create(acc_cfg)

        self.state = RegistrationState.REGISTERING
        logger.info(f"Created SIP account: {username}@{server}:{port} via {transport}")

    def on_reg_state(self, info):
        """Callback when registration state changes."""
        # PJSUA2 AccountInfo uses regStatus and regStatusText
        code = info.regStatus
        reason = info.regStatusText

        if code == 200:
            self.state = RegistrationState.REGISTERED
            self._last_reg_time = time.time()
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

    def on_incoming_call(self, call: 'SIPCall'):
        """Callback when an incoming call is received."""
        logger.info(f"Incoming call from {call.info.caller_id} to {call.info.destination}")

        if self._inbound_call_handler:
            try:
                self._inbound_call_handler(call)
            except Exception as e:
                logger.error(f"Error in inbound call handler: {e}")
                call.hangup()
        else:
            logger.warning("No inbound call handler registered - rejecting call")
            call.hangup()

    def set_inbound_call_handler(self, handler: Callable):
        """Set the handler for incoming calls."""
        self._inbound_call_handler = handler
        logger.info("Inbound call handler registered")

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

    def answer(self, code: int = 200):
        """Answer an incoming call."""
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        if self._pj_call:
            prm = pj.CallOpParam()
            prm.statusCode = code
            self._pj_call.answer(prm)
            logger.info(f"Answered call {self.info.call_id} with code {code}")

    def make_call(self, destination: str, caller_id: str = ""):
        """Initiate an outbound call."""
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("PJSUA2 not available")

        self.info.destination = destination
        self.info.caller_id = caller_id
        self.info.state = CallState.CALLING

        # Build destination URI with transport parameter matching registration
        server = self.account.engine.sip_server
        port = self.account.engine.sip_port
        transport = self.account.engine.transport_type

        # Include transport in call URI to match registration transport
        if transport == "TLS":
            dest_uri = f"sip:{destination}@{server}:{port};transport=tls"
        elif transport == "TCP":
            dest_uri = f"sip:{destination}@{server}:{port};transport=tcp"
        else:
            dest_uri = f"sip:{destination}@{server}:{port}"

        logger.info(f"Call destination URI: {dest_uri}")

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

        # Log media state changes for debugging
        call_info = self._pj_call.getInfo()

        for i, mi in enumerate(call_info.media):
            if mi.type == pj.PJMEDIA_TYPE_AUDIO:
                if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    # Audio media is active - ready for file playback
                    # Note: We use null audio device, so we don't connect to physical audio
                    # AudioMediaPlayer will transmit directly to the call's audio slot
                    logger.info(f"Call {self.info.call_id}: Audio media ACTIVE (slot {i}) - ready for playback")
                elif mi.status == pj.PJSUA_CALL_MEDIA_LOCAL_HOLD:
                    logger.info(f"Call {self.info.call_id}: Audio on hold (local)")
                elif mi.status == pj.PJSUA_CALL_MEDIA_REMOTE_HOLD:
                    logger.info(f"Call {self.info.call_id}: Audio on hold (remote)")
                elif mi.status == pj.PJSUA_CALL_MEDIA_NONE:
                    logger.debug(f"Call {self.info.call_id}: Audio media inactive")

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

    def send_dtmf(self, digits: str, method: int = 0):
        """
        Send DTMF digits to the remote party.

        Args:
            digits: DTMF digits to send (0-9, *, #, A-D)
            method: DTMF method:
                    0 = RFC2833 (default, preferred for Grandstream)
                    1 = SIP INFO
                    2 = Inband (requires G.711)
        """
        if not self._pj_call or self.info.state != CallState.CONFIRMED:
            logger.warning(f"Cannot send DTMF - call not active")
            return False

        try:
            prm = pj.CallOpParam()
            prm.options = method  # DTMF method
            for digit in digits:
                self._pj_call.dialDtmf(digit)
                logger.debug(f"Call {self.info.call_id}: Sent DTMF '{digit}'")
            logger.info(f"Call {self.info.call_id}: Sent DTMF digits '{digits}'")
            return True
        except Exception as e:
            logger.error(f"Failed to send DTMF: {e}")
            return False

    def get_media_info(self) -> dict:
        """
        Get detailed media information for this call.
        Useful for debugging Grandstream compatibility issues.
        """
        if not self._pj_call:
            return {}

        try:
            call_info = self._pj_call.getInfo()
            media_info = {
                "media_count": len(call_info.media),
                "streams": []
            }

            for i, mi in enumerate(call_info.media):
                stream_info = {
                    "index": i,
                    "type": "audio" if mi.type == pj.PJMEDIA_TYPE_AUDIO else "video" if mi.type == pj.PJMEDIA_TYPE_VIDEO else "unknown",
                    "status": self._media_status_str(mi.status),
                    "direction": mi.dir
                }
                media_info["streams"].append(stream_info)

            return media_info
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return {}

    def _media_status_str(self, status) -> str:
        """Convert media status to string."""
        status_map = {
            pj.PJSUA_CALL_MEDIA_NONE: "none",
            pj.PJSUA_CALL_MEDIA_ACTIVE: "active",
            pj.PJSUA_CALL_MEDIA_LOCAL_HOLD: "local_hold",
            pj.PJSUA_CALL_MEDIA_REMOTE_HOLD: "remote_hold",
            pj.PJSUA_CALL_MEDIA_ERROR: "error"
        }
        return status_map.get(status, f"unknown({status})")


class SRTPMode:
    """SRTP mode constants matching PJSUA2."""
    DISABLED = 0   # PJMEDIA_SRTP_DISABLED
    OPTIONAL = 1   # PJMEDIA_SRTP_OPTIONAL
    MANDATORY = 2  # PJMEDIA_SRTP_MANDATORY


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
        self.transport_type = "UDP"  # Default transport type
        self.srtp_mode = SRTPMode.DISABLED  # Default SRTP mode

        # Configuration
        self.sip_server = ""
        self.sip_port = 5060
        self.local_port = 5061
        self.rtp_port_start = 10000
        self.rtp_port_end = 20000
        # Grandstream UCM compatible codecs (priority order)
        # PCMU (G.711 μ-law) - Primary, universal compatibility
        # PCMA (G.711 A-law) - Secondary, EU standard
        # G722 - Wideband for better quality when supported
        # telephone-event - RFC2833 DTMF support (critical for Grandstream)
        self.codecs = ["PCMU/8000", "PCMA/8000", "G722/16000", "telephone-event/8000"]

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
        log_level: int = 3,
        transport: str = "UDP",
        srtp_mode: int = 0
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
            transport: Transport protocol (UDP, TCP, TLS)
            srtp_mode: SRTP mode (0=disabled, 1=optional, 2=mandatory)
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
        self.transport_type = transport.upper()
        self.srtp_mode = srtp_mode
        if codecs:
            self.codecs = codecs

        srtp_mode_names = {0: "DISABLED", 1: "OPTIONAL", 2: "MANDATORY"}
        logger.info(f"Initializing SIP engine for {sip_server}:{sip_port} using {self.transport_type}, SRTP={srtp_mode_names.get(srtp_mode, 'UNKNOWN')}")

        # Create endpoint
        self._endpoint = pj.Endpoint()
        self._endpoint.libCreate()

        # Configure endpoint
        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = log_level
        ep_cfg.logConfig.consoleLevel = log_level

        # User Agent config for NAT traversal
        # Enable symmetric RTP - critical for NAT/firewall traversal with Grandstream
        # This ensures RTP is sent from the same port it's received on
        ep_cfg.uaConfig.natTypeInSdp = 1

        # Media config - optimized for Grandstream UCM
        ep_cfg.medConfig.clockRate = 8000
        ep_cfg.medConfig.sndClockRate = 8000
        ep_cfg.medConfig.channelCount = 1
        ep_cfg.medConfig.audioFramePtime = 20  # 20ms ptime - standard for G.711
        ep_cfg.medConfig.noVad = True  # Disable VAD - Grandstream prefers continuous audio

        # Enable symmetric RTP at media level for NAT traversal
        # This is critical for cloud VPS where public IP differs from local IP
        ep_cfg.medConfig.enableSymRtp = True

        # RTP port range
        ep_cfg.medConfig.rtpPortStart = rtp_port_start
        ep_cfg.medConfig.rtpPortEnd = rtp_port_end

        # STUN server for NAT traversal (optional but recommended)
        import os
        stun_server = os.environ.get('STUN_SERVER', 'stun.l.google.com:19302')
        if stun_server:
            ep_cfg.uaConfig.stunServer.append(stun_server)
            logger.info(f"NAT: Using STUN server {stun_server}")

        # Initialize
        self._endpoint.libInit(ep_cfg)

        # Set null audio device (no physical audio device in Docker)
        # This allows calls to be made without a sound card
        try:
            self._endpoint.audDevManager().setNullDev()
            logger.info("Using null audio device")
        except Exception as e:
            logger.warning(f"Could not set null audio device: {e}")

        # Create transport based on type
        tp_cfg = pj.TransportConfig()
        tp_cfg.port = local_port

        # Configure public IP for NAT traversal (important for cloud VPS)
        import os
        public_ip = os.environ.get('PUBLIC_IP', '')
        if public_ip:
            tp_cfg.publicAddress = public_ip
            logger.info(f"NAT: Using public IP {public_ip} for SDP")

        if self.transport_type == "TLS":
            # Configure TLS transport
            try:
                # TLS configuration
                tp_cfg.tlsConfig.method = pj.PJSIP_TLSV1_2_METHOD
                # For Grandstream UCM, we may need to accept self-signed certs
                tp_cfg.tlsConfig.verifyServer = False
                tp_cfg.tlsConfig.verifyClient = False

                self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_TLS, tp_cfg)
                logger.info(f"Created TLS transport on port {local_port}")
            except Exception as e:
                logger.error(f"Failed to create TLS transport: {e}")
                logger.info("Falling back to UDP transport")
                tp_cfg = pj.TransportConfig()
                tp_cfg.port = local_port
                self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)
        elif self.transport_type == "TCP":
            try:
                self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_TCP, tp_cfg)
                logger.info(f"Created TCP transport on port {local_port}")
            except Exception as e:
                logger.error(f"Failed to create TCP transport: {e}")
                logger.info("Falling back to UDP transport")
                self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)
        else:
            # Default to UDP
            self._transport = self._endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, tp_cfg)
            logger.info(f"Created UDP transport on port {local_port}")

        # Start the library
        self._endpoint.libStart()

        # Configure codec priority
        self._configure_codecs()

        self._initialized = True
        self._running = True

        logger.info(f"SIP engine initialized successfully with {self.transport_type} transport")

    def _configure_codecs(self):
        """Configure codec priorities optimized for Grandstream UCM."""
        if not self._endpoint:
            return

        # Log available codecs for debugging
        codec_infos = self._endpoint.codecEnum2()
        available = [ci.codecId for ci in codec_infos]
        logger.info(f"Available codecs: {available}")

        # Disable all codecs first
        for ci in codec_infos:
            self._endpoint.codecSetPriority(ci.codecId, 0)

        # Enable preferred codecs with priority
        # Higher priority = preferred codec
        priority = 255
        enabled_codecs = []
        for codec in self.codecs:
            try:
                self._endpoint.codecSetPriority(codec, priority)
                enabled_codecs.append(f"{codec}({priority})")
                priority -= 1
            except Exception as e:
                logger.warning(f"Could not enable codec {codec}: {e}")

        logger.info(f"Enabled codecs (priority order): {enabled_codecs}")

        # Configure codec parameters for Grandstream compatibility
        # G.711: 20ms ptime is standard and compatible with all systems
        # Grandstream UCM default is 20ms ptime for G.711
        try:
            # PCMU settings
            param = self._endpoint.codecGetParam("PCMU/8000")
            param.setting.frmTime = 20  # 20ms ptime
            self._endpoint.codecSetParam("PCMU/8000", param)

            # PCMA settings
            param = self._endpoint.codecGetParam("PCMA/8000")
            param.setting.frmTime = 20  # 20ms ptime
            self._endpoint.codecSetParam("PCMA/8000", param)

            logger.info("Codec parameters configured: G.711 ptime=20ms")
        except Exception as e:
            logger.debug(f"Could not configure codec parameters: {e}")

    def register(
        self,
        username: str,
        password: str,
        server: Optional[str] = None,
        port: Optional[int] = None,
        transport: str = "UDP",
        srtp_mode: Optional[int] = None
    ):
        """
        Register as a PJSIP extension with the UCM.

        Args:
            username: SIP extension/username
            password: SIP password
            server: SIP server (uses initialized server if not provided)
            port: SIP port (uses initialized port if not provided)
            transport: Transport protocol (UDP, TCP, TLS)
            srtp_mode: SRTP mode (0=disabled, 1=optional, 2=mandatory)
        """
        if not self._initialized:
            raise RuntimeError("SIP engine not initialized")

        server = server or self.sip_server
        port = port or self.sip_port
        # Use provided srtp_mode or fall back to engine's default
        srtp = srtp_mode if srtp_mode is not None else self.srtp_mode

        logger.info(f"Registering as {username}@{server}:{port}")

        # Create account
        self._account = SIPAccount(self)
        self._account.create(server, port, username, password, transport, srtp)

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

    def set_inbound_call_handler(self, handler: Callable):
        """Set the handler for incoming calls (handset mode)."""
        if self._account:
            self._account.set_inbound_call_handler(handler)
        else:
            logger.warning("Cannot set inbound handler - no account registered")

    def add_inbound_call(self, call: SIPCall):
        """Track an inbound call."""
        self._calls[call.info.call_id] = call
        logger.info(f"Tracking inbound call: {call.info.call_id}")

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

        def onIncomingCall(self, prm):
            """Called when an incoming call is received."""
            try:
                # Create a SIPCall wrapper for the incoming call
                call = SIPCall(self._wrapper, f"inbound-{uuid.uuid4().hex[:12]}")
                call._pj_call = _PJCall(call, self)

                # Get call info
                call_info = call._pj_call.getInfo()
                call.info.caller_id = call_info.remoteUri
                call.info.destination = call_info.localUri
                call.info.state = CallState.RINGING

                logger.info(f"Incoming call: {call.info.caller_id} -> {call.info.destination}")

                # Notify the wrapper
                self._wrapper.on_incoming_call(call)
            except Exception as e:
                logger.error(f"Error handling incoming call: {e}")

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
