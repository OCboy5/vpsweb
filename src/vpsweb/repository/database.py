"""
VPSWeb Repository Database Configuration v0.3.1

SQLite database setup with SQLAlchemy ORM configuration.
Provides database session management and initialization utilities.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
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
    pool_reset_on_return=None,  # Disable pool reset to avoid SQLite rollback issues
    echo=settings.log_level.lower() == "debug",  # Log SQL in debug mode
)


# Enable foreign key constraints for SQLite connections
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite"""
    print("🔥 DEBUG: Setting foreign_keys=ON for new connection")
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Also ensure foreign keys are enabled on checkout from pool
@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Ensure foreign keys are enabled when checking out from pool"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
        try:
            db.rollback()
        except Exception:
            # Ignore rollback errors - they occur when no transaction is active
            # This is common with SQLite for read-only operations
            pass
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
