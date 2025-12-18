"""
FastAGI Server for handling IVR interactions.

This server receives AGI requests from Asterisk/UCM6302 and processes
IVR flows for automated calls.
"""
import asyncio
import logging
import os
import signal
import sys

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AGISession:
    """Handles a single AGI session."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.env = {}

    async def read_env(self):
        """Read AGI environment variables."""
        while True:
            line = await self.reader.readline()
            if not line:
                break
            line = line.decode().strip()
            if line == "":
                break
            if ": " in line:
                key, value = line.split(": ", 1)
                self.env[key] = value
        logger.debug(f"AGI Environment: {self.env}")

    async def send_command(self, command: str) -> str:
        """Send AGI command and get response."""
        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()
        response = await self.reader.readline()
        return response.decode().strip()

    async def answer(self):
        """Answer the call."""
        return await self.send_command("ANSWER")

    async def hangup(self):
        """Hangup the call."""
        return await self.send_command("HANGUP")

    async def stream_file(self, filename: str, escape_digits: str = ""):
        """Play an audio file."""
        return await self.send_command(f'STREAM FILE "{filename}" "{escape_digits}"')

    async def get_data(self, filename: str, timeout: int = 5000, max_digits: int = 10):
        """Play file and collect DTMF digits."""
        return await self.send_command(
            f'GET DATA "{filename}" {timeout} {max_digits}'
        )

    async def say_digits(self, digits: str, escape_digits: str = ""):
        """Say digits."""
        return await self.send_command(f'SAY DIGITS {digits} "{escape_digits}"')

    async def set_variable(self, name: str, value: str):
        """Set a channel variable."""
        return await self.send_command(f'SET VARIABLE {name} "{value}"')

    async def run(self):
        """Run the AGI session."""
        try:
            await self.read_env()

            # Answer the call
            await self.answer()

            # Get the IVR flow ID from channel variables or default
            ivr_flow_id = self.env.get("agi_arg_1", "default")
            logger.info(f"Processing IVR flow: {ivr_flow_id}")

            # TODO: Load IVR flow from database and process nodes
            # For now, play a simple greeting and hangup

            # Play greeting (file should exist in Asterisk sounds directory)
            await self.stream_file("hello-world")

            # Hangup
            await self.hangup()

        except Exception as e:
            logger.error(f"AGI session error: {e}")
        finally:
            self.writer.close()
            await self.writer.wait_closed()


class AGIServer:
    """FastAGI Server."""

    def __init__(self, host: str = "0.0.0.0", port: int = 4573):
        self.host = host
        self.port = port
        self.server = None
        self.running = False

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle incoming AGI connection."""
        peer = writer.get_extra_info("peername")
        logger.info(f"New AGI connection from {peer}")

        session = AGISession(reader, writer)
        await session.run()

        logger.info(f"AGI connection from {peer} closed")

    async def start(self):
        """Start the AGI server."""
        self.running = True
        self.server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )

        addr = self.server.sockets[0].getsockname()
        logger.info(f"FastAGI Server listening on {addr[0]}:{addr[1]}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the AGI server."""
        logger.info("Stopping AGI Server...")
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()


async def main():
    """Main entry point."""
    host = os.getenv("AGI_HOST", "0.0.0.0")
    port = int(os.getenv("AGI_PORT", "4573"))

    server = AGIServer(host, port)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(server.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
