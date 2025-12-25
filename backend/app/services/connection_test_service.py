"""
Connection Test Service for SIP/PJSIP.
"""
import json
import logging
import socket
import ssl
import time
from typing import Optional

import redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
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
    "TLS handshake": "TLS connection failed. Check if UCM supports TLS 1.2 and has valid certificates.",
    "SSL": "SSL/TLS error. Try using TCP transport instead, or verify UCM TLS configuration.",
}


class ConnectionTestService:
    """Service for testing SIP connections."""

    def __init__(self, db: AsyncSession, app_logger: logging.Logger):
        self.db = db
        self.logger = app_logger
        self._redis_client = None

    def _get_redis_client(self):
        """Get Redis client for checking dialer status (with SSL support for DO Managed Redis)."""
        if self._redis_client is None:
            redis_url = app_settings.redis_url
            if redis_url.startswith("rediss://"):
                # DigitalOcean Managed Redis uses self-signed certs
                self._redis_client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    ssl_cert_reqs=None,  # Disable cert verification for DO
                    socket_keepalive=True,
                    health_check_interval=30
                )
            else:
                self._redis_client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_keepalive=True,
                    health_check_interval=30
                )
        return self._redis_client

    def _get_dialer_status(self) -> Optional[dict]:
        """Get the current dialer SIP status from Redis."""
        try:
            client = self._get_redis_client()
            status_data = client.get("dialer:sip_status")
            if status_data:
                return json.loads(status_data)
        except Exception as e:
            self.logger.warning(f"Failed to get dialer status from Redis: {e}")
        return None

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
        3. Send via UDP or TCP (based on settings)
        4. Wait for response (5 second timeout)
        5. Parse response
        """
        sip_server = settings.sip_server
        sip_port = settings.sip_port
        sip_username = settings.sip_username
        sip_transport = settings.sip_transport.value if hasattr(settings.sip_transport, 'value') else str(settings.sip_transport)

        test_steps = []
        start_time = time.time()
        sock = None
        dialer_registered = False

        self.logger.info(f"Starting SIP test to {sip_server}:{sip_port} via {sip_transport}")

        # Step 0: Check dialer engine status first (this shows if UCM is responding)
        dialer_status = self._get_dialer_status()
        if dialer_status:
            status = dialer_status.get("status", "unknown")
            extension = dialer_status.get("extension", "unknown")
            active_calls = dialer_status.get("active_calls", 0)

            if status == "registered":
                dialer_registered = True
                test_steps.append(f"✓ Dialer engine registered with UCM as extension {extension}")
                if active_calls > 0:
                    test_steps.append(f"✓ {active_calls} active call(s) in progress")
                self.logger.info(f"Dialer is registered as {extension}, {active_calls} active calls")
            elif status == "unregistered":
                test_steps.append(f"⚠ Dialer engine not currently registered (status: {status})")
            elif status == "error":
                error_detail = dialer_status.get("error", "unknown error")
                test_steps.append(f"✗ Dialer engine error: {error_detail}")
            else:
                test_steps.append(f"⚠ Dialer engine status: {status}")
        else:
            test_steps.append("⚠ Could not retrieve dialer engine status (dialer may be starting up)")

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
                f"Via: SIP/2.0/{sip_transport.upper()} {resolved_ip}:{local_port};branch=z9hG4bK-test-{call_id}\r\n"
                f"From: <sip:{sip_username}@{sip_server}>;tag=test-{call_id}\r\n"
                f"To: <sip:{sip_server}:{sip_port}>\r\n"
                f"Call-ID: {call_id}@autodialer\r\n"
                f"CSeq: 1 OPTIONS\r\n"
                f"Contact: <sip:{sip_username}@{resolved_ip}:{local_port};transport={sip_transport.lower()}>\r\n"
                f"Max-Forwards: 70\r\n"
                f"User-Agent: SIP-Autodialer/1.0\r\n"
                f"Accept: application/sdp\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )

            # Step 3 & 4: Send and wait for response (use TCP, TLS, or UDP based on transport)
            response = None

            if sip_transport.upper() in ("TCP", "TLS"):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)

                # Wrap with TLS if needed
                if sip_transport.upper() == "TLS":
                    # Create TLS context with TLS 1.2 minimum
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE  # UCM may use self-signed certs
                    sock = ssl_context.wrap_socket(sock, server_hostname=sip_server)
                    test_steps.append("✓ Using TLS 1.2+ encryption")

                sock.connect((resolved_ip, sip_port))
                protocol_name = "TLS" if sip_transport.upper() == "TLS" else "TCP"
                test_steps.append(f"✓ {protocol_name} connection established to {resolved_ip}:{sip_port}")
                sock.sendall(sip_request.encode())
                test_steps.append(f"✓ Sent SIP OPTIONS via {protocol_name}")
                # Wait for response
                data = sock.recv(4096)
                response = data.decode('utf-8', errors='ignore')
                test_steps.append(f"✓ Received response from {resolved_ip}:{sip_port}")
            else:
                # UDP (default)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(5.0)
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
            else:
                success = False
                message = "Empty response received"

            if sock:
                sock.close()
            timing_ms = int((time.time() - start_time) * 1000)

            self.logger.info(f"SIP test completed: success={success}, timing={timing_ms}ms")

            # Enhance message if dialer is also registered
            if success and dialer_registered:
                message = f"{message}. Dialer is registered with UCM."
                if server_info is None:
                    server_info = {}
                server_info["dialer_status"] = "registered"

            return SIPConnectionTestResponse(
                success=success,
                message=message,
                details={
                    "host": sip_server,
                    "port": sip_port,
                    "extension": sip_username,
                    "dialer_registered": dialer_registered
                },
                timing_ms=timing_ms,
                resolved_ip=resolved_ip,
                test_steps=test_steps,
                server_info=server_info if server_info else None,
                registered=dialer_registered,
                diagnostic_hint=None if success else self._get_diagnostic_hint(message)
            )

        except socket.timeout:
            if sock:
                sock.close()
            timing_ms = int((time.time() - start_time) * 1000)
            self.logger.warning("SIP OPTIONS request - no response received")

            # If dialer is registered (we checked at start), connection is working
            if dialer_registered:
                # Dialer is registered, so UCM is responding - just not to OPTIONS
                test_steps.append("⚠ UCM did not respond to OPTIONS probe (this is normal for many PBXes)")
                test_steps.append("✓ Connection verified via dialer registration")

                return SIPConnectionTestResponse(
                    success=True,
                    message=f"SIP connection working - dialer is registered with UCM (extension {dialer_status.get('extension', 'unknown')})",
                    details={
                        "host": sip_server,
                        "port": sip_port,
                        "extension": dialer_status.get("extension"),
                        "active_calls": dialer_status.get("active_calls", 0),
                        "note": "UCM is responding to the dialer - OPTIONS probe was ignored (normal behavior)"
                    },
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    server_info={"dialer_status": "registered", "ucm_responding": True},
                    registered=True,
                    diagnostic_hint=None
                )
            else:
                # Dialer not registered and no OPTIONS response - real problem
                error_msg = "No SIP response received (timeout after 5 seconds)"
                test_steps.append(f"✗ {error_msg}")
                test_steps.append("✗ Dialer engine is also not registered with UCM")
                test_steps.append("⚠ Check: UCM firewall, SIP port, credentials, and network connectivity")

                return SIPConnectionTestResponse(
                    success=False,
                    message="SIP connection failed - no response from UCM and dialer not registered",
                    details={"host": sip_server, "port": sip_port},
                    timing_ms=timing_ms,
                    resolved_ip=resolved_ip,
                    test_steps=test_steps,
                    registered=False,
                    diagnostic_hint="The UCM is not responding. Verify the SIP server address, port, and that the UCM firewall allows connections from this server."
                )

        except ConnectionRefusedError as e:
            if sock:
                sock.close()
            timing_ms = int((time.time() - start_time) * 1000)
            error_msg = f"{sip_transport} connection refused to {sip_server}:{sip_port}"
            self.logger.error(f"SIP test failed: {error_msg}")
            test_steps.append(f"✗ {error_msg}")

            return SIPConnectionTestResponse(
                success=False,
                message=f"SIP test failed: {error_msg}",
                details={"host": sip_server, "port": sip_port, "error": error_msg},
                timing_ms=timing_ms,
                resolved_ip=resolved_ip,
                test_steps=test_steps,
                registered=False,
                diagnostic_hint=self._get_diagnostic_hint("Connection refused")
            )

        except ssl.SSLError as e:
            if sock:
                sock.close()
            timing_ms = int((time.time() - start_time) * 1000)
            error_msg = f"TLS handshake failed: {e}"
            self.logger.error(f"SIP test failed: {error_msg}")
            test_steps.append(f"✗ {error_msg}")

            return SIPConnectionTestResponse(
                success=False,
                message=f"SIP test failed: {error_msg}",
                details={"host": sip_server, "port": sip_port, "error": error_msg},
                timing_ms=timing_ms,
                resolved_ip=resolved_ip,
                test_steps=test_steps,
                registered=False,
                diagnostic_hint=self._get_diagnostic_hint("TLS handshake")
            )

        except Exception as e:
            if sock:
                sock.close()
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
