"""
Dialer Engine Main Entry Point.

This module starts the dialer engine that manages outbound calls
through the Grandstream UCM6302 PBX via AMI.
"""
import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from panoramisk import Manager

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DialerEngine:
    """Main dialer engine class."""

    def __init__(self):
        self.running = False
        self.ami_host = os.getenv("AMI_HOST", "192.168.1.100")
        self.ami_port = int(os.getenv("AMI_PORT", "5038"))
        self.ami_username = os.getenv("AMI_USERNAME", "autodialer_ami")
        self.ami_password = os.getenv("AMI_PASSWORD", "")
        self.channel_driver = os.getenv("CHANNEL_DRIVER", "PJSIP")  # PJSIP or SIP
        self.sip_extension = os.getenv("SIP_EXTENSION", "1005")
        self.manager: Optional[Manager] = None

    async def connect_ami(self):
        """Connect to Asterisk Manager Interface."""
        logger.info(f"Connecting to AMI at {self.ami_host}:{self.ami_port}")

        try:
            self.manager = Manager(
                host=self.ami_host,
                port=self.ami_port,
                username=self.ami_username,
                secret=self.ami_password,
                ssl=False,
                ping_delay=30  # Send keepalive ping every 30 seconds
            )

            await asyncio.wait_for(self.manager.connect(), timeout=15.0)
            logger.info(f"Successfully connected to AMI as {self.ami_username}")

            # Verify connection with a ping
            response = await self.manager.send_action({'Action': 'Ping'})
            if response.get('Response') == 'Success':
                logger.info("AMI connection verified with Ping")

            # Detect channel driver if not explicitly set
            if self.channel_driver == "AUTO":
                self.channel_driver = await self._detect_channel_driver()
                logger.info(f"Auto-detected channel driver: {self.channel_driver}")
            else:
                logger.info(f"Using configured channel driver: {self.channel_driver}")

        except asyncio.TimeoutError:
            logger.error("AMI connection timeout after 15 seconds")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to AMI: {e}")
            raise

    async def _detect_channel_driver(self) -> str:
        """
        Detect which SIP channel driver is active (PJSIP vs SIP).

        Returns:
            "PJSIP" or "SIP"
        """
        try:
            # Check for PJSIP module
            response = await self.manager.send_action({
                'Action': 'Command',
                'Command': 'module show like res_pjsip.so'
            })

            if response and 'Output' in response:
                output = response.get('Output', '')
                if 'res_pjsip.so' in output and 'Running' in output:
                    return "PJSIP"

            # Check for chan_sip module (legacy)
            response = await self.manager.send_action({
                'Action': 'Command',
                'Command': 'module show like chan_sip.so'
            })

            if response and 'Output' in response:
                output = response.get('Output', '')
                if 'chan_sip.so' in output and 'Running' in output:
                    return "SIP"

            # Default to PJSIP
            logger.warning("Could not detect channel driver, defaulting to PJSIP")
            return "PJSIP"

        except Exception as e:
            logger.error(f"Error detecting channel driver: {e}, defaulting to PJSIP")
            return "PJSIP"

    async def originate_call(
        self,
        destination: str,
        caller_id: str = "AutoDialer",
        timeout: int = 30000,
        context: str = "from-internal",
        priority: int = 1
    ) -> dict:
        """
        Originate an outbound call via AMI.

        Args:
            destination: Phone number to call (with dial prefix, e.g., "91234567890")
            caller_id: Caller ID to display
            timeout: Call timeout in milliseconds (default 30000 = 30 seconds)
            context: Dialplan context (default "from-internal")
            priority: Dialplan priority (default 1)

        Returns:
            Dict with AMI response

        Example:
            result = await engine.originate_call(
                destination="91234567890",
                caller_id="1005"
            )
        """
        if not self.manager:
            raise RuntimeError("AMI not connected. Call connect_ami() first.")

        # Construct channel string based on driver
        channel = f"{self.channel_driver}/{self.sip_extension}"

        logger.info(
            f"Originating call: Channel={channel}, Destination={destination}, "
            f"CallerID={caller_id}, Timeout={timeout}ms"
        )

        try:
            response = await self.manager.send_action({
                'Action': 'Originate',
                'Channel': channel,
                'Context': context,
                'Exten': destination,
                'Priority': str(priority),
                'CallerID': f'"{caller_id}" <{self.sip_extension}>',
                'Timeout': str(timeout),
                'Async': 'true'  # Don't block waiting for call completion
            })

            if response.get('Response') == 'Success':
                logger.info(f"Call originated successfully to {destination}")
                return {
                    'success': True,
                    'message': response.get('Message', 'Call originated'),
                    'channel': channel,
                    'destination': destination
                }
            else:
                error_msg = response.get('Message', 'Unknown error')
                logger.error(f"Call origination failed: {error_msg}")
                return {
                    'success': False,
                    'message': error_msg,
                    'channel': channel,
                    'destination': destination
                }

        except Exception as e:
            logger.error(f"Error originating call to {destination}: {e}")
            return {
                'success': False,
                'message': str(e),
                'channel': channel,
                'destination': destination
            }

    async def process_campaigns(self):
        """Process active campaigns and initiate calls."""
        while self.running:
            try:
                # TODO: Check for active campaigns
                # TODO: Get contacts to dial
                # TODO: Initiate calls via AMI
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error processing campaigns: {e}")
                await asyncio.sleep(5)

    async def start(self):
        """Start the dialer engine."""
        self.running = True
        logger.info("Starting Dialer Engine...")

        try:
            await self.connect_ami()
            await self.process_campaigns()
        except Exception as e:
            logger.error(f"Dialer engine error: {e}")
            raise

    async def disconnect_ami(self):
        """Disconnect from AMI."""
        if self.manager:
            try:
                logger.info("Disconnecting from AMI...")
                await self.manager.close()
                self.manager = None
                logger.info("AMI disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting from AMI: {e}")

    async def stop(self):
        """Stop the dialer engine."""
        logger.info("Stopping Dialer Engine...")
        self.running = False
        await self.disconnect_ami()


async def main():
    """Main entry point."""
    engine = DialerEngine()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(engine.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await engine.start()
    except KeyboardInterrupt:
        await engine.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
