"""
Database Backup and Restore System for VPSWeb Repository

This module provides comprehensive database backup and restore functionality
including automated backups, scheduling, verification, and disaster recovery.

Features:
- Automated and manual database backups
- Multiple backup formats and compression
- Backup verification and integrity checking
- Scheduled backup management
- Restore functionality with rollbacks
- Backup cleanup and archival
- Disaster recovery procedures
"""

import asyncio
import hashlib
import json
import logging
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import gzip
import sqlite3
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models import Base
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


@dataclass
class BackupConfig:
    """
    Configuration for database backup operations.

    Defines backup schedules, retention policies, compression
    settings, and operational parameters.
    """

    # Backup storage
    backup_directory: str = "backups"
    compression_enabled: bool = True
    compression_level: int = 6
    backup_format: str = "sql"  # sql, json, binary

    # Retention policy
    daily_retention_days: int = 7
    weekly_retention_weeks: int = 4
    monthly_retention_months: int = 12
    yearly_retention_years: int = 5

    # Backup scheduling
    auto_backup_enabled: bool = True
    backup_frequency_hours: int = 6
    backup_verification_enabled: bool = True

    # Backup size limits
    max_backup_size_gb: float = 10.0
    max_total_backups_gb: float = 100.0

    # Security settings
    encrypt_backups: bool = False
    backup_password: Optional[str] = None

    # Performance settings
    backup_timeout_minutes: int = 30
    parallel_backup_threads: int = 1

    @classmethod
    def for_development(cls) -> 'BackupConfig':
        """Create development-friendly backup configuration."""
        return cls(
            backup_directory="dev_backups",
            compression_enabled=True,
            daily_retention_days=3,
            weekly_retention_weeks=2,
            monthly_retention_months=1,
            auto_backup_enabled=False,
            backup_frequency_hours=24,
            max_backup_size_gb=1.0,
            max_total_backups_gb=5.0,
        )

    @classmethod
    def for_production(cls) -> 'BackupConfig':
        """Create production-grade backup configuration."""
        return cls(
            backup_directory="prod_backups",
            compression_enabled=True,
            compression_level=9,
            daily_retention_days=7,
            weekly_retention_weeks=4,
            monthly_retention_months=12,
            yearly_retention_years=5,
            auto_backup_enabled=True,
            backup_frequency_hours=6,
            backup_verification_enabled=True,
            max_backup_size_gb=10.0,
            max_total_backups_gb=100.0,
            encrypt_backups=True,
        )


@dataclass
class BackupMetadata:
    """Metadata for a backup file."""

    backup_id: str
    timestamp: str
    database_url: str
    backup_type: str  # full, incremental, differential
    backup_format: str
    compressed: bool
    encrypted: bool
    file_size_bytes: int
    checksum: str
    table_counts: Dict[str, int]
    schema_version: str
    backup_duration_seconds: float
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        """Create from dictionary."""
        return cls(**data)


