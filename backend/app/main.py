import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, close_db, get_db, async_session_factory
from app.redis_client import init_redis, close_redis
from app.websocket.manager import manager
from app.websocket.handlers import handle_ws_connection
from app.dependencies import get_user_from_ws_token
from app.services.shipment_service import seed_shipments

from app.routers import auth, channels, messages, dm, shipments, ai, users

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info("Starting Hemut backend...")
    await init_db()
    await init_redis()
    await manager.start()

    # Seed mock data
    async with async_session_factory() as session:
        await seed_shipments(session)
        # Seed default channels
        from app.models.channel import Channel
        from sqlalchemy import select
        result = await session.execute(select(Channel).where(Channel.is_dm == False).limit(1))
        if not result.scalar_one_or_none():
            default_channels = [
                Channel(name="general", description="General discussion for all team members"),
                Channel(name="route-east", description="East route logistics and shipment tracking"),
                Channel(name="route-west", description="West route logistics and operations"),
                Channel(name="warehouse-mumbai", description="Mumbai warehouse operations and inventory"),
                Channel(name="warehouse-delhi", description="Delhi distribution center updates"),
                Channel(name="dispatch", description="Dispatch coordination and scheduling"),
                Channel(name="alerts", description="System alerts and urgent notifications"),
            ]
            for ch in default_channels:
                session.add(ch)
            await session.commit()
            logger.info("Seeded default channels")

    logger.info("Hemut backend started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down Hemut backend...")
    await manager.stop()
    await close_redis()
    await close_db()
    logger.info("Hemut backend shut down.")


app = FastAPI(
    title="Hemut - Real-Time Logistics Collaboration",
    description="Slack-style collaboration platform for logistics teams",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(messages.router)
app.include_router(dm.router)
app.include_router(shipments.router)
app.include_router(ai.router)
app.include_router(users.router)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """Main WebSocket endpoint for real-time communication."""
    async with async_session_factory() as db:
        user = await get_user_from_ws_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return

        await handle_ws_connection(websocket, user, db)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "hemut-backend"}
