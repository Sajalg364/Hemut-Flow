from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Normalise the DATABASE_URL to use the psycopg async dialect.
# The user (or Render env-var) may supply any of:
#   postgresql://…  |  postgresql+asyncpg://…  |  postgresql+psycopg://…
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql+asyncpg://"):
    _db_url = _db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_async_engine(
    _db_url,
    echo=settings.APP_ENV == "development",
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (for dev use; production should use Alembic)."""
    async with engine.begin() as conn:
        from app.models import user, channel, membership, message, shipment  # noqa
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose of the engine."""
    await engine.dispose()
