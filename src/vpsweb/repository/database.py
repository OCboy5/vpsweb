"""
VPSWeb Repository Database Configuration v0.3.1

SQLite database setup with SQLAlchemy ORM configuration.
Provides database session management and initialization utilities.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import StaticPool
from .settings import settings

# Create SQLAlchemy engine with SQLite-specific settings
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,  # Required for SQLite
        "timeout": 20,  # Set timeout for database locking
        "autocommit": False,  # Enable modern transaction control for proper session isolation
    },
    poolclass=StaticPool,  # Use StaticPool for SQLite
    echo=settings.log_level.lower() == "debug",  # Log SQL in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for ORM models
Base = declarative_base()


def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in ORM models.
    """
    from . import models  # Import models to ensure they're registered

    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Dependency function to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Handle any exceptions during database operations
        db.rollback()
        raise
    finally:
        try:
            # Close session safely, ignoring rollback errors
            db.close()
        except Exception:
            # Ignore cleanup errors - they don't affect functionality
            pass


def create_session() -> Session:
    """
    Create a new database session manually.

    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()


def check_db_connection() -> bool:
    """
    Test database connection.

    Returns:
        bool: True if connection is successful
    """
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
