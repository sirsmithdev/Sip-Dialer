"""
WebSocket endpoint for real-time updates.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.api.websocket_manager import manager
from app.core.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str) -> Optional[str]:
    """Verify JWT token and extract user ID."""
    try:
        payload = decode_token(token)
        if payload is None:
            return None
        user_id = payload.get("sub")
        return user_id
    except JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
):
    """
    WebSocket endpoint for real-time updates.

    Connect with: ws://host/api/v1/ws?token=<jwt_token>

    Message types received:
    - dashboard.stats: Dashboard statistics updates
    - campaign.progress: Campaign progress updates
    - sip.status: SIP connection status changes
    - call.update: Individual call status updates (future)
    """
    # Authenticate user
    user_id = await get_user_from_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Connect
    await manager.connect(websocket, user_id)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong, subscriptions, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0  # Heartbeat timeout
                )

                # Handle client messages
                message_type = data.get("type")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe":
                    # Future: Handle channel subscriptions
                    channel = data.get("channel")
                    logger.debug(f"User {user_id} subscribed to {channel}")
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel
                    })

                elif message_type == "unsubscribe":
                    # Future: Handle channel unsubscriptions
                    channel = data.get("channel")
                    logger.debug(f"User {user_id} unsubscribed from {channel}")
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": channel
                    })

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        manager.disconnect(websocket, user_id)
