import json
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.message import Message
from app.models.user import User
from app.config import settings
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a logistics operations assistant for Hemut, a logistics collaboration platform.
Your task is to summarize team chat messages from a logistics channel.

Focus on:
- Shipment status updates (delays, deliveries, ETAs)
- Route changes or diversions
- Warehouse operations and inventory issues
- Action items and pending decisions
- Escalations or urgent matters
- Key numbers: tracking IDs, PO numbers, quantities

Format your summary as:
📋 **Channel Summary** (last {hours} hours)

**🚨 Urgent/Escalations:**
- List any urgent items or escalations

**📦 Shipment Updates:**
- List shipment-related updates

**📝 Action Items:**
- List any pending actions or decisions

**💬 Key Discussions:**
- Summarize other important discussions

Be concise and actionable. If there are no messages, say so clearly.
"""


async def get_channel_summary(
    db: AsyncSession,
    channel_id: str,
    hours: int = 24,
) -> str:
    """Generate an AI summary of recent channel messages using Google Gemini."""

    # Check Redis cache first
    redis = await get_redis()
    cache_key = f"summary:{channel_id}:{hours}"
    cached = await redis.get(cache_key)
    if cached:
        return cached

    # Fetch messages from the last N hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Message, User.username, User.display_name)
        .join(User, Message.sender_id == User.id)
        .where(
            Message.channel_id == channel_id,
            Message.created_at >= cutoff,
        )
        .order_by(Message.created_at)
        .limit(200)  # Cap to avoid token limits
    )
    rows = result.all()

    if not rows:
        return f"📋 **Channel Summary** (last {hours} hours)\n\nNo messages found in this time period."

    # Format messages for the AI
    formatted_messages = []
    for row in rows:
        msg = row[0]
        username = row.username or "unknown"
        display_name = row.display_name or username
        timestamp = msg.created_at.strftime("%H:%M")
        formatted_messages.append(
            f"[{timestamp}] {display_name} (@{username}): {msg.content}"
        )

    messages_text = "\n".join(formatted_messages)
    prompt = SYSTEM_PROMPT.format(hours=hours) + f"\n\nMessages:\n{messages_text}"

    # Call Google Gemini
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        summary = response.text

        # Cache for 5 minutes
        await redis.setex(cache_key, 300, summary)

        return summary

    except Exception as e:
        logger.error(f"AI summarization failed: {e}")
        # Fallback: basic message count summary
        return (
            f"📋 **Channel Summary** (last {hours} hours)\n\n"
            f"⚠️ AI summarization is currently unavailable.\n\n"
            f"**Stats:** {len(rows)} messages from {len(set(r.username for r in rows))} participants.\n\n"
            f"**Latest message:** {rows[-1][0].content[:200]}..."
        )
