from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.shipment import SummarizeRequest
from app.services.ai_service import get_channel_summary
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/summarize")
async def summarize_channel(
    data: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summarize recent messages in a channel using AI."""
    summary = await get_channel_summary(db, data.channel_id, data.hours)
    return {"summary": summary, "channel_id": data.channel_id, "hours": data.hours}
