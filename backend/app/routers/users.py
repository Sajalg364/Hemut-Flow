from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse, UserPresence
from app.services.presence_service import get_online_users, get_user_status
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users (for DM picker)."""
    result = await db.execute(
        select(User).where(User.id != current_user.id).order_by(User.username)
    )
    users = result.scalars().all()

    user_list = []
    for user in users:
        status = await get_user_status(user.id)
        user_list.append(
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                status=status,
                created_at=user.created_at,
            )
        )
    return user_list


@router.get("/online", response_model=list[str])
async def list_online_users(
    current_user: User = Depends(get_current_user),
):
    """Get list of online user IDs."""
    return await get_online_users()