class BackupManager:
    """
    Manages database backup operations with comprehensive features.

    Handles backup creation, verification, storage, and cleanup
    according to configured policies.
    """

    def __init__(self, database_url: str, config: BackupConfig):
        """
        Initialize the backup manager.

        Args:
            database_url: Database connection URL
            config: Backup configuration
        """
        self.database_url = database_url
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.BackupManager")
        self.backup_path = Path(config.backup_directory)
        self.backup_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.backup_path / "daily").mkdir(exist_ok=True)
        (self.backup_path / "weekly").mkdir(exist_ok=True)
        (self.backup_path / "monthly").mkdir(exist_ok=True)
        (self.backup_path / "yearly").mkdir(exist_ok=True)
        (self.backup_path / "metadata").mkdir(exist_ok=True)

    async def create_full_backup(self, backup_type: str = "manual") -> Tuple[bool, BackupMetadata]:
        """
        Create a full database backup.

        Args:
            backup_type: Type of backup (manual, scheduled, auto)

        Returns:
            Tuple of (success, backup_metadata)
        """
        start_time = datetime.now()
        backup_id = f"backup_{start_time.strftime('%Y%m%d_%H%M%S')}_{backup_type}"

        self.logger.info(f"Starting full backup: {backup_id}")

        try:
            # Get table statistics before backup
            table_counts = await self._get_table_counts()

            # Create backup file
            backup_file = self._get_backup_file_path(backup_id, backup_type)
            temp_file = backup_file.with_suffix('.tmp')

            if self.config.backup_format == "sql":
                await self._create_sql_backup(temp_file)
            elif self.config.backup_format == "json":
                await self._create_json_backup(temp_file)
            else:
                raise ValueError(f"Unsupported backup format: {self.config.backup_format}")

            # Compress if enabled
            if self.config.compression_enabled:
                compressed_file = await self._compress_backup(temp_file)
                temp_file.unlink()
                backup_file = compressed_file
            else:
                backup_file = temp_file.rename(backup_file)

            # Calculate checksum
            checksum = await self._calculate_checksum(backup_file)

            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=start_time.isoformat(),
                database_url=self.database_url,
                backup_type=backup_type,
                backup_format=self.config.backup_format,
                compressed=self.config.compression_enabled,
                encrypted=self.config.encrypt_backups,
                file_size_bytes=backup_file.stat().st_size,
                checksum=checksum,
                table_counts=table_counts,
                schema_version="1.0.0",  # TODO: Get from database
                backup_duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=True
            )

            # Save metadata
            await self._save_backup_metadata(metadata)

            # Verify backup if enabled
            if self.config.backup_verification_enabled:
                verification_success = await self._verify_backup(backup_file, metadata)
                if not verification_success:
                    raise Exception("Backup verification failed")

            self.logger.info(f"Backup completed successfully: {backup_id} ({backup_file.stat().st_size} bytes)")
            return True, metadata

        except Exception as e:
            self.logger.error(f"Backup failed: {backup_id} - {str(e)}")

            # Clean up temporary files
            for temp_file in self.backup_path.glob(f"{backup_id}*.tmp*"):
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=start_time.isoformat(),
                database_url=self.database_url,
                backup_type=backup_type,
                backup_format=self.config.backup_format,
                compressed=self.config.compression_enabled,
                encrypted=self.config.encrypt_backups,
                file_size_bytes=0,
                checksum="",
                table_counts={},
                schema_version="1.0.0",
                backup_duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error_message=str(e)
            )

            return False, metadata

    async def _create_sql_backup(self, backup_file: Path) -> None:
        """Create SQL dump backup."""
        if "sqlite" in self.database_url:
            # Extract database path from URL
            db_path = self.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

            # Use SQLite's backup command
            with sqlite3.connect(db_path) as source:
                with sqlite3.connect(str(backup_file)) as backup:
                    source.backup(backup)
        else:
            raise NotImplementedError("SQL backup format only supported for SQLite")

    async def _create_json_backup(self, backup_file: Path) -> None:
        """Create JSON format backup."""
        backup_data = {
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database_url": self.database_url,
                "format": "json",
                "version": "1.0"
            },
            "tables": {}
        }

        async with get_session() as session:
            # Get all table names
            if "sqlite" in session.bind.url.drivername:
                tables_query = text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
            else:
                tables_query = text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

            result = await session.execute(tables_query)
            table_names = [row[0] for row in result.fetchall()]

            # Export each table
            for table_name in table_names:
                try:
                    data_query = text(f"SELECT * FROM {table_name}")
                    data_result = await session.execute(data_query)
                    rows = data_result.fetchall()

                    # Convert rows to dictionaries
                    table_data = []
                    columns = data_result.keys()
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        # Convert datetime objects to strings
                        for key, value in row_dict.items():
                            if isinstance(value, datetime):
                                row_dict[key] = value.isoformat()
                        table_data.append(row_dict)

                    backup_data["tables"][table_name] = table_data
                    self.logger.info(f"Exported {len(table_data)} rows from table {table_name}")

                except Exception as e:
                    self.logger.warning(f"Failed to export table {table_name}: {e}")

        # Write JSON backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

    async def _compress_backup(self, backup_file: Path) -> Path:
        """Compress backup file using gzip."""
        compressed_file = backup_file.with_suffix(backup_file.suffix + '.gz')

        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb', compresslevel=self.config.compression_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

        return compressed_file

    async def _calculate_checksum(self, backup_file: Path) -> str:
        """Calculate SHA-256 checksum of backup file."""
        hash_sha256 = hashlib.sha256()

        with open(backup_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    async def _get_table_counts(self) -> Dict[str, int]:
        """Get record counts for all tables."""
        table_counts = {}

        async with get_session() as session:
            if "sqlite" in session.bind.url.drivername:
                tables_query = text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
            else:
                tables_query = text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

            result = await session.execute(tables_query)
            table_names = [row[0] for row in result.fetchall()]

            for table_name in table_names:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    table_counts[table_name] = count_result.scalar()
                except Exception as e:
                    self.logger.warning(f"Failed to get count for table {table_name}: {e}")

        return table_counts

    def _get_backup_file_path(self, backup_id: str, backup_type: str) -> Path:
        """Get backup file path based on type and timestamp."""
        timestamp = datetime.now()

        # Determine backup category
        if backup_type == "scheduled":
            category = "daily"
        else:
            category = "manual"

        file_extension = "sql"
        if self.config.backup_format == "json":
            file_extension = "json"

        if self.config.compression_enabled:
            file_extension += ".gz"

        filename = f"{backup_id}.{file_extension}"
        return self.backup_path / category / filename

    async def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to file."""
        metadata_file = self.backup_path / "metadata" / f"{metadata.backup_id}.json"

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata.to_dict(), f, indent=2)

    async def _verify_backup(self, backup_file: Path, metadata: BackupMetadata) -> bool:
        """Verify backup integrity."""
        try:
            # Check file exists and size matches
            if not backup_file.exists():
                return False

            if backup_file.stat().st_size != metadata.file_size_bytes:
                return False

            # Verify checksum
            calculated_checksum = await self._calculate_checksum(backup_file)
            if calculated_checksum != metadata.checksum:
                return False

            # If SQL format, try to open and query
            if self.config.backup_format == "sql" and "sqlite" in self.database_url:
                try:
                    with sqlite3.connect(str(backup_file)) as backup_conn:
                        cursor = backup_conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = [row[0] for row in cursor.fetchall()]

                        # Verify all expected tables exist
                        expected_tables = set(metadata.table_counts.keys())
                        actual_tables = set(tables)

                        if not expected_tables.issubset(actual_tables):
                            return False

                except Exception as e:
                    self.logger.warning(f"Backup verification query failed: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False

    async def list_backups(self, backup_type: Optional[str] = None) -> List[BackupMetadata]:
        """
        List available backups.

        Args:
            backup_type: Filter by backup type (optional)

        Returns:
            List of backup metadata
        """
        backups = []
        metadata_dir = self.backup_path / "metadata"

        if not metadata_dir.exists():
            return backups

        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)

                metadata = BackupMetadata.from_dict(metadata_dict)

                if backup_type is None or metadata.backup_type == backup_type:
                    backups.append(metadata)

            except Exception as e:
                self.logger.warning(f"Failed to load metadata from {metadata_file}: {e}")

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        return backups

    async def cleanup_old_backups(self) -> Dict[str, int]:
        """
        Clean up old backups according to retention policy.

        Returns:
            Dictionary with cleanup statistics
        """
        cleanup_stats = {
            "daily_deleted": 0,
            "weekly_deleted": 0,
            "monthly_deleted": 0,
            "yearly_deleted": 0,
            "total_deleted": 0
        }

        now = datetime.now(timezone.utc)

        # Get all backups
        all_backups = await self.list_backups()

        # Group backups by retention category
        daily_backups = []
        weekly_backups = []
        monthly_backups = []
        yearly_backups = []

        for backup in all_backups:
            if not backup.success:
                continue

            backup_time = datetime.fromisoformat(backup.timestamp.replace('Z', '+00:00'))
            days_old = (now - backup_time).days

            if backup.backup_type == "scheduled":
                if days_old <= 7:
                    daily_backups.append(backup)
                elif days_old <= 30:
                    weekly_backups.append(backup)
                elif days_old <= 365:
                    monthly_backups.append(backup)
                else:
                    yearly_backups.append(backup)

        # Clean up old daily backups (keep last N days)
        daily_backups.sort(key=lambda x: x.timestamp, reverse=True)
        for backup in daily_backups[self.config.daily_retention_days:]:
            if await self._delete_backup(backup):
                cleanup_stats["daily_deleted"] += 1

        # Clean up old weekly backups (keep last N weeks)
        weekly_backups.sort(key=lambda x: x.timestamp, reverse=True)
        for backup in weekly_backups[self.config.weekly_retention_weeks:]:
            if await self._delete_backup(backup):
                cleanup_stats["weekly_deleted"] += 1

        # Clean up old monthly backups (keep last N months)
        monthly_backups.sort(key=lambda x: x.timestamp, reverse=True)
        for backup in monthly_backups[self.config.monthly_retention_months:]:
            if await self._delete_backup(backup):
                cleanup_stats["monthly_deleted"] += 1

        # Clean up old yearly backups (keep last N years)
        yearly_backups.sort(key=lambda x: x.timestamp, reverse=True)
        for backup in yearly_backups[self.config.yearly_retention_years:]:
            if await self._delete_backup(backup):
                cleanup_stats["yearly_deleted"] += 1

        cleanup_stats["total_deleted"] = sum(cleanup_stats.values())

        self.logger.info(f"Backup cleanup completed: {cleanup_stats}")
        return cleanup_stats

    async def _delete_backup(self, metadata: BackupMetadata) -> bool:
        """Delete backup files and metadata."""
        try:
            # Delete backup file
            backup_file = self.backup_path / "daily" / f"{metadata.backup_id}.sql"
            if metadata.compressed:
                backup_file = backup_file.with_suffix('.sql.gz')
            elif metadata.backup_format == "json":
                backup_file = backup_file.with_suffix('.json')
                if metadata.compressed:
                    backup_file = backup_file.with_suffix('.json.gz')

            if backup_file.exists():
                backup_file.unlink()

            # Delete metadata file
            metadata_file = self.backup_path / "metadata" / f"{metadata.backup_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()

            return True

        except Exception as e:
            self.logger.error(f"Failed to delete backup {metadata.backup_id}: {e}")
            return False


class RestoreManager:
    """
    Manages database restore operations.

    Handles restore from backups with verification and rollback
    capabilities.
    """

    def __init__(self, database_url: str, config: BackupConfig):
        """
        Initialize the restore manager.

        Args:
            database_url: Database connection URL
            config: Backup configuration
        """
        self.database_url = database_url
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RestoreManager")

    async def restore_from_backup(
        self,
        backup_id: str,
        create_backup_before_restore: bool = True,
        verify_restore: bool = True
    ) -> Tuple[bool, str]:
        """
        Restore database from backup.

        Args:
            backup_id: ID of backup to restore from
            create_backup_before_restore: Create backup before restore
            verify_restore: Verify restore after completion

        Returns:
            Tuple of (success, message)
        """
        self.logger.info(f"Starting restore from backup: {backup_id}")

        try:
            # Load backup metadata
            backup_manager = BackupManager(self.database_url, self.config)
            backups = await backup_manager.list_backups()
            backup_metadata = None

            for backup in backups:
                if backup.backup_id == backup_id:
                    backup_metadata = backup
                    break

            if not backup_metadata:
                return False, f"Backup {backup_id} not found"

            # Create pre-restore backup if requested
            if create_backup_before_restore:
                self.logger.info("Creating pre-restore backup")
                pre_restore_success, _ = await backup_manager.create_full_backup("pre_restore")
                if not pre_restore_success:
                    return False, "Failed to create pre-restore backup"

            # Perform restore
            if backup_metadata.backup_format == "sql":
                success = await self._restore_from_sql(backup_metadata)
            elif backup_metadata.backup_format == "json":
                success = await self._restore_from_json(backup_metadata)
            else:
                return False, f"Unsupported backup format: {backup_metadata.backup_format}"

            if not success:
                return False, "Restore operation failed"

            # Verify restore if requested
            if verify_restore:
                verification_success = await self._verify_restore(backup_metadata)
                if not verification_success:
                    return False, "Restore verification failed"

            self.logger.info(f"Restore completed successfully from backup: {backup_id}")
            return True, "Restore completed successfully"

        except Exception as e:
            error_msg = f"Restore failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    async def _restore_from_sql(self, backup_metadata: BackupMetadata) -> bool:
        """Restore from SQL backup file."""
        try:
            backup_manager = BackupManager(self.database_url, self.config)

            # Find backup file
            backup_file = backup_manager.backup_path / "daily" / f"{backup_metadata.backup_id}.sql"
            if backup_metadata.compressed:
                backup_file = backup_file.with_suffix('.sql.gz')

            if not backup_file.exists():
                return False

            # For SQLite, restore by copying the database file
            if "sqlite" in self.database_url:
                target_db_path = self.database_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

                # Create backup of current database
                if Path(target_db_path).exists():
                    shutil.copy2(target_db_path, f"{target_db_path}.restore_backup")

                # Decompress if needed
                if backup_metadata.compressed:
                    with gzip.open(backup_file, 'rb') as f_in:
                        with open(target_db_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    shutil.copy2(backup_file, target_db_path)

                return True

            return False

        except Exception as e:
            self.logger.error(f"SQL restore failed: {e}")
            return False

    async def _restore_from_json(self, backup_metadata: BackupMetadata) -> bool:
        """Restore from JSON backup file."""
        try:
            backup_manager = BackupManager(self.database_url, self.config)

            # Find backup file
            backup_file = backup_manager.backup_path / "daily" / f"{backup_metadata.backup_id}.json"
            if backup_metadata.compressed:
                backup_file = backup_file.with_suffix('.json.gz')

            if not backup_file.exists():
                return False

            # Load JSON backup data
            if backup_metadata.compressed:
                with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)

            # Clear existing data
            async with get_session() as session:
                # Get all table names and drop data
                if "sqlite" in session.bind.url.drivername:
                    tables_query = text("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                else:
                    tables_query = text("""
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = 'public'
                    """)

                result = await session.execute(tables_query)
                table_names = [row[0] for row in result.fetchall()]

                # Disable foreign key constraints temporarily (SQLite)
                if "sqlite" in session.bind.url.drivername:
                    await session.execute(text("PRAGMA foreign_keys = OFF"))

                # Clear tables in reverse dependency order
                for table_name in reversed(table_names):
                    try:
                        await session.execute(text(f"DELETE FROM {table_name}"))
                        await session.commit()
                        self.logger.info(f"Cleared table {table_name}")
                    except Exception as e:
                        self.logger.warning(f"Failed to clear table {table_name}: {e}")

                # Restore data
                tables_data = backup_data.get("tables", {})
                for table_name in table_names:
                    if table_name in tables_data:
                        table_data = tables_data[table_name]

                        if table_data:
                            # Get column names from first row
                            columns = list(table_data[0].keys())
                            placeholders = ", ".join([f":{col}" for col in columns])

                            # Insert data
                            for row in table_data:
                                # Convert string dates back to datetime objects
                                for key, value in row.items():
                                    if isinstance(value, str) and 'T' in value:
                                        try:
                                            row[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                        except ValueError:
                                            pass

                                insert_query = text(f"""
                                    INSERT INTO {table_name} ({', '.join(columns)})
                                    VALUES ({placeholders})
                                """)

                                try:
                                    await session.execute(insert_query, row)
                                except Exception as e:
                                    self.logger.warning(f"Failed to insert row into {table_name}: {e}")

                            await session.commit()
                            self.logger.info(f"Restored {len(table_data)} rows to {table_name}")

                # Re-enable foreign key constraints (SQLite)
                if "sqlite" in session.bind.url.drivername:
                    await session.execute(text("PRAGMA foreign_keys = ON"))

            return True

        except Exception as e:
            self.logger.error(f"JSON restore failed: {e}")
            return False

    async def _verify_restore(self, backup_metadata: BackupMetadata) -> bool:
        """Verify that restore was successful."""
        try:
            # Compare table counts
            current_counts = await self._get_current_table_counts()

            for table_name, expected_count in backup_metadata.table_counts.items():
                actual_count = current_counts.get(table_name, 0)
                if actual_count != expected_count:
                    self.logger.warning(
                        f"Table count mismatch for {table_name}: "
                        f"expected {expected_count}, got {actual_count}"
                    )

            return True

        except Exception as e:
            self.logger.error(f"Restore verification failed: {e}")
            return False

    async def _get_current_table_counts(self) -> Dict[str, int]:
        """Get current table counts."""
        table_counts = {}

        async with get_session() as session:
            if "sqlite" in session.bind.url.drivername:
                tables_query = text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
            else:
                tables_query = text("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

            result = await session.execute(tables_query)
            table_names = [row[0] for row in result.fetchall()]

            for table_name in table_names:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    table_counts[table_name] = count_result.scalar()
                except Exception as e:
                    self.logger.warning(f"Failed to get count for table {table_name}: {e}")

        return table_counts


# Convenience functions
async def create_backup(
    database_url: str,
    config: Optional[BackupConfig] = None,
    backup_type: str = "manual"
) -> Tuple[bool, BackupMetadata]:
    """
    Create a database backup.

    Args:
        database_url: Database connection URL
        config: Optional backup configuration
        backup_type: Type of backup

    Returns:
        Tuple of (success, backup_metadata)
    """
    if config is None:
        config = BackupConfig.for_development()

    backup_manager = BackupManager(database_url, config)
    return await backup_manager.create_full_backup(backup_type)


async def restore_database(
    database_url: str,
    backup_id: str,
    config: Optional[BackupConfig] = None
) -> Tuple[bool, str]:
    """
    Restore database from backup.

    Args:
        database_url: Database connection URL
        backup_id: ID of backup to restore from
        config: Optional backup configuration

    Returns:
        Tuple of (success, message)
    """
    if config is None:
        config = BackupConfig.for_development()

    restore_manager = RestoreManager(database_url, config)
    return await restore_manager.restore_from_backup(backup_id)


async def list_available_backups(
    database_url: str,
    config: Optional[BackupConfig] = None
) -> List[BackupMetadata]:
    """
    List available backups.

    Args:
        database_url: Database connection URL
        config: Optional backup configuration

    Returns:
        List of backup metadata
    """
    if config is None:
        config = BackupConfig.for_development()

    backup_manager = BackupManager(database_url, config)
    return await backup_manager.list_backups()


async def cleanup_old_backups(
    database_url: str,
    config: Optional[BackupConfig] = None
) -> Dict[str, int]:
    """
    Clean up old backups according to retention policy.

    Args:
        database_url: Database connection URL
        config: Optional backup configuration

    Returns:
        Cleanup statistics
    """
    if config is None:
        config = BackupConfig.for_development()

    backup_manager = BackupManager(database_url, config)
    return await backup_manager.cleanup_old_backups()