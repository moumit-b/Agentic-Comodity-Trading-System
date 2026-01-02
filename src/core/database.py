"""Database setup and session management using async SQLAlchemy."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


# ==============================================================================
# Base Model
# ==============================================================================


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# ==============================================================================
# Engine & Session Management
# ==============================================================================

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(config: DatabaseConfig) -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.

    Args:
        config: Database configuration

    Returns:
        Configured AsyncEngine instance
    """
    logger.info(
        f"Creating async engine: {config.host}:{config.port}/{config.name} "
        f"(pool_size={config.pool_size}, max_overflow={config.max_overflow})"
    )

    return create_async_engine(
        config.url,
        echo=config.echo_sql,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_timeout=config.pool_timeout,
        pool_recycle=config.pool_recycle,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            "timeout": config.command_timeout,
            "command_timeout": config.command_timeout,
        },
    )


def create_test_engine(config: DatabaseConfig) -> AsyncEngine:
    """
    Create async engine for testing with no connection pooling.

    Args:
        config: Database configuration

    Returns:
        AsyncEngine with NullPool for tests
    """
    logger.info(f"Creating test engine (NullPool): {config.host}:{config.port}/{config.name}")

    return create_async_engine(
        config.url,
        echo=config.echo_sql,
        poolclass=NullPool,  # No connection pooling for tests
        connect_args={
            "timeout": config.command_timeout,
            "command_timeout": config.command_timeout,
        },
    )


def init_db(config: DatabaseConfig, test_mode: bool = False) -> None:
    """
    Initialize database engine and session factory.

    Must be called at application startup before any database operations.

    Args:
        config: Database configuration
        test_mode: If True, use NullPool for testing

    Example:
        >>> from src.core.config import DatabaseConfig
        >>> config = DatabaseConfig()
        >>> init_db(config)
    """
    global _engine, _session_factory

    if _engine is not None:
        logger.warning("Database already initialized, skipping...")
        return

    # Create engine
    _engine = create_test_engine(config) if test_mode else create_engine(config)

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Allow access to objects after commit
        autoflush=False,  # Explicit flush control
        autocommit=False,  # Explicit transaction control
    )

    logger.info("Database initialized successfully")


async def shutdown_db() -> None:
    """
    Shutdown database engine and close all connections.

    Should be called at application shutdown.

    Example:
        >>> await shutdown_db()
    """
    global _engine, _session_factory

    if _engine is None:
        logger.warning("Database not initialized, skipping shutdown...")
        return

    logger.info("Shutting down database engine...")
    await _engine.dispose()
    _engine = None
    _session_factory = None
    logger.info("Database shutdown complete")


def get_engine() -> AsyncEngine:
    """
    Get the global async engine instance.

    Returns:
        AsyncEngine instance

    Raises:
        RuntimeError: If database not initialized

    Example:
        >>> engine = get_engine()
        >>> async with engine.begin() as conn:
        ...     await conn.execute(text("SELECT 1"))
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() at application startup.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the global session factory.

    Returns:
        async_sessionmaker instance

    Raises:
        RuntimeError: If database not initialized

    Example:
        >>> factory = get_session_factory()
        >>> async with factory() as session:
        ...     result = await session.execute(select(Position))
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() at application startup.")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session context manager.

    Automatically handles:
    - Session creation
    - Transaction commit on success
    - Transaction rollback on error
    - Session cleanup

    Yields:
        AsyncSession instance

    Example:
        >>> async with get_session() as session:
        ...     position = Position(symbol="USO", side="LONG", qty=100)
        ...     session.add(position)
        ...     # Automatic commit on exit
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session rollback due to error: {e}")
            raise
        finally:
            await session.close()


# ==============================================================================
# Database Utilities
# ==============================================================================


async def create_all_tables() -> None:
    """
    Create all tables defined in Base metadata.

    NOTE: For production, use Alembic migrations instead.
    This is primarily for testing and initial setup.

    Example:
        >>> await create_all_tables()
    """
    engine = get_engine()
    logger.info("Creating all tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("All tables created successfully")


async def drop_all_tables() -> None:
    """
    Drop all tables defined in Base metadata.

    WARNING: This will delete all data! Use with extreme caution.
    Primarily for testing.

    Example:
        >>> await drop_all_tables()
    """
    engine = get_engine()
    logger.warning("Dropping all tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.warning("All tables dropped")


async def check_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        True if connection successful, False otherwise

    Example:
        >>> if await check_connection():
        ...     print("Database connected!")
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
