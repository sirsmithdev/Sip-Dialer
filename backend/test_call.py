"""
Test Call Script for Grandstream UCM PBX.

This script initiates a test call using the dialer engine.
"""
import asyncio
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import the dialer engine
from dialer.main import DialerEngine


async def make_test_call(
    destination: str,
    ami_host: str = "192.168.150.10",
    ami_port: int = 7777,
    ami_username: str = "autodialerami",
    ami_password: str = "",
    extension: str = "1005",
    channel_driver: str = "PJSIP"
):
    """
    Make a test call via AMI.

    Args:
        destination: Phone number to call (e.g., "91234567890" for 9+number)
        ami_host: Grandstream UCM IP address
        ami_port: AMI port (7777 for Grandstream)
        ami_username: AMI username (must be 8+ chars)
        ami_password: AMI password
        extension: SIP extension to use for outbound
        channel_driver: PJSIP or SIP
    """
    # Set environment variables for the engine
    os.environ["AMI_HOST"] = ami_host
    os.environ["AMI_PORT"] = str(ami_port)
    os.environ["AMI_USERNAME"] = ami_username
    os.environ["AMI_PASSWORD"] = ami_password
    os.environ["CHANNEL_DRIVER"] = channel_driver
    os.environ["SIP_EXTENSION"] = extension

    engine = DialerEngine()

    try:
        # Connect to AMI
        logger.info(f"Connecting to AMI at {ami_host}:{ami_port}...")
        await engine.connect_ami()
        logger.info("✓ AMI connection successful!")

        # Make the test call
        logger.info(f"Initiating test call to {destination}...")
        result = await engine.originate_call(
            destination=destination,
            caller_id=extension,
            timeout=30000,
            context="from-internal",
            priority=1
        )

        if result['success']:
            logger.info(f"✓ Call initiated successfully!")
            logger.info(f"  Channel: {result['channel']}")
            logger.info(f"  Destination: {result['destination']}")
            logger.info(f"  Message: {result['message']}")

            # Wait a bit for call to complete
            logger.info("Waiting 30 seconds for call to complete...")
            await asyncio.sleep(30)
        else:
            logger.error(f"✗ Call failed: {result['message']}")

    except asyncio.TimeoutError:
        logger.error("✗ AMI connection timeout - check network connectivity")
    except ConnectionRefusedError:
        logger.error(f"✗ Connection refused - verify AMI is enabled at {ami_host}:{ami_port}")
    except Exception as e:
        logger.error(f"✗ Error: {e}")
    finally:
        await engine.disconnect_ami()


def print_usage():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    SIP Dialer Test Call                          ║
╚══════════════════════════════════════════════════════════════════╝

Usage: python test_call.py <destination> [options]

Arguments:
  destination      Phone number to call (with dial prefix if needed)
                   Example: 91234567890 (9 + phone number)

Options:
  --ami-host       AMI host IP (default: 192.168.150.10)
  --ami-port       AMI port (default: 7777 for Grandstream)
  --ami-user       AMI username (default: autodialerami)
  --ami-pass       AMI password (required)
  --extension      SIP extension (default: 1005)
  --driver         Channel driver: PJSIP or SIP (default: PJSIP)

Examples:
  # Call a local extension (e.g., extension 1001)
  python test_call.py 1001 --ami-pass your_password

  # Call an external number through trunk (9 + number)
  python test_call.py 91234567890 --ami-pass your_password

  # With custom settings
  python test_call.py 91234567890 \\
    --ami-host 192.168.150.10 \\
    --ami-port 7777 \\
    --ami-user autodialerami \\
    --ami-pass your_ami_password \\
    --extension 1005 \\
    --driver PJSIP
""")


def parse_args():
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help']:
        print_usage()
        sys.exit(0)

    # Defaults for Grandstream UCM
    config = {
        'destination': args[0],
        'ami_host': '192.168.150.10',
        'ami_port': 7777,
        'ami_username': 'autodialerami',
        'ami_password': '',
        'extension': '1005',
        'channel_driver': 'PJSIP'
    }

    i = 1
    while i < len(args):
        if args[i] == '--ami-host' and i + 1 < len(args):
            config['ami_host'] = args[i + 1]
            i += 2
        elif args[i] == '--ami-port' and i + 1 < len(args):
            config['ami_port'] = int(args[i + 1])
            i += 2
        elif args[i] == '--ami-user' and i + 1 < len(args):
            config['ami_username'] = args[i + 1]
            i += 2
        elif args[i] == '--ami-pass' and i + 1 < len(args):
            config['ami_password'] = args[i + 1]
            i += 2
        elif args[i] == '--extension' and i + 1 < len(args):
            config['extension'] = args[i + 1]
            i += 2
        elif args[i] == '--driver' and i + 1 < len(args):
            config['channel_driver'] = args[i + 1]
            i += 2
        else:
            i += 1

    return config


if __name__ == "__main__":
    config = parse_args()

    if not config['ami_password']:
        logger.error("AMI password is required! Use --ami-pass <password>")
        print_usage()
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    Test Call Configuration                        ║
╠══════════════════════════════════════════════════════════════════╣
║  AMI Host:      {config['ami_host']:48}║
║  AMI Port:      {config['ami_port']:<48}║
║  AMI Username:  {config['ami_username']:48}║
║  Extension:     {config['extension']:48}║
║  Driver:        {config['channel_driver']:48}║
║  Destination:   {config['destination']:48}║
╚══════════════════════════════════════════════════════════════════╝
""")

    asyncio.run(make_test_call(**config))
