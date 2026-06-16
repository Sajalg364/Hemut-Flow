from pydantic import BaseModel, Field
from datetime import datetime


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    description: str | None = None


class ChannelResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_dm: bool = False
    created_by: str | None = None
    created_at: datetime
    member_count: int | None = None
    unread_count: int | None = None

    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    channels: list[ChannelResponse]


class MembershipResponse(BaseModel):
    channel_id: str
    user_id: str
    joined_at: datetime

    class Config:
        from_attributes = True
