import json
from app.redis_client import get_redis

# Presence TTL in seconds
PRESENCE_TTL = 60
AWAY_TTL = 120


async def set_user_online(user_id, username: str):
    """Mark a user as online."""
    redis = await get_redis()
    key = f"presence:{user_id}"
    await redis.setex(key, PRESENCE_TTL, "online")
    await redis.sadd("online_users", str(user_id))

    # Publish presence change
    await redis.publish(
        "presence",
        json.dumps({
            "type": "presence_update",
            "data": {
                "user_id": str(user_id),
                "username": username,
                "status": "online",
            },
        }),
    )


async def refresh_presence(user_id):
    """Refresh the presence TTL (called on heartbeat)."""
    redis = await get_redis()
    key = f"presence:{user_id}"
    current = await redis.get(key)
    if current:
        await redis.setex(key, PRESENCE_TTL, "online")
    await redis.sadd("online_users", str(user_id))


async def set_user_offline(user_id, username: str):
    """Mark a user as offline."""
    redis = await get_redis()
    await redis.delete(f"presence:{user_id}")
    await redis.srem("online_users", str(user_id))

    # Publish presence change
    await redis.publish(
        "presence",
        json.dumps({
            "type": "presence_update",
            "data": {
                "user_id": str(user_id),
                "username": username,
                "status": "offline",
            },
        }),
    )


async def get_user_status(user_id) -> str:
    """Get a user's current presence status."""
    redis = await get_redis()
    key = f"presence:{user_id}"
    status = await redis.get(key)
    if status:
        return status
    # Check if they're in the online set but expired (away)
    is_member = await redis.sismember("online_users", str(user_id))
    if is_member:
        return "away"
    return "offline"


async def get_online_users() -> list[str]:
    """Get list of online user IDs."""
    redis = await get_redis()
    return list(await redis.smembers("online_users"))


async def get_unread_count(user_id, channel_id) -> int:
    """Get unread message count for a user in a channel."""
    redis = await get_redis()
    count = await redis.get(f"unread:{user_id}:{channel_id}")
    return int(count) if count else 0


async def clear_unread(user_id, channel_id):
    """Clear unread count when user reads a channel."""
    redis = await get_redis()
    await redis.delete(f"unread:{user_id}:{channel_id}")
