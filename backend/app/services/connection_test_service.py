"""
Connection Test Service for SIP and AMI.
"""
import asyncio
import logging
import socket
import time
from typing import Optional, Tuple

from panoramisk import Manager
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sip_settings import SIPSettings, ChannelDriver
from app.schemas.sip_settings import SIPConnectionTestResponse
from app.core.security import decrypt_password


logger = logging.getLogger(__name__)


# Diagnostic hints for common errors
ERROR_HINTS = {
    "Connection refused": "Port may be blocked by firewall. Check UCM6302 firewall settings and ensure AMI/SIP is enabled.",
    "timed out": "Network connectivity issue. Verify host is reachable and UCM6302 is powered on.",
    "Authentication failed": "Invalid credentials. Verify AMI username and password in UCM6302 → PBX → AMI Users.",
    "No SIP response": "SIP server not responding. Check UCM6302 → SIP Settings → Enable SIP.",
    "Connection reset": "Server closed connection. AMI may be disabled or max connections reached.",
    "Invalid SIP response": "Received malformed SIP response. Server may not be a valid SIP server.",
}


class ConnectionTestService:
    """Service for testing SIP and AMI connections."""

    def __init__(self, db: AsyncSession, app_logger: logging.Logger):
        self.db = db
        self.logger = app_logger

    def _get_diagnostic_hint(self, error_message: str) -> Optional[str]:
        """Get a user-friendly diagnostic hint based on error message."""
        error_lower = error_message.lower()
        for key, hint in ERROR_HINTS.items():
            if key.lower() in error_lower:
                return hint
        return None

    async def test_ami_connection(self, settings: SIPSettings) -> SIPConnectionTestResponse:
        """
        Test AMI connection with full authentication.

        Steps:
        1. Resolve DNS to IP
        2. Connect to AMI port
        3. Authenticate with credentials
        4. Execute Ping command
        5. Retrieve server version
        """
        ami_host = settings.ami_host or settings.sip_server
        ami_port = settings.ami_port
        ami_username = settings.ami_username or "admin"
        ami_password = decrypt_password(settings.ami_password_encrypted)

        test_steps = []
        start_time = time.time()

        self.logger.info(
            f"Starting AMI test to {ami_host}:{ami_port}"
        )

        try:
            # Step 1: Resolve DNS
            try:
                resolved_ip = socket.gethostbyname(ami_host)
            except socket.gaierror:
                resolved_ip = ami_host  # Assume it's already an IP

            # Step 2-4: Connect and authenticate using panoramisk
            manager = Manager(
                host=ami_host,
                port=ami_port,
                username=ami_username,
                secret=ami_password,
                ssl=False,
                ping_delay=None  # Disable automatic ping for test
            )

            try:
                # Connect with timeout
                await asyncio.wait_for(manager.connect(), timeout=10.0)
                test_steps.append(f"✓ Connected to {resolved_ip}:{ami_port}")

                # Authentication happens automatically during connect
                test_steps.append(f"✓ Authenticated as {ami_username}")

                # Execute Ping command to verify functionality
                response = await asyncio.wait_for(
                    manager.send_action({'Action': 'Ping'}),
                    timeout=5.0
                )

                if response and response.get('Response') == 'Success':
                    test_steps.append("✓ AMI Ping successful")
                else:
                    test_steps.append("⚠ AMI Ping returned unexpected response")

                # Try to get Asterisk version
                server_info = {}
                try:
                    ver_response = await asyncio.wait_for(
                        manager.send_action({'Action': 'CoreShowVersion'}),
                        timeout=5.0
                    )
                    if ver_response and 'CoreShowVersion' in ver_response:
                        server_info['version'] = ver_response.get('CoreShowVersion', 'Unknown')
                except Exception:
                    pass  # Version retrieval is optional

                # Close connection
                await manager.close()

                timing_ms = int((time.time() - start_time) * 1000)

                self.logger.info(f"AMI test completed: success=True, timing={timing_ms}ms")

                return SIPConnectionTestResponse(
                    success=True,
                    message=f"Successfully connected and authenticated to AMI at {ami_host}:{ami_port}",
                    details={"host": ami_host, "port": ami_port},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    server_info=server_info if server_info else None,
                    authenticated=True,
                    diagnostic_hint=None
                )

            except asyncio.TimeoutError:
                timing_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Connection timed out after 10 seconds"
                self.logger.warning(f"AMI connection failed: timeout after 10s")

                return SIPConnectionTestResponse(
                    success=False,
                    message=error_msg,
                    details={"host": ami_host, "port": ami_port},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps + [f"✗ {error_msg}"],
                    authenticated=False,
                    diagnostic_hint=self._get_diagnostic_hint("timed out")
                )

            except Exception as e:
                timing_ms = int((time.time() - start_time) * 1000)
                error_msg = str(e)

                # Check if it's an authentication error
                if "authentication" in error_msg.lower() or "incorrect" in error_msg.lower():
                    self.logger.error(f"AMI authentication failed for user {ami_username}: {error_msg}")
                    test_steps.append(f"✗ Authentication failed")
                    authenticated = False
                    hint = self._get_diagnostic_hint("Authentication failed")
                else:
                    self.logger.error(f"AMI connection error: {error_msg}")
                    test_steps.append(f"✗ {error_msg}")
                    authenticated = None
                    hint = self._get_diagnostic_hint(error_msg)

                return SIPConnectionTestResponse(
                    success=False,
                    message=f"AMI connection failed: {error_msg}",
                    details={"host": ami_host, "port": ami_port, "error": error_msg},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    authenticated=authenticated,
                    diagnostic_hint=hint
                )

        except Exception as e:
            timing_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self.logger.error(f"AMI test failed unexpectedly: {error_msg}", exc_info=True)

            return SIPConnectionTestResponse(
                success=False,
                message=f"AMI test failed: {error_msg}",
                details={"host": ami_host, "port": ami_port, "error": error_msg},
                timing_ms=timing_ms,
                test_steps=[f"✗ {error_msg}"],
                diagnostic_hint=self._get_diagnostic_hint(error_msg)
            )

    async def test_sip_connection(self, settings: SIPSettings) -> SIPConnectionTestResponse:
        """
        Test SIP connection with proper OPTIONS request.

        Steps:
        1. Resolve DNS to IP
        2. Create proper SIP OPTIONS request
        3. Send via UDP
        4. Wait for response (5 second timeout)
        5. Parse response
        """
        sip_server = settings.sip_server
        sip_port = settings.sip_port
        sip_username = settings.sip_username

        test_steps = []
        start_time = time.time()

        self.logger.info(f"Starting SIP test to {sip_server}:{sip_port}")

        try:
            # Step 1: Resolve DNS
            try:
                resolved_ip = socket.gethostbyname(sip_server)
            except socket.gaierror:
                resolved_ip = sip_server  # Assume it's already an IP

            # Step 2: Create proper SIP OPTIONS request
            call_id = f"test-{int(time.time())}"
            sip_request = (
                f"OPTIONS sip:{sip_server} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {resolved_ip}:{sip_port};branch=z9hG4bK-test\r\n"
                f"From: <sip:{sip_username}@{sip_server}>;tag=test\r\n"
                f"To: <sip:{sip_server}>\r\n"
                f"Call-ID: {call_id}\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Contact: <sip:{sip_username}@{resolved_ip}:{sip_port}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: SIP-Autodialer-Test\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )

            # Step 3 & 4: Send and wait for response
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)

            try:
                sock.sendto(sip_request.encode(), (resolved_ip, sip_port))
                test_steps.append(f"✓ Sent SIP OPTIONS to {resolved_ip}:{sip_port}")

                # Wait for response
                data, addr = sock.recvfrom(4096)
                response = data.decode('utf-8', errors='ignore')

                test_steps.append(f"✓ Received response from {addr[0]}:{addr[1]}")

                # Step 5: Parse response
                server_info = {}
                lines = response.split('\r\n')

                # Check status line
                if lines:
                    status_line = lines[0]
                    if 'SIP/2.0' in status_line:
                        test_steps.append(f"✓ Valid SIP response: {status_line}")

                        # Extract headers
                        for line in lines[1:]:
                            if line.startswith('Server:') or line.startswith('User-Agent:'):
                                server_info['server'] = line.split(':', 1)[1].strip()
                                test_steps.append(f"Server: {server_info['server']}")
                                break
                    else:
                        test_steps.append("⚠ Received non-SIP response")
                        server_info['note'] = "Response doesn't appear to be valid SIP"

                sock.close()
                timing_ms = int((time.time() - start_time) * 1000)

                self.logger.info(f"SIP test completed: success=True, timing={timing_ms}ms")

                return SIPConnectionTestResponse(
                    success=True,
                    message=f"Successfully received SIP response from {sip_server}:{sip_port}",
                    details={"host": sip_server, "port": sip_port},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    server_info=server_info if server_info else None,
                    diagnostic_hint=None
                )

            except socket.timeout:
                sock.close()
                timing_ms = int((time.time() - start_time) * 1000)
                error_msg = "No SIP response received (timeout after 5 seconds)"
                self.logger.warning(f"SIP OPTIONS request - no response received")

                test_steps.append(f"✗ {error_msg}")

                return SIPConnectionTestResponse(
                    success=False,
                    message=error_msg,
                    details={"host": sip_server, "port": sip_port},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    diagnostic_hint=self._get_diagnostic_hint("No SIP response")
                )

            except Exception as e:
                sock.close()
                raise e

        except Exception as e:
            timing_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            self.logger.error(f"SIP test failed: {error_msg}")

            return SIPConnectionTestResponse(
                success=False,
                message=f"SIP test failed: {error_msg}",
                details={"host": sip_server, "port": sip_port, "error": error_msg},
                timing_ms=timing_ms,
                test_steps=test_steps + [f"✗ {error_msg}"],
                diagnostic_hint=self._get_diagnostic_hint(error_msg)
            )

    async def detect_channel_driver(self, settings: SIPSettings) -> Tuple[ChannelDriver, str]:
        """
        Detect which SIP channel driver is active (PJSIP vs chan_sip).

        Returns:
            Tuple of (ChannelDriver enum, description string)

        Strategy:
        1. Connect to AMI
        2. Run 'module show like res_pjsip.so' command
        3. If loaded, return PJSIP
        4. Otherwise check for chan_sip.so
        5. Default to PJSIP if can't determine
        """
        ami_host = settings.ami_host or settings.sip_server
        ami_port = settings.ami_port
        ami_username = settings.ami_username or "admin"
        ami_password = decrypt_password(settings.ami_password_encrypted)

        self.logger.info(f"Detecting channel driver via AMI at {ami_host}:{ami_port}")

        try:
            manager = Manager(
                host=ami_host,
                port=ami_port,
                username=ami_username,
                secret=ami_password,
                ssl=False,
                ping_delay=None
            )

            try:
                # Connect with timeout
                await asyncio.wait_for(manager.connect(), timeout=10.0)

                # Check for PJSIP module
                pjsip_response = await asyncio.wait_for(
                    manager.send_action({
                        'Action': 'Command',
                        'Command': 'module show like res_pjsip.so'
                    }),
                    timeout=5.0
                )

                # Parse response to check if PJSIP is loaded
                if pjsip_response and 'Output' in pjsip_response:
                    output = pjsip_response.get('Output', '')
                    if 'res_pjsip.so' in output and 'Running' in output:
                        await manager.close()
                        self.logger.info("Detected channel driver: PJSIP")
                        return (ChannelDriver.PJSIP, "PJSIP module is loaded and running")

                # Check for chan_sip module (legacy)
                chansip_response = await asyncio.wait_for(
                    manager.send_action({
                        'Action': 'Command',
                        'Command': 'module show like chan_sip.so'
                    }),
                    timeout=5.0
                )

                if chansip_response and 'Output' in chansip_response:
                    output = chansip_response.get('Output', '')
                    if 'chan_sip.so' in output and 'Running' in output:
                        await manager.close()
                        self.logger.info("Detected channel driver: SIP (chan_sip)")
                        return (ChannelDriver.SIP, "chan_sip module is loaded and running")

                # Close connection
                await manager.close()

                # Default to PJSIP (most modern systems use PJSIP)
                self.logger.warning("Could not determine channel driver from modules, defaulting to PJSIP")
                return (ChannelDriver.PJSIP, "Could not detect driver, defaulting to PJSIP")

            except Exception as e:
                self.logger.error(f"Error detecting channel driver: {e}")
                # Default to PJSIP on error
                return (ChannelDriver.PJSIP, f"Error during detection: {str(e)}, defaulting to PJSIP")

        except Exception as e:
            self.logger.error(f"Failed to connect to AMI for driver detection: {e}")
            # Default to PJSIP on connection error
            return (ChannelDriver.PJSIP, f"AMI connection failed: {str(e)}, defaulting to PJSIP")
