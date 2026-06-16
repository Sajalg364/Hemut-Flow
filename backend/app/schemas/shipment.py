from pydantic import BaseModel
from datetime import datetime


class ShipmentResponse(BaseModel):
    id: str
    origin: str
    destination: str
    status: str
    carrier: str | None = None
    eta: datetime | None = None
    weight_kg: float | None = None
    items_description: str | None = None
    tracking_url: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShipmentListResponse(BaseModel):
    shipments: list[ShipmentResponse]


class SummarizeRequest(BaseModel):
    channel_id: str
    hours: int = 24
