"""
Redis connection management.
"""
import ssl
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings

# Global Redis client
_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        # Check if using SSL (rediss:// URLs used by DigitalOcean Managed Redis)
        redis_url = settings.redis_url
        if redis_url.startswith("rediss://"):
            # Create SSL context for DigitalOcean Managed Redis
            # DO Managed Redis uses self-signed certs, so we need to skip verification
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                ssl=ssl_context,
            )
        else:
            # Local/non-SSL Redis
            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
