from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.membership import Membership
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse, MessageUpdate
from app.services.message_service import create_message, get_channel_messages, edit_message, delete_message
from app.services.presence_service import clear_unread
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/channels", tags=["messages"])


@router.post("/{channel_id}/messages", response_model=MessageResponse)
async def post_message(
    channel_id: str,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
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

    # Only analyze regular text messages for escalations
    if data.message_type == "text":
        background_tasks.add_task(
            check_and_escalate_message,
            channel_id=channel_id,
            sender_id=current_user.id,
            content=data.content,
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


@router.put("/{channel_id}/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    channel_id: str,
    message_id: str,
    data: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit an existing message."""
    from app.models.message import Message
    
    # Fetch the message
    result = await db.execute(select(Message).where(Message.id == message_id, Message.channel_id == channel_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Verify ownership
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")
        
    if message.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot edit a deleted message")

    updated_message = await edit_message(db, message, data.content)
    
    return MessageResponse(
        id=updated_message.id,
        channel_id=updated_message.channel_id,
        sender_id=updated_message.sender_id,
        sender_username=current_user.username,
        sender_display_name=current_user.display_name,
        sender_avatar_url=current_user.avatar_url,
        content=updated_message.content,
        message_type=updated_message.message_type,
        metadata_json=updated_message.metadata_json,
        created_at=updated_message.created_at,
        is_edited=updated_message.is_edited,
        is_deleted=updated_message.is_deleted,
    )


@router.delete("/{channel_id}/messages/{message_id}")
async def delete_message_endpoint(
    channel_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a message."""
    from app.models.message import Message
    
    # Fetch the message
    result = await db.execute(select(Message).where(Message.id == message_id, Message.channel_id == channel_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Verify ownership
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")

    if not message.is_deleted:
        await delete_message(db, message)
    
    return {"status": "success", "message": "Message deleted"}


async def check_and_escalate_message(channel_id: str, sender_id: str, content: str):
    """Background task to analyze a message for critical escalations and alert the channel."""
    from app.services.ai_service import analyze_for_escalation
    from app.services.message_service import create_message
    from app.database import async_session_factory
    import logging
    
    escalation = await analyze_for_escalation(content)
    if escalation:
        logging.info(f"Escalation detected in channel {channel_id}: {escalation['reason']}")
        
        async with async_session_factory() as db:
            from app.models.channel import Channel
            from app.models.user import User
            from app.models.membership import Membership
            from sqlalchemy import select
            
            # Find or create a global 'alerts' channel
            result = await db.execute(select(Channel).where(Channel.name == "alerts", Channel.is_dm == False))
            alerts_channel = result.scalar_one_or_none()
            if not alerts_channel:
                alerts_channel = Channel(
                    name="alerts", 
                    description="System-wide critical logistics escalations and AI alerts.", 
                    created_by=sender_id,
                    is_dm=False
                )
                db.add(alerts_channel)
                await db.commit()
                await db.refresh(alerts_channel)
                
            # Ensure ALL users are members of the alerts channel
            users_res = await db.execute(select(User))
            for u in users_res.scalars().all():
                mem_res = await db.execute(select(Membership).where(
                    Membership.user_id == u.id, 
                    Membership.channel_id == alerts_channel.id
                ))
                if not mem_res.scalar_one_or_none():
                    db.add(Membership(user_id=u.id, channel_id=alerts_channel.id))
            await db.commit()

            alert_content = f"⚠️ **AI ALERT:** Critical escalation detected! Reason: {escalation['reason']}"
            if escalation.get('shipment_id'):
                alert_content += f"\n📦 Shipment: {escalation['shipment_id']}"
                
            try:
                # Post the alert in the original channel
                await create_message(
                    db=db,
                    channel_id=channel_id,
                    sender_id=sender_id, # Displayed as system message anyway
                    content=alert_content,
                    message_type="system",
                )
                
                # If the original channel was not the alerts channel, post it there too
                if channel_id != alerts_channel.id:
                    # Fetch original channel and sender info for context
                    orig_channel_res = await db.execute(select(Channel).where(Channel.id == channel_id))
                    orig_channel = orig_channel_res.scalar_one_or_none()
                    channel_name = f"#{orig_channel.name}" if orig_channel and not orig_channel.is_dm else "Direct Message"
                    
                    sender_res = await db.execute(select(User).where(User.id == sender_id))
                    sender = sender_res.scalar_one_or_none()
                    sender_name = f"@{sender.username}" if sender else "Unknown User"
                    
                    # Provide context on where it originated
                    global_alert_content = alert_content + f"\n*(Cross-posted from {channel_name} | Reported by {sender_name})*"
                    await create_message(
                        db=db,
                        channel_id=alerts_channel.id,
                        sender_id=sender_id,
                        content=global_alert_content,
                        message_type="system",
                    )
                
                await db.commit()
            except Exception as e:
                logging.error(f"Failed to post AI escalation alert: {e}")
                await db.rollback()
