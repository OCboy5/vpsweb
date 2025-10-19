"""
Database Models for VPSWeb Repository System

This module defines SQLAlchemy models for the repository database,
including background tasks, translations, and system metadata.

Features:
- SQLAlchemy async models with proper relationships
- Background task tracking and status management
- Translation job storage and retrieval
- System metrics and monitoring data
- Database indexes for performance optimization
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Text, Boolean,
    JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from ..config import get_config
from ..tasks import TaskStatus, TaskPriority
from ..utils.logger import get_structured_logger

logger = get_structured_logger()

Base = declarative_base()


class TaskStatusDB(str, Enum):
    """Database-compatible task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriorityDB(str, Enum):
    """Database-compatible task priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class BackgroundTask(Base):
    """
    Database model for background tasks.

    Stores task metadata, status, progress, and execution history
    for comprehensive task tracking and monitoring.
    """

    __tablename__ = "background_tasks"

    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name = Column(String(255), nullable=False)
    task_type = Column(String(100), nullable=False)

    # Status and priority
    status = Column(String(20), nullable=False, default=TaskStatusDB.PENDING)
    priority = Column(String(20), nullable=False, default=TaskPriorityDB.NORMAL)

    # Progress tracking
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(Text, default="", nullable=False)

    # Timing information
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    # Execution parameters
    max_retries = Column(Integer, default=3, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    timeout_seconds = Column(Integer, default=300, nullable=False)

    # Resource usage
    memory_usage_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)

    # Result and error storage
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Metadata and configuration
    metadata = Column(JSON, nullable=True, default=dict)
    config = Column(JSON, nullable=True, default=dict)

    # Relationships
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    metrics = relationship("TaskMetrics", back_populates="task", cascade="all, delete-orphan")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_background_tasks_status", "status"),
        Index("idx_background_tasks_type", "task_type"),
        Index("idx_background_tasks_priority", "priority"),
        Index("idx_background_tasks_created", "created_at"),
        Index("idx_background_tasks_updated", "updated_at"),
        Index("idx_background_tasks_type_status", "task_type", "status"),
        CheckConstraint("progress >= 0.0 AND progress <= 1.0", name="check_progress_range"),
        CheckConstraint("retry_count >= 0 AND retry_count <= max_retries", name="check_retry_count"),
        CheckConstraint("timeout_seconds > 0", name="check_timeout_positive"),
        CheckConstraint("memory_usage_mb IS NULL OR memory_usage_mb > 0", name="check_memory_positive"),
        CheckConstraint("cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0)",
                       name="check_cpu_range"),
    )

    def __repr__(self) -> str:
        return f"<BackgroundTask(id='{self.id}', name='{self.task_name}', status='{self.status}')>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return None

    @property
    def is_finished(self) -> bool:
        """Check if task is in a finished state."""
        return self.status in [TaskStatusDB.COMPLETED, TaskStatusDB.FAILED, TaskStatusDB.CANCELLED]

    @property
    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return (self.status == TaskStatusDB.FAILED and
                self.retry_count < self.max_retries)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "duration_seconds": self.duration_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "result": self.result,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
            "config": self.config or {},
            "is_finished": self.is_finished,
            "should_retry": self.should_retry,
        }


class TaskExecution(Base):
    """
    Database model for individual task executions.

    Tracks each execution attempt for retry analysis and auditing.
    """

    __tablename__ = "task_executions"

    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("background_tasks.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)

    # Execution timing
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Execution status
    status = Column(String(20), nullable=False)
    exit_code = Column(Integer, nullable=True)

    # Resource usage for this execution
    memory_usage_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    peak_memory_mb = Column(Float, nullable=True)

    # Output and error capture
    stdout_output = Column(Text, nullable=True)
    stderr_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Environment and context
    environment_info = Column(JSON, nullable=True)
    execution_context = Column(JSON, nullable=True)

    # Relationships
    task = relationship("BackgroundTask", back_populates="executions")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_task_executions_task", "task_id"),
        Index("idx_task_executions_started", "started_at"),
        Index("idx_task_executions_status", "status"),
        UniqueConstraint("task_id", "attempt_number", name="uq_task_attempt"),
        CheckConstraint("attempt_number > 0", name="check_attempt_positive"),
        CheckConstraint("cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0)",
                       name="check_exec_cpu_range"),
    )

    def __repr__(self) -> str:
        return f"<TaskExecution(id='{self.id}', task_id='{self.task_id}', attempt={self.attempt_number})>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return None


class TaskMetrics(Base):
    """
    Database model for task performance metrics.

    Stores detailed performance data for monitoring and optimization.
    """

    __tablename__ = "task_metrics"

    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("background_tasks.id"), nullable=False)

    # Metrics timestamp
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Performance metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    disk_io_read_mb = Column(Float, nullable=True)
    disk_io_write_mb = Column(Float, nullable=True)
    network_io_recv_mb = Column(Float, nullable=True)
    network_io_sent_mb = Column(Float, nullable=True)

    # Task-specific metrics
    progress = Column(Float, nullable=True)
    queue_wait_time_seconds = Column(Float, nullable=True)
    processing_rate = Column(Float, nullable=True)  # items per second

    # System metrics
    system_cpu_usage = Column(Float, nullable=True)
    system_memory_usage = Column(Float, nullable=True)
    system_disk_usage = Column(Float, nullable=True)

    # Custom metrics
    custom_metrics = Column(JSON, nullable=True)

    # Relationships
    task = relationship("BackgroundTask", back_populates="metrics")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_task_metrics_task", "task_id"),
        Index("idx_task_metrics_timestamp", "timestamp"),
        Index("idx_task_metrics_cpu", "cpu_usage_percent"),
        Index("idx_task_metrics_memory", "memory_usage_mb"),
        CheckConstraint("cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0)",
                       name="check_metrics_cpu_range"),
        CheckConstraint("memory_usage_mb IS NULL OR memory_usage_mb >= 0", name="check_metrics_memory_positive"),
        CheckConstraint("progress IS NULL OR (progress >= 0.0 AND progress <= 1.0)", name="check_metrics_progress_range"),
    )

    def __repr__(self) -> str:
        return f"<TaskMetrics(id='{self.id}', task_id='{self.task_id}', timestamp='{self.timestamp}')>"


class TranslationJob(Base):
    """
    Database model for translation jobs submitted through VPSWeb integration.

    Stores translation requests, results, and metadata for the repository system.
    """

    __tablename__ = "translation_jobs"

    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_task_id = Column(String, ForeignKey("background_tasks.id"), nullable=True)

    # Translation content
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)

    # Workflow information
    workflow_mode = Column(String(20), nullable=False, default="hybrid")
    poem_id = Column(String(255), nullable=True)

    # Job status and timing
    status = Column(String(20), nullable=False, default=TaskStatusDB.PENDING)
    submitted_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Quality metrics
    quality_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Metadata and configuration
    metadata = Column(JSON, nullable=True, default=dict)
    translation_config = Column(JSON, nullable=True, default=dict)
    result_metadata = Column(JSON, nullable=True, default=dict)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationships
    original_task = relationship("BackgroundTask", foreign_keys=[original_task_id])

    # Constraints and indexes
    __table_args__ = (
        Index("idx_translation_jobs_status", "status"),
        Index("idx_translation_jobs_languages", "source_language", "target_language"),
        Index("idx_translation_jobs_workflow", "workflow_mode"),
        Index("idx_translation_jobs_submitted", "submitted_at"),
        Index("idx_translation_jobs_poem", "poem_id"),
        CheckConstraint("source_language != target_language", name="check_different_languages"),
        CheckConstraint("quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)",
                       name="check_quality_range"),
        CheckConstraint("confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)",
                       name="check_confidence_range"),
        CheckConstraint("retry_count >= 0", name="check_retry_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<TranslationJob(id='{self.id}', status='{self.status}', '{self.source_language}'→'{self.target_language}')>"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return None

    @property
    def is_completed(self) -> bool:
        """Check if translation job is completed."""
        return self.status == TaskStatusDB.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert translation job to dictionary representation."""
        return {
            "id": self.id,
            "original_task_id": self.original_task_id,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "workflow_mode": self.workflow_mode,
            "poem_id": self.poem_id,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "quality_score": self.quality_score,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata or {},
            "translation_config": self.translation_config or {},
            "result_metadata": self.result_metadata or {},
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "is_completed": self.is_completed,
        }


