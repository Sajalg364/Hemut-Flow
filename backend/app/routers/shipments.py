from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.shipment import ShipmentResponse, ShipmentListResponse
from app.services.shipment_service import get_shipment_by_id, get_all_shipments
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/shipments", tags=["shipments"])


@router.get("/", response_model=ShipmentListResponse)
async def list_shipments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all shipments."""
    shipments = await get_all_shipments(db)
    return ShipmentListResponse(
        shipments=[ShipmentResponse.model_validate(s) for s in shipments]
    )


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lookup a shipment by ID."""
    shipment = await get_shipment_by_id(db, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")
    return ShipmentResponse.model_validate(shipment)
