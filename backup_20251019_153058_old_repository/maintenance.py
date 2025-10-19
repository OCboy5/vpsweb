"""
Database Maintenance and Cleanup Routines for VPSWeb Repository System

This module provides comprehensive database maintenance utilities including
cleanup routines, performance optimization, data archiving, and health monitoring.

Features:
- Automated cleanup of expired and orphaned data
- Database performance optimization routines
- Data archiving and purging strategies
- Comprehensive health monitoring and reporting
- Scheduled maintenance task management
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
import json

from sqlalchemy import text, func, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models import (
    Poem, Translation, AiLog, HumanNote
)
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


@dataclass
class CleanupConfig:
    """
    Configuration for database cleanup operations.

    Defines retention periods, cleanup strategies, and operational
    parameters for maintenance tasks.
    """

    # Data retention periods (in days)
    ai_log_retention_days: int = 90
    temp_translation_retention_days: int = 30
    audit_log_retention_days: int = 365

    # Cleanup thresholds
    max_orphaned_records: int = 1000
    cleanup_batch_size: int = 500

    # Performance settings
    max_vacuum_duration_minutes: int = 30
    analyze_threshold_percent: int = 10

    # Safety settings
    require_backup: bool = True
    dry_run: bool = False
    confirm_destructive: bool = False

    # Archive settings
    enable_archiving: bool = True
    archive_path: str = "archives"
    compress_archives: bool = True

    @classmethod
    def for_development(cls) -> 'CleanupConfig':
        """Create development-friendly cleanup configuration."""
        return cls(
            ai_log_retention_days=7,
            temp_translation_retention_days=3,
            audit_log_retention_days=30,
            max_orphaned_records=100,
            cleanup_batch_size=50,
            require_backup=False,
            dry_run=True,
        )

    @classmethod
    def for_production(cls) -> 'CleanupConfig':
        """Create production-safe cleanup configuration."""
        return cls(
            ai_log_retention_days=90,
            temp_translation_retention_days=30,
            audit_log_retention_days=365,
            max_orphaned_records=1000,
            cleanup_batch_size=500,
            require_backup=True,
            dry_run=False,
            confirm_destructive=True,
        )


@dataclass
class CleanupResult:
    """Results from a cleanup operation."""

    operation: str
    records_processed: int
    records_deleted: int
    records_archived: int
    errors: List[str]
    duration_seconds: float
    space_freed_mb: Optional[float] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


class DataArchiver:
    """
    Handles archiving of old data before deletion.

    Provides configurable archiving strategies with compression
    and metadata tracking.
    """

    def __init__(self, config: CleanupConfig):
        """
        Initialize the data archiver.

        Args:
            config: Cleanup configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DataArchiver")
        self.archive_path = Path(config.archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    async def archive_ai_logs(self, session: AsyncSession, cutoff_date: datetime) -> CleanupResult:
        """
        Archive old AI logs before deletion.

        Args:
            session: Database session
            cutoff_date: Cutoff date for archiving

        Returns:
            Archive operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_archived = 0
        errors = []

        try:
            # Query old AI logs
            query = text("""
                SELECT id, created_at, updated_at, provider, model_name,
                       workflow_mode, status, duration_seconds, total_tokens,
                       cost, error_message, metadata_json
                FROM ai_logs
                WHERE created_at < :cutoff_date
                ORDER BY created_at
                LIMIT :batch_size
            """)

            while True:
                result = await session.execute(
                    query,
                    {"cutoff_date": cutoff_date, "batch_size": self.config.cleanup_batch_size}
                )
                rows = result.fetchall()

                if not rows:
                    break

                # Prepare archive data
                archive_data = []
                for row in rows:
                    archive_data.append({
                        "id": row.id,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "provider": row.provider,
                        "model_name": row.model_name,
                        "workflow_mode": row.workflow_mode,
                        "status": row.status,
                        "duration_seconds": row.duration_seconds,
                        "total_tokens": row.total_tokens,
                        "cost": float(row.cost),
                        "error_message": row.error_message,
                        "metadata_json": row.metadata_json,
                    })

                # Write to archive file
                if archive_data:
                    archive_file = self.archive_path / f"ai_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{records_archived}.json"

                    if self.config.compress_archives:
                        import gzip
                        with gzip.open(f"{archive_file}.gz", 'wt', encoding='utf-8') as f:
                            json.dump(archive_data, f, indent=2)
                        archive_file = f"{archive_file}.gz"
                    else:
                        with open(archive_file, 'w', encoding='utf-8') as f:
                            json.dump(archive_data, f, indent=2)

                    records_archived += len(archive_data)
                    records_processed += len(archive_data)

                self.logger.info(f"Archived {len(archive_data)} AI logs to {archive_file}")

                # Commit the transaction
                await session.commit()

        except Exception as e:
            errors.append(f"Archive AI logs failed: {str(e)}")
            self.logger.error(f"AI log archiving error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="archive_ai_logs",
            records_processed=records_processed,
            records_deleted=0,
            records_archived=records_archived,
            errors=errors,
            duration_seconds=duration
        )

    async def archive_translations(self, session: AsyncSession, cutoff_date: datetime) -> CleanupResult:
        """
        Archive old temporary translations.

        Args:
            session: Database session
            cutoff_date: Cutoff date for archiving

        Returns:
            Archive operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_archived = 0
        errors = []

        try:
            # Query old temporary translations
            query = text("""
                SELECT t.id, t.poem_id, t.version, t.target_language,
                       t.translator_type, t.quality_score, t.is_published,
                       t.created_at, t.updated_at, t.translation_text,
                       t.metadata_json, p.poet_name, p.poem_title
                FROM translations t
                JOIN poems p ON t.poem_id = p.id
                WHERE t.created_at < :cutoff_date
                AND t.is_published = false
                ORDER BY t.created_at
                LIMIT :batch_size
            """)

            while True:
                result = await session.execute(
                    query,
                    {"cutoff_date": cutoff_date, "batch_size": self.config.cleanup_batch_size}
                )
                rows = result.fetchall()

                if not rows:
                    break

                # Prepare archive data
                archive_data = []
                for row in rows:
                    archive_data.append({
                        "id": row.id,
                        "poem_id": row.poem_id,
                        "version": row.version,
                        "target_language": row.target_language,
                        "translator_type": row.translator_type,
                        "quality_score": float(row.quality_score) if row.quality_score else None,
                        "is_published": row.is_published,
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat(),
                        "translation_text": row.translation_text,
                        "metadata_json": row.metadata_json,
                        "poet_name": row.poet_name,
                        "poem_title": row.poem_title,
                    })

                # Write to archive file
                if archive_data:
                    archive_file = self.archive_path / f"translations_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{records_archived}.json"

                    if self.config.compress_archives:
                        import gzip
                        with gzip.open(f"{archive_file}.gz", 'wt', encoding='utf-8') as f:
                            json.dump(archive_data, f, indent=2)
                        archive_file = f"{archive_file}.gz"
                    else:
                        with open(archive_file, 'w', encoding='utf-8') as f:
                            json.dump(archive_data, f, indent=2)

                    records_archived += len(archive_data)
                    records_processed += len(archive_data)

                self.logger.info(f"Archived {len(archive_data)} translations to {archive_file}")

                await session.commit()

        except Exception as e:
            errors.append(f"Archive translations failed: {str(e)}")
            self.logger.error(f"Translation archiving error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="archive_translations",
            records_processed=records_processed,
            records_deleted=0,
            records_archived=records_archived,
            errors=errors,
            duration_seconds=duration
        )


class DatabaseCleaner:
    """
    Performs database cleanup operations according to configuration.

    Handles safe deletion of expired data, orphaned records, and
    performance optimization tasks.
    """

    def __init__(self, config: CleanupConfig):
        """
        Initialize the database cleaner.

        Args:
            config: Cleanup configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.DatabaseCleaner")
        self.archiver = DataArchiver(config) if config.enable_archiving else None

    async def cleanup_ai_logs(self, session: AsyncSession) -> CleanupResult:
        """
        Clean up old AI logs according to retention policy.

        Args:
            session: Database session

        Returns:
            Cleanup operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_deleted = 0
        errors = []

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.ai_log_retention_days)

            # Archive first if enabled
            if self.archiver:
                archive_result = await self.archiver.archive_ai_logs(session, cutoff_date)
                records_processed += archive_result.records_processed
                errors.extend(archive_result.errors)

            # Delete old AI logs
            while True:
                delete_query = text("""
                    DELETE FROM ai_logs
                    WHERE created_at < :cutoff_date
                    LIMIT :batch_size
                """)

                result = await session.execute(
                    delete_query,
                    {"cutoff_date": cutoff_date, "batch_size": self.config.cleanup_batch_size}
                )

                deleted_count = result.rowcount
                records_deleted += deleted_count
                records_processed += deleted_count

                if deleted_count == 0:
                    break

                await session.commit()
                self.logger.info(f"Deleted {deleted_count} old AI logs")

        except Exception as e:
            errors.append(f"Cleanup AI logs failed: {str(e)}")
            self.logger.error(f"AI log cleanup error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="cleanup_ai_logs",
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=0,
            errors=errors,
            duration_seconds=duration
        )

    async def cleanup_temp_translations(self, session: AsyncSession) -> CleanupResult:
        """
        Clean up old temporary/unpublished translations.

        Args:
            session: Database session

        Returns:
            Cleanup operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_deleted = 0
        errors = []

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.temp_translation_retention_days)

            # Archive first if enabled
            if self.archiver:
                archive_result = await self.archiver.archive_translations(session, cutoff_date)
                records_processed += archive_result.records_processed
                errors.extend(archive_result.errors)

            # Delete old temporary translations
            while True:
                delete_query = text("""
                    DELETE FROM translations
                    WHERE created_at < :cutoff_date
                    AND is_published = false
                    LIMIT :batch_size
                """)

                result = await session.execute(
                    delete_query,
                    {"cutoff_date": cutoff_date, "batch_size": self.config.cleanup_batch_size}
                )

                deleted_count = result.rowcount
                records_deleted += deleted_count
                records_processed += deleted_count

                if deleted_count == 0:
                    break

                await session.commit()
                self.logger.info(f"Deleted {deleted_count} old temporary translations")

        except Exception as e:
            errors.append(f"Cleanup temp translations failed: {str(e)}")
            self.logger.error(f"Temp translation cleanup error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="cleanup_temp_translations",
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=0,
            errors=errors,
            duration_seconds=duration
        )

    async def cleanup_orphaned_records(self, session: AsyncSession) -> CleanupResult:
        """
        Clean up orphaned records and maintain referential integrity.

        Args:
            session: Database session

        Returns:
            Cleanup operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_deleted = 0
        errors = []

        try:
            # Find and clean orphaned human notes (notes without existing poems)
            orphaned_notes_query = text("""
                DELETE FROM human_notes
                WHERE poem_id NOT IN (SELECT id FROM poems)
                LIMIT :batch_size
            """)

            while True:
                result = await session.execute(
                    orphaned_notes_query,
                    {"batch_size": self.config.cleanup_batch_size}
                )

                deleted_count = result.rowcount
                records_deleted += deleted_count
                records_processed += deleted_count

                if deleted_count == 0:
                    break

                await session.commit()
                self.logger.info(f"Deleted {deleted_count} orphaned human notes")

        except Exception as e:
            errors.append(f"Cleanup orphaned records failed: {str(e)}")
            self.logger.error(f"Orphaned records cleanup error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="cleanup_orphaned_records",
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=0,
            errors=errors,
            duration_seconds=duration
        )

    async def optimize_database(self, session: AsyncSession) -> CleanupResult:
        """
        Perform database optimization operations.

        Args:
            session: Database session

        Returns:
            Optimization operation result
        """
        start_time = datetime.now()
        records_processed = 0
        records_deleted = 0
        errors = []
        recommendations = []

        try:
            # Update table statistics
            if "sqlite" in session.bind.url.drivername:
                # SQLite optimization
                await session.execute(text("ANALYZE"))
                await session.execute(text("VACUUM"))
                recommendations.append("SQLite ANALYZE and VACUUM completed")

            elif "postgresql" in session.bind.url.drivername:
                # PostgreSQL optimization
                await session.execute(text("ANALYZE"))
                recommendations.append("PostgreSQL ANALYZE completed")

                # Update table statistics for better query planning
                tables = ["poems", "translations", "ai_logs", "human_notes"]
                for table in tables:
                    try:
                        await session.execute(text(f"ANALYZE {table}"))
                    except Exception as e:
                        self.logger.warning(f"Failed to analyze {table}: {e}")

            await session.commit()
            records_processed = 1  # Mark as processed

        except Exception as e:
            errors.append(f"Database optimization failed: {str(e)}")
            self.logger.error(f"Database optimization error: {e}")

        duration = (datetime.now() - start_time).total_seconds()

        return CleanupResult(
            operation="optimize_database",
            records_processed=records_processed,
            records_deleted=records_deleted,
            records_archived=0,
            errors=errors,
            duration_seconds=duration,
            recommendations=recommendations
        )