class SystemMetrics(Base):
    """
    Database model for system-wide performance metrics.

    Stores system resource usage and performance data for monitoring.
    """

    __tablename__ = "system_metrics"

    # Primary fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # CPU metrics
    cpu_usage_percent = Column(Float, nullable=True)
    cpu_load_1min = Column(Float, nullable=True)
    cpu_load_5min = Column(Float, nullable=True)
    cpu_load_15min = Column(Float, nullable=True)

    # Memory metrics
    memory_total_mb = Column(Float, nullable=True)
    memory_used_mb = Column(Float, nullable=True)
    memory_available_mb = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)

    # Disk metrics
    disk_total_mb = Column(Float, nullable=True)
    disk_used_mb = Column(Float, nullable=True)
    disk_available_mb = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    disk_read_rate_mb_s = Column(Float, nullable=True)
    disk_write_rate_mb_s = Column(Float, nullable=True)

    # Network metrics
    network_sent_mb = Column(Float, nullable=True)
    network_recv_mb = Column(Float, nullable=True)
    network_sent_rate_mb_s = Column(Float, nullable=True)
    network_recv_rate_mb_s = Column(Float, nullable=True)

    # Application metrics
    active_tasks = Column(Integer, nullable=True)
    queued_tasks = Column(Integer, nullable=True)
    completed_tasks = Column(Integer, nullable=True)
    failed_tasks = Column(Integer, nullable=True)

    # Custom metrics
    custom_metrics = Column(JSON, nullable=True)

    # Constraints and indexes
    __table_args__ = (
        Index("idx_system_metrics_timestamp", "timestamp"),
        Index("idx_system_metrics_cpu", "cpu_usage_percent"),
        Index("idx_system_metrics_memory", "memory_usage_percent"),
        Index("idx_system_metrics_disk", "disk_usage_percent"),
        CheckConstraint("cpu_usage_percent IS NULL OR (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0)",
                       name="check_sys_cpu_range"),
        CheckConstraint("memory_usage_percent IS NULL OR (memory_usage_percent >= 0.0 AND memory_usage_percent <= 100.0)",
                       name="check_sys_memory_range"),
        CheckConstraint("disk_usage_percent IS NULL OR (disk_usage_percent >= 0.0 AND disk_usage_percent <= 100.0)",
                       name="check_sys_disk_range"),
    )

    def __repr__(self) -> str:
        return f"<SystemMetrics(id='{self.id}', timestamp='{self.timestamp}')>"


