import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.message import Message
from app.models.user import User
from app.redis_client import get_redis


async def create_message(
    db: AsyncSession,
    channel_id: str,
    sender_id: str,
    content: str,
    message_type: str = "text",
    metadata_json: dict | None = None,
) -> Message:
    """Create a new message and publish to Redis for real-time delivery."""
    message = Message(
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        metadata_json=metadata_json,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Get sender info for the broadcast
    sender = await db.execute(select(User).where(User.id == sender_id))
    sender_user = sender.scalar_one_or_none()

    # Publish to Redis for real-time fan-out
    redis = await get_redis()
    message_data = {
        "type": "new_message",
        "data": {
            "id": str(message.id),
            "channel_id": str(message.channel_id),
            "sender_id": str(message.sender_id),
            "sender_username": sender_user.username if sender_user else "unknown",
            "sender_display_name": sender_user.display_name if sender_user else None,
            "sender_avatar_url": sender_user.avatar_url if sender_user else None,
            "content": message.content,
            "message_type": message.message_type,
            "metadata_json": message.metadata_json,
            "created_at": message.created_at.isoformat(),
            "is_edited": message.is_edited,
            "is_deleted": message.is_deleted,
        },
    }
    await redis.publish(f"channel:{channel_id}", json.dumps(message_data))

    # Increment unread counters for channel members (except sender)
    from app.models.membership import Membership
    members_result = await db.execute(
        select(Membership.user_id).where(
            Membership.channel_id == channel_id,
            Membership.user_id != sender_id,
        )
    )
    for (user_id,) in members_result:
        await redis.incr(f"unread:{user_id}:{channel_id}")

    return message


async def get_channel_messages(
    db: AsyncSession,
    channel_id: str,
    limit: int = 50,
    before: datetime | None = None,
) -> tuple[list[dict], bool]:
    """Get paginated messages for a channel with sender info."""
    query = (
        select(
            Message,
            User.username.label("sender_username"),
            User.display_name.label("sender_display_name"),
            User.avatar_url.label("sender_avatar_url"),
        )
        .join(User, Message.sender_id == User.id)
        .where(Message.channel_id == channel_id)
    )

    if before:
        query = query.where(Message.created_at < before)

    query = query.order_by(desc(Message.created_at)).limit(limit + 1)

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > limit
    messages = []
    for row in rows[:limit]:
        msg = row[0]
        messages.append({
            "id": str(msg.id),
            "channel_id": str(msg.channel_id),
            "sender_id": str(msg.sender_id),
            "sender_username": row.sender_username,
            "sender_display_name": row.sender_display_name,
            "sender_avatar_url": row.sender_avatar_url,
            "content": msg.content,
            "message_type": msg.message_type,
            "metadata_json": msg.metadata_json,
            "created_at": msg.created_at.isoformat(),
            "is_edited": msg.is_edited,
            "is_deleted": msg.is_deleted,
        })

    # Return in chronological order (oldest first)
    messages.reverse()
    return messages, has_more


async def edit_message(
    db: AsyncSession,
    message: Message,
    new_content: str,
) -> Message:
    """Edit a message and broadcast the update."""
    message.content = new_content
    message.is_edited = True
    await db.commit()
    await db.refresh(message)

    # Broadcast update
    redis = await get_redis()
    message_data = {
        "type": "message_updated",
        "data": {
            "id": str(message.id),
            "channel_id": str(message.channel_id),
            "content": message.content,
            "is_edited": message.is_edited,
        },
    }
    await redis.publish(f"channel:{message.channel_id}", json.dumps(message_data))
    return message


async def delete_message(
    db: AsyncSession,
    message: Message,
) -> Message:
    """Soft delete a message and broadcast the deletion."""
    message.is_deleted = True
    message.content = "This message was deleted"
    await db.commit()
    await db.refresh(message)

    # Broadcast deletion
    redis = await get_redis()
    message_data = {
        "type": "message_deleted",
        "data": {
            "id": str(message.id),
            "channel_id": str(message.channel_id),
            "is_deleted": True,
            "content": message.content,
        },
    }
    await redis.publish(f"channel:{message.channel_id}", json.dumps(message_data))
    return message
