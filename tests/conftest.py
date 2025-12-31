"""Shared pytest fixtures for all tests."""

import asyncio

import pytest
import pytest_asyncio

from src.core.config import DatabaseConfig
from src.core.database import create_all_tables, init_db, shutdown_db
from src.models.risk import CircuitBreaker


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database(event_loop):
    """Initialize test database with in-memory SQLite."""
    # Create test config with in-memory SQLite
    test_config = DatabaseConfig()
    # Override URL to use in-memory SQLite
    test_config._url = "sqlite+aiosqlite:///:memory:"

    # Initialize database
    init_db(test_config, test_mode=True)

    # Create all tables
    await create_all_tables()

    yield

    # Cleanup
    await shutdown_db()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test."""
    yield

    # Clear all test data after test
    try:
        from src.core.database import get_session
        from src.models.settlement import Settlement
        from sqlalchemy import delete

        async with get_session() as session:
            # Clear circuit breakers
            await session.execute(delete(CircuitBreaker))
            # Clear settlements
            await session.execute(delete(Settlement))
            await session.commit()
    except Exception:
        # Ignore cleanup errors
        pass
