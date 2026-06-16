from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.shipment import Shipment


# Mock shipment data for the logistics context
MOCK_SHIPMENTS = [
    {
        "id": "SHIP-1001",
        "origin": "Mumbai Warehouse, Maharashtra",
        "destination": "Delhi Distribution Center, New Delhi",
        "status": "in_transit",
        "carrier": "BlueDart Express",
        "eta": datetime.now(timezone.utc) + timedelta(hours=18),
        "weight_kg": 450.5,
        "items_description": "Electronics - 200 units of LED monitors",
        "tracking_url": "https://tracking.example.com/SHIP-1001",
    },
    {
        "id": "SHIP-1002",
        "origin": "Chennai Port, Tamil Nadu",
        "destination": "Hyderabad Hub, Telangana",
        "status": "delayed",
        "carrier": "DTDC Logistics",
        "eta": datetime.now(timezone.utc) + timedelta(hours=36),
        "weight_kg": 1200.0,
        "items_description": "Auto parts - Brake assemblies and engine components",
        "tracking_url": "https://tracking.example.com/SHIP-1002",
    },
    {
        "id": "SHIP-1003",
        "origin": "Kolkata Factory, West Bengal",
        "destination": "Pune Retail Center, Maharashtra",
        "status": "delivered",
        "carrier": "Delhivery",
        "eta": datetime.now(timezone.utc) - timedelta(hours=2),
        "weight_kg": 85.3,
        "items_description": "Textiles - 500 units of cotton fabric rolls",
        "tracking_url": "https://tracking.example.com/SHIP-1003",
    },
    {
        "id": "SHIP-1004",
        "origin": "Ahmedabad Plant, Gujarat",
        "destination": "Jaipur Warehouse, Rajasthan",
        "status": "pending",
        "carrier": "Gati Express",
        "eta": datetime.now(timezone.utc) + timedelta(hours=48),
        "weight_kg": 2100.0,
        "items_description": "Chemicals - Industrial solvents and adhesives",
        "tracking_url": "https://tracking.example.com/SHIP-1004",
    },
    {
        "id": "SHIP-1005",
        "origin": "Bangalore Tech Park, Karnataka",
        "destination": "Mumbai Port, Maharashtra",
        "status": "in_transit",
        "carrier": "FedEx India",
        "eta": datetime.now(timezone.utc) + timedelta(hours=8),
        "weight_kg": 320.7,
        "items_description": "Server equipment - 50 rack servers for export",
        "tracking_url": "https://tracking.example.com/SHIP-1005",
    },
    {
        "id": "SHIP-1042",
        "origin": "Lucknow Depot, Uttar Pradesh",
        "destination": "Patna Distribution, Bihar",
        "status": "in_transit",
        "carrier": "XpressBees",
        "eta": datetime.now(timezone.utc) + timedelta(hours=12),
        "weight_kg": 780.0,
        "items_description": "FMCG goods - Mixed consumer products for retail",
        "tracking_url": "https://tracking.example.com/SHIP-1042",
    },
]


async def seed_shipments(db: AsyncSession):
    """Seed mock shipment data if not already present."""
    result = await db.execute(select(Shipment).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    for data in MOCK_SHIPMENTS:
        shipment = Shipment(**data)
        db.add(shipment)
    await db.commit()


async def get_shipment_by_id(db: AsyncSession, shipment_id: str) -> Shipment | None:
    """Lookup a shipment by its ID."""
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id.upper())
    )
    return result.scalar_one_or_none()


async def get_all_shipments(db: AsyncSession) -> list[Shipment]:
    """Get all shipments."""
    result = await db.execute(select(Shipment).order_by(Shipment.created_at.desc()))
    return list(result.scalars().all())
