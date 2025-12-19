"""
Connection Test Service for SIP/PJSIP.
"""
import logging
import socket
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sip_settings import SIPSettings
from app.schemas.sip_settings import SIPConnectionTestResponse


logger = logging.getLogger(__name__)


# Diagnostic hints for common errors
ERROR_HINTS = {
    "Connection refused": "Port may be blocked by firewall. Check UCM6302 firewall settings and ensure SIP is enabled.",
    "timed out": "Network connectivity issue. Verify host is reachable and UCM6302 is powered on.",
    "No SIP response": "SIP server not responding. Check UCM6302 → SIP Settings → Enable SIP.",
    "Invalid SIP response": "Received malformed SIP response. Server may not be a valid SIP server.",
    "401 Unauthorized": "Invalid credentials. Verify PJSIP extension username and password on UCM6302.",
    "403 Forbidden": "Access denied. Extension may be disabled or restricted on UCM6302.",
    "404 Not Found": "Extension not found. Verify the PJSIP extension exists on UCM6302.",
}


class ConnectionTestService:
    """Service for testing SIP connections."""

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

    async def test_sip_connection(self, settings: SIPSettings) -> SIPConnectionTestResponse:
        """
        Test SIP connection with OPTIONS request.

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
                test_steps.append(f"✓ Resolved {sip_server} to {resolved_ip}")
            except socket.gaierror:
                resolved_ip = sip_server  # Assume it's already an IP
                test_steps.append(f"✓ Using IP address {resolved_ip}")

            # Step 2: Create proper SIP OPTIONS request
            call_id = f"test-{int(time.time())}"
            local_port = 5061  # Use a different port for the test
            sip_request = (
                f"OPTIONS sip:{sip_server}:{sip_port} SIP/2.0\r\n"
                f"Via: SIP/2.0/UDP {resolved_ip}:{local_port};branch=z9hG4bK-test-{call_id}\r\n"
                f"From: <sip:{sip_username}@{sip_server}>;tag=test-{call_id}\r\n"
                f"To: <sip:{sip_server}:{sip_port}>\r\n"
                f"Call-ID: {call_id}@autodialer\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Contact: <sip:{sip_username}@{resolved_ip}:{local_port}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: SIP-Autodialer/1.0\r\n"
                f"Accept: application/sdp\r\n"
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
                        # Extract status code
                        parts = status_line.split(' ', 2)
                        status_code = int(parts[1]) if len(parts) > 1 else 0
                        status_text = parts[2] if len(parts) > 2 else ''

                        test_steps.append(f"✓ SIP Response: {status_code} {status_text}")

                        # Extract headers
                        for line in lines[1:]:
                            if line.startswith('Server:') or line.startswith('User-Agent:'):
                                server_info['server'] = line.split(':', 1)[1].strip()
                            elif line.startswith('Allow:'):
                                server_info['allow'] = line.split(':', 1)[1].strip()

                        # Determine success based on status code
                        if 200 <= status_code < 300:
                            success = True
                            message = f"SIP server responded successfully: {status_code} {status_text}"
                        elif status_code == 401:
                            success = False
                            message = "Authentication required - credentials will be needed for registration"
                            test_steps.append("✓ Server requires authentication (expected)")
                            # This is actually a good sign - server is alive and will need auth
                            success = True
                        elif status_code == 403:
                            success = False
                            message = f"Access forbidden: {status_code} {status_text}"
                        elif status_code == 404:
                            success = False
                            message = f"Extension not found: {status_code} {status_text}"
                        else:
                            success = status_code < 400
                            message = f"SIP Response: {status_code} {status_text}"
                    else:
                        test_steps.append("⚠ Received non-SIP response")
                        server_info['note'] = "Response doesn't appear to be valid SIP"
                        success = False
                        message = "Invalid SIP response received"

                sock.close()
                timing_ms = int((time.time() - start_time) * 1000)

                self.logger.info(f"SIP test completed: success={success}, timing={timing_ms}ms")

                return SIPConnectionTestResponse(
                    success=success,
                    message=message,
                    details={"host": sip_server, "port": sip_port, "extension": sip_username},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    server_info=server_info if server_info else None,
                    registered=None,  # OPTIONS doesn't register
                    diagnostic_hint=None if success else self._get_diagnostic_hint(message)
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
                    registered=False,
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
                registered=False,
                diagnostic_hint=self._get_diagnostic_hint(error_msg)
            )
