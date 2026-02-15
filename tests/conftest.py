"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.db.base import Base
from app.dependencies import get_database_session


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://livechat_user:livechat_pass@localhost:5432/livechat_sync_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_database_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_agent_data():
    """Sample agent data for tests."""
    return {
        "livechat_agent_id": "lc_test_001",
        "ringcentral_extension_id": "101",
        "email": "test@example.com",
        "name": "Test Agent",
    }


@pytest.fixture
def sample_livechat_webhook():
    """Sample LiveChat webhook payload."""
    return {
        "webhook_id": "test_webhook_123",
        "action": "incoming_chat",
        "payload": {
            "chat": {
                "id": "test_chat_001",
                "users": [
                    {
                        "id": "lc_test_001",
                        "type": "agent",
                        "name": "Test Agent",
                    },
                    {
                        "id": "customer_001",
                        "type": "customer",
                        "email": "customer@example.com",
                    },
                ],
            }
        },
    }


@pytest.fixture
def sample_ringcentral_webhook():
    """Sample RingCentral webhook payload."""
    return {
        "uuid": "test_webhook_456",
        "event": "/restapi/v1.0/account/~/extension/101/telephony/sessions",
        "timestamp": "2024-01-01T12:00:00Z",
        "body": {
            "sessionId": "test_session_001",
            "parties": [
                {
                    "extensionId": "101",
                    "direction": {"value": "Inbound"},
                    "from": {"phoneNumber": "+15551234567"},
                    "status": {"code": "Answered"},
                }
            ],
        },
    }