class MaintenanceScheduler:
    """
    Schedules and manages database maintenance tasks.

    Provides automated maintenance scheduling with configurable
    intervals and comprehensive logging.
    """

    def __init__(self, config: CleanupConfig):
        """
        Initialize the maintenance scheduler.

        Args:
            config: Cleanup configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.MaintenanceScheduler")
        self.cleaner = DatabaseCleaner(config)

    async def run_daily_maintenance(self) -> Dict[str, CleanupResult]:
        """
        Run daily maintenance tasks.

        Returns:
            Dictionary of maintenance operation results
        """
        self.logger.info("Starting daily database maintenance")

        results = {}

        async with get_session() as session:
            # Clean up old AI logs
            if not self.config.dry_run:
                results["ai_logs"] = await self.cleaner.cleanup_ai_logs(session)
            else:
                self.logger.info("DRY RUN: Skipping AI log cleanup")

            # Clean up temporary translations
            if not self.config.dry_run:
                results["temp_translations"] = await self.cleaner.cleanup_temp_translations(session)
            else:
                self.logger.info("DRY RUN: Skipping temp translation cleanup")

            # Clean up orphaned records
            if not self.config.dry_run:
                results["orphaned_records"] = await self.cleaner.cleanup_orphaned_records(session)
            else:
                self.logger.info("DRY RUN: Skipping orphaned records cleanup")

        self.logger.info(f"Daily maintenance completed. Operations: {list(results.keys())}")
        return results

    async def run_weekly_maintenance(self) -> Dict[str, CleanupResult]:
        """
        Run weekly maintenance tasks.

        Returns:
            Dictionary of maintenance operation results
        """
        self.logger.info("Starting weekly database maintenance")

        results = await self.run_daily_maintenance()

        async with get_session() as session:
            # Database optimization
            if not self.config.dry_run:
                results["optimization"] = await self.cleaner.optimize_database(session)
            else:
                self.logger.info("DRY RUN: Skipping database optimization")

        self.logger.info(f"Weekly maintenance completed. Operations: {list(results.keys())}")
        return results

    async def generate_maintenance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive maintenance report.

        Returns:
            Maintenance report with statistics and recommendations
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "configuration": {
                "ai_log_retention_days": self.config.ai_log_retention_days,
                "temp_translation_retention_days": self.config.temp_translation_retention_days,
                "cleanup_batch_size": self.config.cleanup_batch_size,
                "dry_run": self.config.dry_run,
                "archiving_enabled": self.config.enable_archiving,
            },
            "database_statistics": {},
            "recommendations": [],
        }

        try:
            async with get_session() as session:
                # Get table statistics
                tables_query = text("""
                    SELECT name, sql FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)

                if "sqlite" in session.bind.url.drivername:
                    result = await session.execute(tables_query)
                    tables = result.fetchall()

                    for table in tables:
                        count_query = text(f"SELECT COUNT(*) FROM {table.name}")
                        count_result = await session.execute(count_query)
                        count = count_result.scalar()

                        report["database_statistics"][table.name] = {
                            "record_count": count,
                            "schema": table.sql
                        }

                # Get database size
                if "sqlite" in session.bind.url.drivername:
                    size_query = text("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                    size_result = await session.execute(size_query)
                    size_bytes = size_result.scalar()
                    size_mb = size_bytes / (1024 * 1024)

                    report["database_statistics"]["database_size_mb"] = round(size_mb, 2)

        except Exception as e:
            self.logger.error(f"Failed to generate maintenance report: {e}")
            report["error"] = str(e)

        return report


# Convenience functions for maintenance operations
async def run_database_maintenance(
    config: Optional[CleanupConfig] = None,
    maintenance_type: str = "daily"
) -> Dict[str, CleanupResult]:
    """
    Run database maintenance with specified configuration.

    Args:
        config: Optional cleanup configuration
        maintenance_type: Type of maintenance (daily, weekly)

    Returns:
        Maintenance operation results
    """
    if config is None:
        config = CleanupConfig.for_development()

    scheduler = MaintenanceScheduler(config)

    if maintenance_type == "weekly":
        return await scheduler.run_weekly_maintenance()
    else:
        return await scheduler.run_daily_maintenance()


async def get_maintenance_report(
    config: Optional[CleanupConfig] = None
) -> Dict[str, Any]:
    """
    Generate maintenance report.

    Args:
        config: Optional cleanup configuration

    Returns:
        Maintenance report
    """
    if config is None:
        config = CleanupConfig.for_development()

    scheduler = MaintenanceScheduler(config)
    return await scheduler.generate_maintenance_report()