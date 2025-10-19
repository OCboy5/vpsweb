"""
Repository Access Layer for VPSWeb Repository System

This module provides high-level repository operations for background tasks,
translation jobs, and system metrics with proper error handling and logging.

Features:
- Async database operations with proper session management
- Background task CRUD operations
- Translation job management
- System metrics collection and querying
- Performance optimized queries with proper indexing
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    BackgroundTask, TaskExecution, TaskMetrics, TranslationJob, SystemMetrics,
    TaskStatusDB, TaskPriorityDB
)
from ..tasks import TaskStatus, TaskPriority
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class TaskNotFoundError(DatabaseError):
    """Exception raised when task is not found."""
    pass


class Repository:
    """
    High-level repository for database operations.

    Provides async methods for managing background tasks, translation jobs,
    and system metrics with proper error handling and logging.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.logger = logger.bind(repository="Repository")

    # Background Task Operations
    async def create_task(
        self,
        task_name: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> BackgroundTask:
        """
        Create a new background task.

        Args:
            task_name: Human-readable task name
            task_type: Task type identifier
            priority: Task priority level
            max_retries: Maximum retry attempts
            timeout_seconds: Task timeout in seconds
            metadata: Task metadata
            config: Task configuration

        Returns:
            Created background task
        """
        try:
            task = BackgroundTask(
                task_name=task_name,
                task_type=task_type,
                priority=TaskPriorityDB(priority.value),
                max_retries=max_retries,
                timeout_seconds=timeout_seconds,
                metadata=metadata or {},
                config=config or {}
            )

            self.session.add(task)
            await self.session.commit()
            await self.session.refresh(task)

            self.logger.info(
                "Created background task",
                task_id=task.id,
                task_name=task_name,
                task_type=task_type,
                priority=priority.value
            )

            return task

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create background task",
                task_name=task_name,
                error=str(e)
            )
            raise DatabaseError(f"Failed to create task: {str(e)}") from e

    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """
        Get background task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Background task or None if not found
        """
        try:
            stmt = select(BackgroundTask).where(
                BackgroundTask.id == task_id
            ).options(
                selectinload(BackgroundTask.executions),
                selectinload(BackgroundTask.metrics)
            )

            result = await self.session.execute(stmt)
            task = result.scalar_one_or_none()

            if task:
                self.logger.debug("Retrieved background task", task_id=task_id)
            else:
                self.logger.warning("Task not found", task_id=task_id)

            return task

        except Exception as e:
            self.logger.error(
                "Failed to get background task",
                task_id=task_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to get task: {str(e)}") from e

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update task status and related fields.

        Args:
            task_id: Task identifier
            status: New task status
            progress: Optional progress update
            message: Optional status message
            result: Optional task result
            error_message: Optional error message

        Returns:
            True if update was successful
        """
        try:
            # Prepare update data
            update_data = {
                "status": TaskStatusDB(status.value),
                "updated_at": datetime.now(timezone.utc)
            }

            if progress is not None:
                update_data["progress"] = progress
            if message is not None:
                update_data["message"] = message
            if result is not None:
                update_data["result"] = result
            if error_message is not None:
                update_data["error_message"] = error_message

            # Handle status-specific timestamp updates
            if status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.now(timezone.utc)
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                update_data["completed_at"] = datetime.now(timezone.utc)

            stmt = (
                update(BackgroundTask)
                .where(BackgroundTask.id == task_id)
                .values(**update_data)
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info(
                    "Updated task status",
                    task_id=task_id,
                    status=status.value,
                    progress=progress
                )
                return True
            else:
                self.logger.warning(
                    "Task not found for status update",
                    task_id=task_id
                )
                return False

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update task status",
                task_id=task_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to update task status: {str(e)}") from e

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 50,
        offset: int = 0,
        created_since: Optional[datetime] = None
    ) -> List[BackgroundTask]:
        """
        List background tasks with optional filtering.

        Args:
            status: Filter by task status
            task_type: Filter by task type
            priority: Filter by task priority
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip
            created_since: Filter tasks created since this time

        Returns:
            List of background tasks
        """
        try:
            stmt = select(BackgroundTask)

            # Apply filters
            conditions = []
            if status:
                conditions.append(BackgroundTask.status == TaskStatusDB(status.value))
            if task_type:
                conditions.append(BackgroundTask.task_type == task_type)
            if priority:
                conditions.append(BackgroundTask.priority == TaskPriorityDB(priority.value))
            if created_since:
                conditions.append(BackgroundTask.created_at >= created_since)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Apply ordering and limits
            stmt = (
                stmt.order_by(BackgroundTask.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            tasks = result.scalars().all()

            self.logger.debug(
                "Listed background tasks",
                count=len(tasks),
                status=status.value if status else None,
                task_type=task_type
            )

            return list(tasks)

        except Exception as e:
            self.logger.error(
                "Failed to list background tasks",
                error=str(e)
            )
            raise DatabaseError(f"Failed to list tasks: {str(e)}") from e

    async def get_active_tasks(self) -> List[BackgroundTask]:
        """
        Get all currently active (running/pending) tasks.

        Returns:
            List of active background tasks
        """
        return await self.list_tasks(
            status=None,  # Will be filtered by query
            limit=1000
        )

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a background task and related data.

        Args:
            task_id: Task identifier

        Returns:
            True if deletion was successful
        """
        try:
            # Delete task (cascades to executions and metrics)
            stmt = delete(BackgroundTask).where(BackgroundTask.id == task_id)
            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info("Deleted background task", task_id=task_id)
                return True
            else:
                self.logger.warning("Task not found for deletion", task_id=task_id)
                return False

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to delete background task",
                task_id=task_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to delete task: {str(e)}") from e

    # Task Execution Operations
    async def create_task_execution(
        self,
        task_id: str,
        attempt_number: int,
        status: TaskStatus = TaskStatus.RUNNING
    ) -> TaskExecution:
        """
        Create a new task execution record.

        Args:
            task_id: Task identifier
            attempt_number: Execution attempt number
            status: Initial execution status

        Returns:
            Created task execution
        """
        try:
            execution = TaskExecution(
                task_id=task_id,
                attempt_number=attempt_number,
                status=TaskStatusDB(status.value),
                started_at=datetime.now(timezone.utc)
            )

            self.session.add(execution)
            await self.session.commit()
            await self.session.refresh(execution)

            self.logger.info(
                "Created task execution",
                execution_id=execution.id,
                task_id=task_id,
                attempt=attempt_number
            )

            return execution

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create task execution",
                task_id=task_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to create task execution: {str(e)}") from e

    # Task Metrics Operations
    async def record_task_metrics(
        self,
        task_id: str,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        progress: Optional[float] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> TaskMetrics:
        """
        Record performance metrics for a task.

        Args:
            task_id: Task identifier
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage in MB
            progress: Task progress (0-1)
            custom_metrics: Additional custom metrics

        Returns:
            Created task metrics record
        """
        try:
            metrics = TaskMetrics(
                task_id=task_id,
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory_usage,
                progress=progress,
                custom_metrics=custom_metrics or {}
            )

            self.session.add(metrics)
            await self.session.commit()
            await self.session.refresh(metrics)

            return metrics

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to record task metrics",
                task_id=task_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to record task metrics: {str(e)}") from e

    # Translation Job Operations
    async def create_translation_job(
        self,
        original_text: str,
        source_language: str,
        target_language: str,
        workflow_mode: str = "hybrid",
        poem_id: Optional[str] = None,
        original_task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TranslationJob:
        """
        Create a new translation job.

        Args:
            original_text: Original text to translate
            source_language: Source language code
            target_language: Target language code
            workflow_mode: VPSWeb workflow mode
            poem_id: Optional poem identifier
            original_task_id: Associated background task ID
            metadata: Additional metadata

        Returns:
            Created translation job
        """
        try:
            job = TranslationJob(
                original_text=original_text,
                source_language=source_language,
                target_language=target_language,
                workflow_mode=workflow_mode,
                poem_id=poem_id,
                original_task_id=original_task_id,
                metadata=metadata or {}
            )

            self.session.add(job)
            await self.session.commit()
            await self.session.refresh(job)

            self.logger.info(
                "Created translation job",
                job_id=job.id,
                source_language=source_language,
                target_language=target_language,
                workflow_mode=workflow_mode
            )

            return job

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create translation job",
                source_language=source_language,
                target_language=target_language,
                error=str(e)
            )
            raise DatabaseError(f"Failed to create translation job: {str(e)}") from e

    async def get_translation_job(self, job_id: str) -> Optional[TranslationJob]:
        """
        Get translation job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Translation job or None if not found
        """
        try:
            stmt = select(TranslationJob).where(TranslationJob.id == job_id)
            result = await self.session.execute(stmt)
            job = result.scalar_one_or_none()

            if job:
                self.logger.debug("Retrieved translation job", job_id=job_id)
            else:
                self.logger.warning("Translation job not found", job_id=job_id)

            return job

        except Exception as e:
            self.logger.error(
                "Failed to get translation job",
                job_id=job_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to get translation job: {str(e)}") from e

    async def update_translation_job(
        self,
        job_id: str,
        status: TaskStatus,
        translated_text: Optional[str] = None,
        quality_score: Optional[float] = None,
        confidence_score: Optional[float] = None,
        result_metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update translation job status and results.

        Args:
            job_id: Job identifier
            status: New job status
            translated_text: Translated text result
            quality_score: Quality assessment score
            confidence_score: Translation confidence score
            result_metadata: Result metadata
            error_message: Error message if failed

        Returns:
            True if update was successful
        """
        try:
            update_data = {
                "status": TaskStatusDB(status.value)
            }

            if translated_text is not None:
                update_data["translated_text"] = translated_text
            if quality_score is not None:
                update_data["quality_score"] = quality_score
            if confidence_score is not None:
                update_data["confidence_score"] = confidence_score
            if result_metadata is not None:
                update_data["result_metadata"] = result_metadata
            if error_message is not None:
                update_data["error_message"] = error_message

            # Handle status-specific timestamp updates
            if status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.now(timezone.utc)
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                update_data["completed_at"] = datetime.now(timezone.utc)

            stmt = (
                update(TranslationJob)
                .where(TranslationJob.id == job_id)
                .values(**update_data)
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            if result.rowcount > 0:
                self.logger.info(
                    "Updated translation job",
                    job_id=job_id,
                    status=status.value
                )
                return True
            else:
                self.logger.warning(
                    "Translation job not found for update",
                    job_id=job_id
                )
                return False

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update translation job",
                job_id=job_id,
                error=str(e)
            )
            raise DatabaseError(f"Failed to update translation job: {str(e)}") from e

    # System Metrics Operations
    async def record_system_metrics(
        self,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        disk_usage: Optional[float] = None,
        active_tasks: Optional[int] = None,
        queued_tasks: Optional[int] = None,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> SystemMetrics:
        """
        Record system performance metrics.

        Args:
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
            active_tasks: Number of active tasks
            queued_tasks: Number of queued tasks
            custom_metrics: Additional custom metrics

        Returns:
            Created system metrics record
        """
        try:
            metrics = SystemMetrics(
                cpu_usage_percent=cpu_usage,
                memory_usage_percent=memory_usage,
                disk_usage_percent=disk_usage,
                active_tasks=active_tasks,
                queued_tasks=queued_tasks,
                custom_metrics=custom_metrics or {}
            )

            self.session.add(metrics)
            await self.session.commit()
            await self.session.refresh(metrics)

            return metrics

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to record system metrics",
                error=str(e)
            )
            raise DatabaseError(f"Failed to record system metrics: {str(e)}") from e

    async def get_system_metrics(
        self,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[SystemMetrics]:
        """
        Get system metrics with optional filtering.

        Args:
            limit: Maximum number of records to return
            since: Filter metrics since this time

        Returns:
            List of system metrics
        """
        try:
            stmt = select(SystemMetrics)

            if since:
                stmt = stmt.where(SystemMetrics.timestamp >= since)

            stmt = (
                stmt.order_by(SystemMetrics.timestamp.desc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            metrics = result.scalars().all()

            return list(metrics)

        except Exception as e:
            self.logger.error(
                "Failed to get system metrics",
                error=str(e)
            )
            raise DatabaseError(f"Failed to get system metrics: {str(e)}") from e

    # Statistics and Analytics
    async def get_task_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive task statistics.

        Returns:
            Dictionary with task statistics
        """
        try:
            # Count tasks by status
            status_counts = await self.session.execute(
                select(
                    BackgroundTask.status,
                    func.count(BackgroundTask.id).label("count")
                ).group_by(BackgroundTask.status)
            )

            status_stats = {
                status.value: count for status, count in status_counts.all()
            }

            # Count tasks by type
            type_counts = await self.session.execute(
                select(
                    BackgroundTask.task_type,
                    func.count(BackgroundTask.id).label("count")
                ).group_by(BackgroundTask.task_type)
            )

            type_stats = {
                task_type: count for task_type, count in type_counts.all()
            }

            # Get average execution time for completed tasks
            avg_duration = await self.session.execute(
                select(
                    func.avg(
                        func.strftime("%s", BackgroundTask.completed_at) -
                        func.strftime("%s", BackgroundTask.started_at)
                    ).label("avg_duration")
                ).where(
                    BackgroundTask.status == TaskStatusDB.COMPLETED,
                    BackgroundTask.started_at.isnot(None),
                    BackgroundTask.completed_at.isnot(None)
                )
            )

            avg_duration_result = avg_duration.scalar()

            return {
                "status_counts": status_stats,
                "type_counts": type_stats,
                "average_duration_seconds": avg_duration_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            self.logger.error(
                "Failed to get task statistics",
                error=str(e)
            )
            raise DatabaseError(f"Failed to get task statistics: {str(e)}") from e

    async def cleanup_old_data(self, retention_hours: int = 24) -> Dict[str, int]:
        """
        Clean up old data from database.

        Args:
            retention_hours: Number of hours to retain data

        Returns:
            Dictionary with cleanup counts by table
        """
        try:
            from .models import cleanup_old_tasks

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

            # Clean up old system metrics
            metrics_stmt = delete(SystemMetrics).where(
                SystemMetrics.timestamp < cutoff_time
            )
            metrics_result = await self.session.execute(metrics_stmt)

            # Clean up old tasks (using the existing function)
            tasks_result = await cleanup_old_tasks(self.session, retention_hours)

            await self.session.commit()

            cleanup_counts = {
                "system_metrics": metrics_result.rowcount,
                "tasks": tasks_result,
                "total": metrics_result.rowcount + tasks_result
            }

            self.logger.info(
                "Completed database cleanup",
                retention_hours=retention_hours,
                cleanup_counts=cleanup_counts
            )

            return cleanup_counts

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to cleanup old data",
                error=str(e)
            )
            raise DatabaseError(f"Failed to cleanup old data: {str(e)}") from e


# Context manager for database sessions
@asynccontextmanager
async def get_repository(session: AsyncSession):
    """
    Context manager for repository access.

    Args:
        session: Database session

    Yields:
        Repository instance
    """
    repo = Repository(session)
    try:
        yield repo
    finally:
        pass  # Session is managed by caller