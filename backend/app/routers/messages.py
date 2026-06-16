from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.membership import Membership
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse
from app.services.message_service import create_message, get_channel_messages
from app.services.presence_service import clear_unread
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/channels", tags=["messages"])


@router.post("/{channel_id}/messages", response_model=MessageResponse)
async def post_message(
    channel_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post a message to a channel."""
    # Verify user is a member
    membership = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.channel_id == channel_id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    message = await create_message(
        db=db,
        channel_id=channel_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        metadata_json=data.metadata_json,
    )

    return MessageResponse(
        id=message.id,
        channel_id=message.channel_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        sender_display_name=current_user.display_name,
        sender_avatar_url=current_user.avatar_url,
        content=message.content,
        message_type=message.message_type,
        metadata_json=message.metadata_json,
        created_at=message.created_at,
    )


@router.get("/{channel_id}/messages", response_model=MessageListResponse)
async def get_messages(
    channel_id: str,
    limit: int = Query(default=50, le=100, ge=1),
    before: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated messages for a channel."""
    # Verify user is a member
    membership = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.channel_id == channel_id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    before_dt = None
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'before' timestamp")

    messages, has_more = await get_channel_messages(
        db=db,
        channel_id=channel_id,
        limit=limit,
        before=before_dt,
    )

    # Clear unread count since user is viewing
    await clear_unread(current_user.id, channel_id)

    next_cursor = None
    if has_more and messages:
        next_cursor = messages[0]["created_at"]

    return MessageListResponse(
        messages=[MessageResponse(**m) for m in messages],
        has_more=has_more,
        next_cursor=next_cursor,
    )
