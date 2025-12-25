"""
Redis connection management.
"""
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
            # DigitalOcean Managed Redis uses self-signed certs
            # For rediss:// URLs, redis-py handles SSL automatically
            # We just need to disable cert verification
            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                ssl_cert_reqs=None,  # Disable certificate verification
                socket_keepalive=True,
                health_check_interval=30,  # Ping every 30s to prevent idle timeout
            )
        else:
            # Local/non-SSL Redis
            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                health_check_interval=30,
            )
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
