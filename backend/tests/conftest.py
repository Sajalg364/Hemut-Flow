import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, String
from unittest.mock import AsyncMock, patch

from app.database import Base, get_db
from app.redis_client import get_redis


# Use SQLite for tests (in-memory) — override PostgreSQL-specific types
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


# Register type adapters for UUID with SQLite
@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create test database tables before each test."""
    # Import models to register them
    from app.models import user, channel, membership, message, shipment  # noqa

    # For SQLite compat, we need to render the tables without PG-specific defaults
    # Use create_all with the test engine - SQLAlchemy will adapt types
    async with test_engine.begin() as conn:
        # Drop first to ensure clean state
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def override_db():
    """Override the database dependency for tests."""
    async def _get_test_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Import app here to avoid circular issues
    from app.main import app
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


# Mock Redis for tests
class MockRedis:
    """In-memory mock Redis for testing."""

    def __init__(self):
        self._data = {}
        self._sets = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, value, ex=None):
        self._data[key] = value

    async def setex(self, key, seconds, value):
        self._data[key] = value

    async def delete(self, key):
        self._data.pop(key, None)

    async def incr(self, key):
        self._data[key] = str(int(self._data.get(key, "0")) + 1)
        return int(self._data[key])

    async def sadd(self, key, *values):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(values)

    async def srem(self, key, *values):
        if key in self._sets:
            self._sets[key] -= set(values)

    async def smembers(self, key):
        return self._sets.get(key, set())

    async def sismember(self, key, value):
        return value in self._sets.get(key, set())

    async def publish(self, channel, message):
        pass  # No-op for tests

    async def ping(self):
        return True

    async def close(self):
        pass


mock_redis_instance = MockRedis()


@pytest_asyncio.fixture(autouse=True)
async def mock_redis_client():
    """Mock Redis for all tests."""
    async def _mock_get_redis():
        return mock_redis_instance

    with patch("app.redis_client.get_redis", new=_mock_get_redis):
        with patch("app.services.message_service.get_redis", new=_mock_get_redis):
            with patch("app.services.presence_service.get_redis", new=_mock_get_redis):
                with patch("app.services.ai_service.get_redis", new=_mock_get_redis):
                    yield mock_redis_instance
    # Reset mock Redis state
    mock_redis_instance._data.clear()
    mock_redis_instance._sets.clear()


@pytest_asyncio.fixture
async def client(override_db, mock_redis_client):
    """Provide an async HTTP test client."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register a user and return auth headers."""
    response = await client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "display_name": "Test User",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_auth_headers(client):
    """Register a second user and return auth headers."""
    response = await client.post("/api/auth/register", json={
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "testpass123",
        "display_name": "Test User 2",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