# Database utility functions
async def create_database_engine(database_url: str) -> async_sessionmaker[AsyncSession]:
    """
    Create async database engine with proper configuration.

    Args:
        database_url: Database connection URL

    Returns:
        Async session maker
    """
    logger.info(f"Creating database engine: {database_url}")

    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL logging
        future=True,
        # SQLite-specific optimizations
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
        } if database_url.startswith("sqlite") else {}
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info("Database engine created successfully")
    return session_maker


async def get_database_session() -> AsyncSession:
    """
    Get database session instance.

    Returns:
        Async database session
    """
    # This would typically get the session maker from a dependency injection container
    # For now, we'll create a simple global session maker
    if not hasattr(get_database_session, "_session_maker"):
        config = get_config()
        session_maker = await create_database_engine(config.database.database_url)
        get_database_session._session_maker = session_maker

    return get_database_session._session_maker()


# Database initialization function
async def initialize_database(database_url: str) -> None:
    """
    Initialize database with all tables and indexes.

    Args:
        database_url: Database connection URL
    """
    logger.info("Initializing database")

    # Create engine and tables
    session_maker = await create_database_engine(database_url)

    # Test database connection
    async with session_maker() as session:
        await session.execute("SELECT 1")
        await session.commit()

    logger.info("Database initialized successfully")


# Database cleanup functions
async def cleanup_old_tasks(session: AsyncSession, retention_hours: int = 24) -> int:
    """
    Clean up old completed tasks from database.

    Args:
        session: Database session
        retention_hours: Number of hours to retain tasks

    Returns:
        Number of tasks cleaned up
    """
    from sqlalchemy import delete
    from datetime import timedelta

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

    # Delete old metrics first (due to foreign key constraints)
    metrics_result = await session.execute(
        delete(TaskMetrics).where(TaskMetrics.timestamp < cutoff_time)
    )

    # Delete old task executions
    executions_result = await session.execute(
        delete(TaskExecution).where(TaskExecution.started_at < cutoff_time)
    )

    # Delete old tasks
    tasks_result = await session.execute(
        delete(BackgroundTask).where(
            BackgroundTask.completed_at < cutoff_time,
            BackgroundTask.status.in_([TaskStatusDB.COMPLETED, TaskStatusDB.FAILED, TaskStatusDB.CANCELLED])
        )
    )

    await session.commit()

    total_cleaned = (
        metrics_result.rowcount +
        executions_result.rowcount +
        tasks_result.rowcount
    )

    logger.info(f"Cleaned up {total_cleaned} old database records")
    return total_cleaned