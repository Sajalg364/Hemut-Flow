import redis.asyncio as redis
from app.config import settings

# Global Redis connection pool
redis_pool: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Initialize the Redis connection pool."""
    global redis_pool
    redis_pool = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    # Test connection
    await redis_pool.ping()
    return redis_pool


async def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    if redis_pool is None:
        return await init_redis()
    return redis_pool


async def close_redis():
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None
