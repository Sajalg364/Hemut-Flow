import json
import logging
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.websocket.manager import manager
from app.services.presence_service import set_user_online, set_user_offline, refresh_presence
from app.models.user import User

logger = logging.getLogger(__name__)


async def handle_ws_connection(websocket: WebSocket, user: User, db: AsyncSession):
    """Handle the full lifecycle of a WebSocket connection."""
    user_id = str(user.id)

    await manager.connect(websocket, user_id)
    await set_user_online(user.id, user.username)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_ws_message(user_id, user.username, message, db)
            except json.JSONDecodeError:
                await manager.send_to_user(
                    user_id, {"type": "error", "data": {"message": "Invalid JSON"}}
                )
    except WebSocketDisconnect:
        logger.info(f"User {user_id} WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await manager.disconnect(user_id)
        await set_user_offline(user.id, user.username)


async def handle_ws_message(
    user_id: str, username: str, message: dict, db: AsyncSession
):
    """Route incoming WebSocket messages to appropriate handlers."""
    msg_type = message.get("type")

    if msg_type == "subscribe_channel":
        channel_id = message.get("channel_id")
        if channel_id:
            await manager.subscribe_to_channel(user_id, channel_id)
            logger.info(f"User {user_id} subscribed to channel {channel_id}")

    elif msg_type == "unsubscribe_channel":
        channel_id = message.get("channel_id")
        if channel_id:
            await manager.unsubscribe_from_channel(user_id, channel_id)

    elif msg_type == "heartbeat":
        from uuid import UUID
        await refresh_presence(UUID(user_id))
        await manager.send_to_user(user_id, {"type": "heartbeat_ack"})

    elif msg_type == "typing":
        channel_id = message.get("channel_id")
        if channel_id:
            await manager.broadcast_to_channel(
                channel_id,
                {
                    "type": "typing_indicator",
                    "data": {
                        "user_id": user_id,
                        "username": username,
                        "channel_id": channel_id,
                    },
                },
                exclude_user=user_id,
            )

    else:
        await manager.send_to_user(
            user_id,
            {"type": "error", "data": {"message": f"Unknown message type: {msg_type}"}},
        )
