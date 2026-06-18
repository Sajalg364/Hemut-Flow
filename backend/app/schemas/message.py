from pydantic import BaseModel, Field
from datetime import datetime


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = "text"
    metadata_json: dict | None = None


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: str
    channel_id: str
    sender_id: str
    sender_username: str | None = None
    sender_display_name: str | None = None
    sender_avatar_url: str | None = None
    content: str
    message_type: str = "text"
    metadata_json: dict | None = None
    created_at: datetime
    is_edited: bool = False
    is_deleted: bool = False

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool = False
    next_cursor: str | None = None


class DMConversation(BaseModel):
    channel_id: str
    other_user: "DMUserInfo"
    last_message: MessageResponse | None = None
    unread_count: int = 0


class DMUserInfo(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    status: str = "offline"

    class Config:
        from_attributes = True
