"""
VPSWeb Repository System - Database Configuration

This module handles database connection setup, session management,
and database initialization for the VPSWeb repository system.

Features:
- Async SQLAlchemy engine with WAL mode for better performance
- Connection pooling configuration
- Session management with proper context handling
- Database initialization and migration support
- Structured logging integration
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
from contextlib import asynccontextmanager

from sqlalchemy import event, text, pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool, QueuePool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """
    Database configuration for connection pooling and optimization.

    Centralizes all database-related configuration parameters with
    sensible defaults for different deployment scenarios.
    """

    def __init__(
        self,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        pool_reset_on_return: str = "commit",
        echo: bool = False,
        echo_pool: bool = False,
        future: bool = True,
        connect_args: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize database configuration.

        Args:
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum overflow connections beyond pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection
            pool_recycle: Seconds to recycle connections (prevent stale connections)
            pool_pre_ping: Validate connections before use
            pool_reset_on_return: What to do with connections when returned
            echo: Enable SQLAlchemy query logging
            echo_pool: Enable connection pool logging
            future: Use SQLAlchemy 2.0 style
            connect_args: Additional connection arguments
            execution_options: Default execution options
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.pool_reset_on_return = pool_reset_on_return
        self.echo = echo
        self.echo_pool = echo_pool
        self.future = future
        self.connect_args = connect_args or {}
        self.execution_options = execution_options or {}

    @classmethod
    def for_development(cls, database_url: str) -> 'DatabaseConfig':
        """Create development-optimized configuration."""
        return cls(
            pool_size=5,
            max_overflow=10,
            pool_timeout=20,
            pool_recycle=1800,  # 30 minutes
            echo=True,
            echo_pool=True,
            connect_args=cls._get_default_connect_args(database_url),
        )

    @classmethod
    def for_production(cls, database_url: str) -> 'DatabaseConfig':
        """Create production-optimized configuration."""
        return cls(
            pool_size=20,
            max_overflow=30,
            pool_timeout=30,
            pool_recycle=3600,  # 1 hour
            echo=False,
            echo_pool=False,
            connect_args=cls._get_default_connect_args(database_url),
            execution_options={
                "isolation_level": "READ_COMMITTED",
                "autocommit": False,
            }
        )

    @classmethod
    def for_testing(cls, database_url: str) -> 'DatabaseConfig':
        """Create testing-optimized configuration."""
        return cls(
            pool_size=1,
            max_overflow=0,
            pool_timeout=10,
            pool_recycle=300,  # 5 minutes
            echo=False,
            connect_args=cls._get_default_connect_args(database_url),
        )

    @staticmethod
    def _get_default_connect_args(database_url: str) -> Dict[str, Any]:
        """Get default connection arguments based on database URL."""
        if "sqlite" in database_url:
            return {
                "check_same_thread": False,
                "timeout": 20,
                "isolation_level": None,  # Autocommit mode for SQLite
            }
        elif "postgresql" in database_url:
            return {
                "server_settings": {
                    "application_name": "vpsweb_repository",
                    "jit": "off",  # Disable JIT for better query planning
                }
            }
        else:
            return {}


class ConnectionPoolMonitor:
    """
    Monitors database connection pool health and performance.

    Provides insights into pool usage, connection health, and
    performance metrics for optimization.
    """

    def __init__(self, engine):
        """
        Initialize the pool monitor.

        Args:
            engine: SQLAlchemy engine to monitor
        """
        self.engine = engine
        self.logger = logging.getLogger(f"{__name__}.PoolMonitor")

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current pool status and metrics.

        Returns:
            Dictionary with pool status information
        """
        if not hasattr(self.engine.pool, 'status'):
            return {"error": "Pool status not available"}

        pool = self.engine.pool
        status = pool.status()

        return {
            "pool_size": pool.size(),
            "checked_in": status['pool_checked_in'],
            "checked_out": status['pool_checked_out'],
            "overflow": status['pool_overflow'],
            "invalid": status['pool_invalid'],
            "total_connections": status['pool_checked_in'] + status['pool_checked_out'],
            "available_connections": status['pool_checked_in'],
            "active_connections": status['pool_checked_out'],
        }

    def log_pool_status(self) -> None:
        """Log current pool status for monitoring."""
        status = self.get_pool_status()
        self.logger.info(
            f"Connection pool status - Size: {status.get('pool_size', 'N/A')}, "
            f"Available: {status.get('available_connections', 'N/A')}, "
            f"Active: {status.get('active_connections', 'N/A')}, "
            f"Overflow: {status.get('overflow', 'N/A')}"
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive pool health check.

        Returns:
            Health check results with recommendations
        """
        try:
            # Test database connectivity
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Get pool metrics
            pool_status = self.get_pool_status()

            # Calculate health indicators
            total_connections = pool_status.get('total_connections', 0)
            pool_size = pool_status.get('pool_size', 0)
            active_connections = pool_status.get('active_connections', 0)

            utilization = (active_connections / total_connections * 100) if total_connections > 0 else 0

            # Determine health status
            health_status = "healthy"
            recommendations = []

            if utilization > 80:
                health_status = "warning"
                recommendations.append("High pool utilization - consider increasing pool_size")
            elif utilization < 20 and total_connections > pool_size:
                health_status = "warning"
                recommendations.append("Low utilization - consider reducing pool_size")

            if pool_status.get('overflow', 0) > 0:
                health_status = "warning"
                recommendations.append("Pool overflow detected - consider increasing max_overflow")

            return {
                "status": health_status,
                "pool_metrics": pool_status,
                "utilization_percent": round(utilization, 2),
                "recommendations": recommendations,
                "timestamp": str(pool.status()['timestamp']) if 'timestamp' in pool.status() else None,
            }

        except Exception as e:
            self.logger.error(f"Pool health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pool_metrics": self.get_pool_status(),
            }


class DatabaseManager:
    """
    Manages database connections and sessions for the repository system.

    Handles SQLite configuration with WAL mode, connection pooling,
    and provides async session management with advanced optimization.
    """

    def __init__(self, database_url: str, config: Optional[DatabaseConfig] = None):
        """
        Initialize the database manager.

        Args:
            database_url: Database connection URL
            config: Database configuration, defaults to development config
        """
        self.database_url = database_url
        self.config = config or DatabaseConfig.for_development(database_url)
        self.engine = None
        self.session_factory = None
        self.pool_monitor = None

    async def initialize(self) -> None:
        """
        Initialize the database engine and session factory.

        Creates the async engine with advanced connection pooling,
        sets up WAL mode, and creates session factory with optimization.
        """
        logger.info(f"Initializing database with URL: {self.database_url}")
        logger.info(f"Using pool configuration: size={self.config.pool_size}, "
                   f"max_overflow={self.config.max_overflow}")

        # Determine pool class based on database type
        if "sqlite" in self.database_url:
            pool_class = StaticPool
        else:
            pool_class = QueuePool

        # Create async engine with advanced configuration
        self.engine = create_async_engine(
            self.database_url,
            echo=self.config.echo,
            poolclass=pool_class,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=self.config.pool_recycle,
            pool_pre_ping=self.config.pool_pre_ping,
            pool_reset_on_return=self.config.pool_reset_on_return,
            connect_args=self.config.connect_args,
            execution_options=self.config.execution_options,
            future=self.config.future,
        )

        # Set up connection pool monitoring
        self.pool_monitor = ConnectionPoolMonitor(self.engine)

        # Configure WAL mode and other SQLite pragmas
        await self._configure_sqlite()

        # Create session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Important for async operations
            autoflush=True,
            autocommit=False,
        )

        logger.info("Database engine and session factory initialized successfully")

    async def _configure_sqlite(self) -> None:
        """
        Configure SQLite-specific settings for optimal performance.

        Enables WAL mode, sets appropriate pragmas for performance
        and data integrity.
        """
        logger.info("Configuring SQLite settings")

        pragmas = [
            # Enable Write-Ahead Logging for better concurrency
            "PRAGMA journal_mode=WAL",
            # Enable foreign key constraints
            "PRAGMA foreign_keys=ON",
            # Optimize for single-writer, multiple-reader scenario
            "PRAGMA synchronous=NORMAL",
            # Configure cache size (default is 2000 pages)
            "PRAGMA cache_size=10000",
            # Set temp store to memory
            "PRAGMA temp_store=MEMORY",
            # Enable memory-mapped I/O for better performance
            "PRAGMA mmap_size=268435456",  # 256MB
            # Configure busy timeout (in milliseconds)
            "PRAGMA busy_timeout=30000",
            # Optimize for small to medium datasets
            "PRAGMA optimize",
        ]

        async with self.engine.begin() as conn:
            for pragma in pragmas:
                try:
                    await conn.execute(text(pragma))
                    logger.debug(f"Applied pragma: {pragma}")
                except Exception as e:
                    logger.warning(f"Failed to apply pragma {pragma}: {e}")

        logger.info("SQLite configuration completed")

    async def create_tables(self) -> None:
        """
        Create all database tables using the models.

        Should be called after initialize() to create the schema.
        """
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.info("Creating database tables")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: This will delete all data! Use only for testing.
        """
        if not self.engine:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.warning("Dropping all database tables")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("All database tables dropped")

    def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Returns:
            AsyncSession: New database session

        Usage:
            async with db.get_session() as session:
                # Use session here
                pass
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self.session_factory()

    async def get_session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with context management.

        Yields:
            AsyncSession: Database session for use in async context

        Usage:
            async with db.get_session_context() as session:
                # Use session here
                pass
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> dict:
        """
        Perform a comprehensive health check on the database and connection pool.

        Returns:
            dict: Health check results with pool metrics
        """
        if not self.engine:
            return {
                "status": "error",
                "message": "Database not initialized"
            }

        try:
            # Basic connectivity test
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.scalar()

                # Get database file size if SQLite
                if "sqlite" in self.database_url:
                    db_path = self.database_url.replace("sqlite+aiosqlite:///", "")
                    if Path(db_path).exists():
                        size = Path(db_path).stat().st_size
                        size_mb = size / (1024 * 1024)
                    else:
                        size_mb = 0
                else:
                    size_mb = None

                # Get database version and stats
                if "sqlite" in self.database_url:
                    version_result = await conn.execute(text("SELECT sqlite_version()"))
                    db_version = version_result.scalar()
                else:
                    db_version = "Unknown"

            # Get pool health check
            pool_health = await self.pool_monitor.health_check() if self.pool_monitor else {"status": "unavailable"}

            return {
                "status": "healthy",
                "database_url": self.database_url,
                "can_connect": True,
                "size_mb": size_mb,
                "database_version": db_version,
                "pool_health": pool_health,
                "configuration": {
                    "pool_size": self.config.pool_size,
                    "max_overflow": self.config.max_overflow,
                    "pool_timeout": self.config.pool_timeout,
                    "pool_recycle": self.config.pool_recycle,
                }
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "database_url": self.database_url,
                "pool_health": await self.pool_monitor.health_check() if self.pool_monitor else {"status": "unavailable"}
            }

    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current connection pool status.

        Returns:
            Dictionary with pool status information
        """
        if not self.pool_monitor:
            return {"error": "Pool monitor not initialized"}

        return self.pool_monitor.get_pool_status()

    def log_pool_status(self) -> None:
        """Log current pool status for monitoring."""
        if self.pool_monitor:
            self.pool_monitor.log_pool_status()

    @asynccontextmanager
    async def get_session_with_retry(self, max_retries: int = 3):
        """
        Get a database session with automatic retry logic.

        Args:
            max_retries: Maximum number of retry attempts

        Yields:
            AsyncSession: Database session with retry logic
        """
        for attempt in range(max_retries):
            try:
                async with self.get_session_context() as session:
                    yield session
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                logger.warning(f"Database session attempt {attempt + 1} failed, retrying: {e}")
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def get_pool_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive pool performance metrics.

        Returns:
            Dictionary with detailed pool metrics
        """
        if not self.pool_monitor:
            return {"error": "Pool monitor not initialized"}

        pool_status = self.pool_monitor.get_pool_status()

        # Calculate additional metrics
        total_connections = pool_status.get('total_connections', 0)
        active_connections = pool_status.get('active_connections', 0)
        available_connections = pool_status.get('available_connections', 0)

        utilization_rate = (active_connections / total_connections * 100) if total_connections > 0 else 0
        availability_rate = (available_connections / total_connections * 100) if total_connections > 0 else 0

        return {
            **pool_status,
            "utilization_rate_percent": round(utilization_rate, 2),
            "availability_rate_percent": round(availability_rate, 2),
            "efficiency_score": self._calculate_efficiency_score(pool_status),
        }

    def _calculate_efficiency_score(self, pool_status: Dict[str, Any]) -> float:
        """
        Calculate pool efficiency score (0-100).

        Args:
            pool_status: Current pool status

        Returns:
            Efficiency score
        """
        total_connections = pool_status.get('total_connections', 0)
        active_connections = pool_status.get('active_connections', 0)
        overflow = pool_status.get('overflow', 0)

        if total_connections == 0:
            return 0.0

        # Base score from utilization
        utilization = active_connections / total_connections
        base_score = min(utilization * 100, 80)  # Cap at 80 for utilization

        # Penalty for overflow
        overflow_penalty = min(overflow * 10, 20)

        # Bonus for optimal utilization (50-80%)
        if 0.5 <= utilization <= 0.8:
            bonus = 20
        else:
            bonus = 0

        return max(0, min(100, base_score + bonus - overflow_penalty))

    async def optimize_pool_settings(self) -> Dict[str, Any]:
        """
        Analyze current pool usage and provide optimization recommendations.

        Returns:
            Optimization recommendations and analysis
        """
        if not self.pool_monitor:
            return {"error": "Pool monitor not initialized"}

        metrics = await self.get_pool_metrics()
        current_config = {
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "pool_timeout": self.config.pool_timeout,
        }

        recommendations = []
        utilization = metrics.get('utilization_rate_percent', 0)
        overflow = metrics.get('overflow', 0)

        # Analyze utilization
        if utilization > 90:
            recommendations.append({
                "priority": "high",
                "type": "increase_pool_size",
                "message": f"Very high utilization ({utilization:.1f}%). Increase pool_size",
                "suggested_value": self.config.pool_size + 5
            })
        elif utilization > 80:
            recommendations.append({
                "priority": "medium",
                "type": "increase_pool_size",
                "message": f"High utilization ({utilization:.1f}%). Consider increasing pool_size",
                "suggested_value": self.config.pool_size + 2
            })
        elif utilization < 20 and self.config.pool_size > 5:
            recommendations.append({
                "priority": "low",
                "type": "decrease_pool_size",
                "message": f"Low utilization ({utilization:.1f}%). Consider reducing pool_size",
                "suggested_value": max(5, self.config.pool_size - 2)
            })

        # Analyze overflow
        if overflow > 0:
            recommendations.append({
                "priority": "medium",
                "type": "increase_max_overflow",
                "message": f"Pool overflow detected ({overflow} connections). Increase max_overflow",
                "suggested_value": self.config.max_overflow + overflow
            })

        return {
            "current_metrics": metrics,
            "current_configuration": current_config,
            "recommendations": recommendations,
            "optimization_score": metrics.get('efficiency_score', 0),
        }

    async def close(self) -> None:
        """
        Close the database engine and clean up resources.
        """
        if self.engine:
            logger.info("Closing database engine")
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None


# Global database manager instance
_db_manager: DatabaseManager | None = None


async def get_database_manager(
    database_url: str,
    config: Optional[DatabaseConfig] = None,
    environment: str = "development"
) -> DatabaseManager:
    """
    Get or create the global database manager instance.

    Args:
        database_url: Database connection URL
        config: Optional database configuration
        environment: Environment type (development, production, testing)

    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager

    if _db_manager is None:
        if config is None:
            config = DatabaseConfig.for_development(database_url)
            if environment == "production":
                config = DatabaseConfig.for_production(database_url)
            elif environment == "testing":
                config = DatabaseConfig.for_testing(database_url)

        _db_manager = DatabaseManager(database_url, config)
        await _db_manager.initialize()

    return _db_manager


async def get_database_manager_for_environment(
    database_url: str,
    environment: str
) -> DatabaseManager:
    """
    Get database manager configured for specific environment.

    Args:
        database_url: Database connection URL
        environment: Environment type (development, production, testing)

    Returns:
        DatabaseManager: Environment-configured database manager
    """
    return await get_database_manager(database_url, environment=environment)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session from the global manager.

    Yields:
        AsyncSession: Database session for use
    """
    global _db_manager

    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call get_database_manager() first.")

    async with _db_manager.get_session_context() as session:
        yield session


# Database initialization helper
async def initialize_database(
    database_url: str,
    config: Optional[DatabaseConfig] = None,
    environment: str = "development"
) -> DatabaseManager:
    """
    Initialize the database with all tables using advanced configuration.

    Args:
        database_url: Database connection URL
        config: Optional database configuration
        environment: Environment type (development, production, testing)

    Returns:
        DatabaseManager: Initialized database manager
    """
    db_manager = await get_database_manager(database_url, config, environment)
    await db_manager.create_tables()

    logger.info(f"Database initialization completed successfully for {environment} environment")
    return db_manager


# Database optimization utilities
async def get_database_performance_report(database_url: str) -> Dict[str, Any]:
    """
    Generate comprehensive database performance report.

    Args:
        database_url: Database connection URL

    Returns:
        Performance report with metrics and recommendations
    """
    db_manager = await get_database_manager(database_url)

    # Get pool metrics
    pool_metrics = await db_manager.get_pool_metrics()

    # Get optimization recommendations
    optimization_report = await db_manager.optimize_pool_settings()

    # Perform health check
    health_status = await db_manager.health_check()

    return {
        "health_check": health_status,
        "pool_metrics": pool_metrics,
        "optimization_recommendations": optimization_report,
        "configuration_summary": {
            "pool_size": db_manager.config.pool_size,
            "max_overflow": db_manager.config.max_overflow,
            "pool_timeout": db_manager.config.pool_timeout,
            "pool_recycle": db_manager.config.pool_recycle,
            "environment": environment if 'environment' in locals() else "custom"
        },
        "performance_score": optimization_report.get("optimization_score", 0)
    }