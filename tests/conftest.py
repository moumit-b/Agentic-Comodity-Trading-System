"""Shared pytest fixtures for all tests."""

import asyncio
import logging

import pytest
import pytest_asyncio
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

_db_available = False


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database(event_loop):
    """Initialize in-memory SQLite test database for all tests.

    Creates only the tables that are compatible with SQLite and needed by tests.
    The bars models use PostgreSQL-specific features (partitioning, composite PK
    with autoincrement) and are excluded.

    Sets the module-level _engine and _session_factory in src.core.database so
    that all code using `from src.core.database import get_session` works.
    """
    global _db_available
    import src.core.database as db_mod

    try:
        # Create a SQLite in-memory engine directly (bypass PostgreSQL-specific config)
        # StaticPool keeps a single connection alive for the entire session —
        # critical for in-memory SQLite where each connection gets its own DB.
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

        # Import models that tests need (registers them with Base.metadata)
        # Deliberately skip src.models.bars (PostgreSQL composite PK with autoincrement)
        import src.models.execution  # noqa: F401
        import src.models.learning  # noqa: F401
        import src.models.position  # noqa: F401
        import src.models.risk  # noqa: F401
        import src.models.settlement  # noqa: F401
        import src.models.signal  # noqa: F401
        from src.core.database import Base

        # SQLite requires INTEGER (not BIGINT) for autoincrement primary keys.
        # Convert BigInteger PK columns to Integer for test compatibility.
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if column.primary_key and column.autoincrement and isinstance(
                    column.type, type(column.type)
                ):
                    from sqlalchemy import BigInteger as _BigInt

                    if isinstance(column.type, _BigInt):
                        column.type = Integer()

        # Create only the tables we imported (skip bars which are PG-only)
        tables_to_create = [
            Base.metadata.tables[name]
            for name in [
                "circuit_breakers",
                "settlements",
                "executions",
                "decisions",
                "signals",
                "positions",
                "prediction_logs",
                "context_analyses",
                "strategy_overrides",
            ]
            if name in Base.metadata.tables
        ]

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=tables_to_create)

        # Set module-level engine and session factory so get_session() works.
        # This is the key: get_session() calls get_session_factory() which reads
        # db_mod._session_factory. By setting it here, ALL code that imported
        # get_session from src.core.database will use our test DB.
        db_mod._engine = engine
        db_mod._session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )

        _db_available = True
        logger.info("Test database initialized (SQLite in-memory)")

        yield

        # Cleanup
        db_mod._engine = None
        db_mod._session_factory = None
        await engine.dispose()

    except Exception as e:
        logger.warning(f"Test database not available (unit tests still work): {e}")
        import traceback

        traceback.print_exc()
        _db_available = False
        yield


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test."""
    yield

    if not _db_available:
        return

    try:
        from sqlalchemy import delete

        from src.core.database import get_session
        from src.models.execution import Execution
        from src.models.risk import CircuitBreaker
        from src.models.settlement import Settlement

        async with get_session() as session:
            await session.execute(delete(CircuitBreaker))
            await session.execute(delete(Execution))
            await session.execute(delete(Settlement))
    except Exception:
        pass
