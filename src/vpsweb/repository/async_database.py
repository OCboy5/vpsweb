"""
VPSWeb Repository Async Database Configuration

Async database setup with SQLAlchemy for FastAPI background tasks.
Provides async database session management to prevent SQLite conflicts.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from .settings import settings

# Create async SQLAlchemy engine with SQLite-specific settings
async_engine = create_async_engine(
    settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False},  # Required for SQLite
    poolclass=StaticPool,  # Use StaticPool for SQLite
    echo=settings.log_level.lower() == "debug",  # Log SQL in debug mode
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_db() -> AsyncSession:
    """
    Dependency function to get async database session.

    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_async_session() -> AsyncSession:
    """
    Create a new async database session manually.

    Returns:
        AsyncSession: SQLAlchemy async database session
    """
    return AsyncSessionLocal()


async def check_async_db_connection() -> bool:
    """
    Test async database connection.

    Returns:
        bool: True if connection is successful
    """
    try:
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def init_async_db() -> None:
    """
    Initialize async database tables.
    Creates all tables defined in ORM models using async connection.
    """
    from . import models  # Import models to ensure they're registered
    from .database import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
