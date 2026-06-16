from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.channel import Channel
from app.models.membership import Membership
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageResponse, DMConversation, DMUserInfo
from app.services.presence_service import get_unread_count, get_user_status
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/dm", tags=["direct-messages"])


@router.post("/{target_user_id}", response_model=dict)
async def create_or_get_dm(
    target_user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get or create a DM channel between current user and target user."""
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot DM yourself")

    # Check target user exists
    target = await db.execute(select(User).where(User.id == target_user_id))
    target_user = target.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find existing DM channel between these two users
    existing_dm = await db.execute(
        select(Channel)
        .where(Channel.is_dm == True)
        .where(
            Channel.id.in_(
                select(Membership.channel_id)
                .where(Membership.user_id == current_user.id)
                .intersect(
                    select(Membership.channel_id)
                    .where(Membership.user_id == target_user_id)
                )
            )
        )
    )
    dm_channel = existing_dm.scalar_one_or_none()

    if dm_channel:
        return {
            "channel_id": str(dm_channel.id),
            "is_new": False,
        }

    # Create new DM channel
    dm_name = f"dm-{min(str(current_user.id), str(target_user_id))}-{max(str(current_user.id), str(target_user_id))}"
    dm_channel = Channel(
        name=dm_name,
        is_dm=True,
        created_by=current_user.id,
    )
    db.add(dm_channel)
    await db.flush()

    # Add both users as members
    db.add(Membership(user_id=current_user.id, channel_id=dm_channel.id))
    db.add(Membership(user_id=target_user_id, channel_id=dm_channel.id))
    await db.flush()

    return {
        "channel_id": str(dm_channel.id),
        "is_new": True,
    }


@router.get("/conversations", response_model=list[DMConversation])
async def list_dm_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all DM conversations for the current user."""
    # Get all DM channels user is in
    dm_channels = await db.execute(
        select(Channel)
        .join(Membership, Channel.id == Membership.channel_id)
        .where(
            Membership.user_id == current_user.id,
            Channel.is_dm == True,
        )
    )
    channels = dm_channels.scalars().all()

    conversations = []
    for channel in channels:
        # Get the other user in the DM
        other_member = await db.execute(
            select(User)
            .join(Membership, User.id == Membership.user_id)
            .where(
                Membership.channel_id == channel.id,
                Membership.user_id != current_user.id,
            )
        )
        other_user = other_member.scalar_one_or_none()
        if not other_user:
            continue

        # Get last message
        last_msg = await db.execute(
            select(Message)
            .where(Message.channel_id == channel.id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_message = last_msg.scalar_one_or_none()

        unread = await get_unread_count(current_user.id, channel.id)
        user_status = await get_user_status(other_user.id)

        last_msg_response = None
        if last_message:
            last_msg_response = MessageResponse(
                id=last_message.id,
                channel_id=last_message.channel_id,
                sender_id=last_message.sender_id,
                content=last_message.content,
                message_type=last_message.message_type,
                metadata_json=last_message.metadata_json,
                created_at=last_message.created_at,
            )

        conversations.append(
            DMConversation(
                channel_id=channel.id,
                other_user=DMUserInfo(
                    id=other_user.id,
                    username=other_user.username,
                    display_name=other_user.display_name,
                    avatar_url=other_user.avatar_url,
                    status=user_status,
                ),
                last_message=last_msg_response,
                unread_count=unread,
            )
        )

    return conversations
