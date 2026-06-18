from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import settings

# Detect if we're connecting through PgBouncer (e.g. Supabase pooler).
# PgBouncer in transaction mode doesn't support prepared statements,
# so we must disable statement caching AND use NullPool (let PgBouncer pool).
_is_pgbouncer = "pooler.supabase.com" in settings.DATABASE_URL

if _is_pgbouncer:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_ENV == "development",
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.APP_ENV == "development",
        pool_size=20,
        max_overflow=10,
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
