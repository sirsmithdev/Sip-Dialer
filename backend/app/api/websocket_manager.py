"""
WebSocket connection manager with Redis pub/sub integration.
"""
import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket
from redis.asyncio import Redis

from app.db.redis import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages from Redis pub/sub.

    Supports multiple connections per user (multiple browser tabs).
    """

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}  # user_id -> [websockets]
        self._redis_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

        logger.info(f"WebSocket connected: user={user_id}, total_connections={self.total_connections}")

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            except ValueError:
                pass

        logger.info(f"WebSocket disconnected: user={user_id}, total_connections={self.total_connections}")

    @property
    def total_connections(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    async def send_personal(self, user_id: str, message: dict) -> None:
        """Send message to a specific user's connections."""
        if user_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    disconnected.append(ws)

            # Clean up disconnected sockets
            for ws in disconnected:
                self.disconnect(ws, user_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        disconnected = []

        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to user {user_id}: {e}")
                    disconnected.append((ws, user_id))

        # Clean up disconnected sockets
        for ws, user_id in disconnected:
            self.disconnect(ws, user_id)

    async def start_redis_subscriber(self) -> None:
        """Start the Redis pub/sub listener in background."""
        if self._running:
            return

        self._running = True
        self._redis_task = asyncio.create_task(self._redis_listener())
        logger.info("Started Redis pub/sub listener for WebSocket broadcasts")

    async def stop_redis_subscriber(self) -> None:
        """Stop the Redis pub/sub listener."""
        self._running = False
        if self._redis_task:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped Redis pub/sub listener")

    async def _redis_listener(self) -> None:
        """Listen for Redis pub/sub messages and broadcast to WebSocket clients."""
        while self._running:
            try:
                redis: Redis = await get_redis()
                pubsub = redis.pubsub()

                # Subscribe to all WebSocket channels
                await pubsub.psubscribe("ws:*")
                logger.info("Subscribed to Redis ws:* channels")

                async for message in pubsub.listen():
                    if not self._running:
                        break

                    if message["type"] == "pmessage":
                        channel = message["channel"]
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8")

                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")

                        try:
                            payload = json.loads(data)
                            await self._handle_redis_message(channel, payload)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from Redis channel {channel}: {data}")

                await pubsub.unsubscribe()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis subscriber error: {e}")
                if self._running:
                    await asyncio.sleep(5)  # Reconnect delay

    async def _handle_redis_message(self, channel: str, payload: dict) -> None:
        """Process a message from Redis and forward to appropriate clients."""
        # Extract channel type from pattern like "ws:dashboard", "ws:campaign:123", etc.
        parts = channel.split(":")

        if len(parts) < 2:
            return

        channel_type = parts[1]  # dashboard, campaign, sip_status, calls

        # Build WebSocket message
        ws_message = {
            "type": f"{channel_type}.update" if channel_type not in payload.get("type", "") else payload.get("type"),
            "data": payload.get("data", payload),
            "channel": channel
        }

        # For now, broadcast all messages to all clients
        # Future: implement channel subscriptions per client
        await self.broadcast(ws_message)

        logger.debug(f"Broadcast from {channel}: {ws_message['type']}")


# Global connection manager instance
manager = ConnectionManager()


async def publish_ws_event(channel: str, event_type: str, data: dict) -> None:
    """
    Publish an event to WebSocket clients via Redis.

    Args:
        channel: Redis channel (e.g., "ws:dashboard", "ws:campaign:123")
        event_type: Event type (e.g., "dashboard.stats", "campaign.progress")
        data: Event data payload
    """
    try:
        redis: Redis = await get_redis()
        message = json.dumps({
            "type": event_type,
            "data": data
        })
        await redis.publish(channel, message)
        logger.debug(f"Published to {channel}: {event_type}")
    except Exception as e:
        logger.error(f"Failed to publish WebSocket event: {e}")
