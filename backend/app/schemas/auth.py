from pydantic import BaseModel, Field
from datetime import datetime


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = Field(None, max_length=100)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    status: str = "offline"
    created_at: datetime

    class Config:
        from_attributes = True


class UserPresence(BaseModel):
    user_id: str
    username: str
    status: str  # online, away, offline
    display_name: str | None = None
