import json
import asyncio
import logging
from uuid import UUID
from fastapi import WebSocket
from app.redis_client import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket connection manager with Redis pub/sub for multi-worker fan-out.

    Each connected client is tracked by user_id. Channel subscriptions are
    managed per-connection and backed by Redis pub/sub for cross-worker broadcasting.
    """

    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}
        # user_id -> set of channel_ids
        self.user_channels: dict[str, set[str]] = {}
        # channel_id -> set of user_ids
        self.channel_users: dict[str, set[str]] = {}
        # Redis subscriber task
        self._subscriber_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start the Redis pub/sub listener."""
        self._running = True
        self._subscriber_task = asyncio.create_task(self._redis_subscriber())
        logger.info("WebSocket ConnectionManager started with Redis pub/sub")

    async def stop(self):
        """Stop the Redis pub/sub listener."""
        self._running = False
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket ConnectionManager stopped")

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_channels[user_id] = set()
        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, user_id: str):
        """Handle WebSocket disconnection."""
        self.active_connections.pop(user_id, None)
        # Clean up channel subscriptions
        channels = self.user_channels.pop(user_id, set())
        for channel_id in channels:
            if channel_id in self.channel_users:
                self.channel_users[channel_id].discard(user_id)
                if not self.channel_users[channel_id]:
                    del self.channel_users[channel_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def subscribe_to_channel(self, user_id: str, channel_id: str):
        """Subscribe a user to a channel's messages."""
        if user_id not in self.user_channels:
            self.user_channels[user_id] = set()
        self.user_channels[user_id].add(channel_id)

        if channel_id not in self.channel_users:
            self.channel_users[channel_id] = set()
        self.channel_users[channel_id].add(user_id)

    async def unsubscribe_from_channel(self, user_id: str, channel_id: str):
        """Unsubscribe a user from a channel."""
        if user_id in self.user_channels:
            self.user_channels[user_id].discard(channel_id)
        if channel_id in self.channel_users:
            self.channel_users[channel_id].discard(user_id)

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user."""
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
                await self.disconnect(user_id)

    async def broadcast_to_channel(self, channel_id: str, message: dict, exclude_user: str | None = None):
        """Broadcast a message to all users subscribed to a channel (local connections only)."""
        users = self.channel_users.get(channel_id, set())
        for user_id in users.copy():
            if user_id != exclude_user:
                await self.send_to_user(user_id, message)

    async def _redis_subscriber(self):
        """Listen to Redis pub/sub and fan out messages to local WebSocket connections."""
        try:
            redis = await get_redis()
            pubsub = redis.pubsub()
            # Subscribe to presence channel
            await pubsub.subscribe("presence")
            subscribed = set()

            while self._running:
                try:
                    # Subscribe to any new channels that have local users
                    current_channels = set(self.channel_users.keys())
                    new_channels = current_channels - subscribed
                    removed_channels = subscribed - current_channels

                    for channel_id in new_channels:
                        ch_name = f"channel:{channel_id}"
                        await pubsub.subscribe(ch_name)
                        subscribed.add(channel_id)

                    for channel_id in removed_channels:
                        ch_name = f"channel:{channel_id}"
                        await pubsub.unsubscribe(ch_name)
                        subscribed.discard(channel_id)

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message["type"] == "message":
                        data = json.loads(message["data"])
                        channel = message["channel"]

                        if channel == "presence":
                            # Broadcast presence to all connected users
                            for user_id in list(self.active_connections.keys()):
                                await self.send_to_user(user_id, data)
                        elif channel.startswith("channel:"):
                            ch_id = channel.replace("channel:", "")
                            await self.broadcast_to_channel(ch_id, data)

                    await asyncio.sleep(0.01)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Redis subscriber error: {e}")
                    await asyncio.sleep(1)

            await pubsub.unsubscribe()
            await pubsub.close()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis subscriber fatal error: {e}")


# Singleton instance
manager = ConnectionManager()
