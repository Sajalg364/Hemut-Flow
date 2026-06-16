from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.channel import Channel
from app.models.membership import Membership
from app.models.user import User
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.dependencies import get_current_user
from app.services.presence_service import get_unread_count

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new channel and auto-join the creator."""
    # Check if channel name already exists
    existing = await db.execute(
        select(Channel).where(Channel.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel name already exists",
        )

    # Create channel
    channel = Channel(
        name=data.name,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(channel)
    await db.flush()

    # Auto-join creator
    membership = Membership(user_id=current_user.id, channel_id=channel.id)
    db.add(membership)
    await db.flush()
    await db.refresh(channel)

    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        is_dm=channel.is_dm,
        created_by=channel.created_by,
        created_at=channel.created_at,
        member_count=1,
        unread_count=0,
    )


@router.get("/", response_model=list[ChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all channels the current user has joined."""
    result = await db.execute(
        select(Channel, func.count(Membership.id).label("member_count"))
        .join(Membership, Channel.id == Membership.channel_id)
        .where(
            Channel.id.in_(
                select(Membership.channel_id).where(
                    Membership.user_id == current_user.id
                )
            ),
            Channel.is_dm == False,
        )
        .group_by(Channel.id)
        .order_by(Channel.name)
    )
    rows = result.all()

    channels = []
    for row in rows:
        channel = row[0]
        member_count = row.member_count
        unread = await get_unread_count(current_user.id, channel.id)
        channels.append(
            ChannelResponse(
                id=channel.id,
                name=channel.name,
                description=channel.description,
                is_dm=channel.is_dm,
                created_by=channel.created_by,
                created_at=channel.created_at,
                member_count=member_count,
                unread_count=unread,
            )
        )

    return channels


@router.get("/available", response_model=list[ChannelResponse])
async def list_available_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all channels (including ones user hasn't joined)."""
    result = await db.execute(
        select(Channel, func.count(Membership.id).label("member_count"))
        .outerjoin(Membership, Channel.id == Membership.channel_id)
        .where(Channel.is_dm == False)
        .group_by(Channel.id)
        .order_by(Channel.name)
    )
    rows = result.all()

    channels = []
    for row in rows:
        channel = row[0]
        member_count = row.member_count
        channels.append(
            ChannelResponse(
                id=channel.id,
                name=channel.name,
                description=channel.description,
                is_dm=channel.is_dm,
                created_by=channel.created_by,
                created_at=channel.created_at,
                member_count=member_count,
            )
        )
    return channels


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get channel details."""
    result = await db.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Count members
    count_result = await db.execute(
        select(func.count(Membership.id)).where(Membership.channel_id == channel_id)
    )
    member_count = count_result.scalar() or 0

    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        is_dm=channel.is_dm,
        created_by=channel.created_by,
        created_at=channel.created_at,
        member_count=member_count,
    )


@router.post("/{channel_id}/join", status_code=status.HTTP_200_OK)
async def join_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join a channel."""
    # Check channel exists
    channel = await db.execute(select(Channel).where(Channel.id == channel_id))
    if not channel.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Channel not found")

    # Check if already a member
    existing = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.channel_id == channel_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already a member"}

    membership = Membership(user_id=current_user.id, channel_id=channel_id)
    db.add(membership)
    await db.flush()
    return {"message": "Joined channel successfully"}


@router.post("/{channel_id}/leave", status_code=status.HTTP_200_OK)
async def leave_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave a channel."""
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == current_user.id,
            Membership.channel_id == channel_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of this channel")

    await db.delete(membership)
    await db.flush()
    return {"message": "Left channel successfully"}
