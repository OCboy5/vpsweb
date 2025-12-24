"""
File Storage Utility for VPSWeb Repository System

This module provides file management operations for the repository system,
including organized storage of poems, translations, and metadata files.

⚠️ **IMPORTANT STORAGE ARCHITECTURE NOTES:**

**Relationship with Database:**
- SQLite database is the **primary source of truth** for all repository data
- File storage serves as **backup/export** and **bulk import** functionality
- JSON files in file storage are **mirrors** of database records, not the authoritative source

**Data Synchronization Strategy:**
- Database operations (CRUD) update SQLite first
- File storage is updated via export operations from database
- Import operations from files should validate against existing database records
- No direct file modifications should occur without database synchronization

**Use Cases:**
1. **Backup/Export**: Create JSON backups of database records
2. **Bulk Import**: Import large datasets from external sources
3. **Data Migration**: Move data between different VPSWeb instances
4. **Offline Processing**: Work with JSON files when database is unavailable
5. **Historical Archives**: Long-term storage of complete dataset snapshots

Features:
- Organized file storage with directory structure
- File validation and security checks
- Backup and restore operations
- File compression and archiving
- Metadata file management
- Import/export functionality
- Database synchronization validation
"""

import asyncio
import hashlib
import json

# Simple configuration for v0.3.1 repository system
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiofiles


def get_default_repo_root() -> Path:
    """Get default repository root directory"""
    # Use environment variable or default to repository_root in project
    repo_root = os.environ.get("VPSWEB_REPO_ROOT")
    if repo_root:
        return Path(repo_root)

    # Default to repository_root directory in project
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    return project_root / "repository_root"


class FileStorageError(Exception):
    """Base exception for file storage operations."""


class FileNotFoundError(FileStorageError):
    """File not found in storage."""


class InvalidFileTypeError(FileStorageError):
    """Invalid file type for operation."""


class SecurityValidationError(FileStorageError):
    """Security validation failed."""


class FileStorageManager:
    """
    Manages file storage operations for the repository system.

    Provides organized storage for poems, translations, and related files
    with proper directory structure and security validation.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize the file storage manager.

        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root or get_default_repo_root()
        self.ensure_directory_structure()

    def ensure_directory_structure(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            "poems",
            "translations",
            "ai_logs",
            "human_notes",
            "exports",
            "imports",
            "backups",
            "temp",
            "logs",
        ]

        for directory in directories:
            dir_path = self.repo_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_poem_directory(self, poem_id: str) -> Path:
        """
        Get the directory path for a poem.

        Args:
            poem_id: Unique identifier for the poem

        Returns:
            Path to poem directory
        """
        return self.repo_root / "poems" / poem_id

    def get_translation_directory(self, translation_id: str) -> Path:
        """
        Get the directory path for a translation.

        Args:
            translation_id: Unique identifier for the translation

        Returns:
            Path to translation directory
        """
        return self.repo_root / "translations" / translation_id

    def get_ai_log_directory(self, log_id: str) -> Path:
        """
        Get the directory path for an AI log.

        Args:
            log_id: Unique identifier for the AI log

        Returns:
            Path to AI log directory
        """
        return self.repo_root / "ai_logs" / log_id

    def get_human_note_directory(self, note_id: str) -> Path:
        """
        Get the directory path for a human note.

        Args:
            note_id: Unique identifier for the human note

        Returns:
            Path to human note directory
        """
        return self.repo_root / "human_notes" / note_id

    def validate_file_path(self, file_path: Path, allowed_extensions: Optional[List[str]] = None) -> bool:
        """
        Validate file path for security.

        Args:
            file_path: File path to validate
            allowed_extensions: List of allowed file extensions

        Returns:
            True if valid

        Raises:
            SecurityValidationError: If path validation fails
        """
        # Check if path is within repository root
        try:
            file_path.resolve().relative_to(self.repo_root.resolve())
        except ValueError:
            raise SecurityValidationError(f"Path outside repository: {file_path}")

        # Check file extension
        if allowed_extensions:
            if file_path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                raise SecurityValidationError(
                    f"File extension not allowed: {file_path.suffix}. " f"Allowed: {allowed_extensions}"
                )

        # Check for dangerous file patterns
        dangerous_patterns = [
            "..",
            "~",
            "$",
            "<",
            ">",
            "|",
            ";",
            "&",
            "`",
            "script",
            "executable",
            "batch",
            "cmd",
        ]

        file_str = str(file_path).lower()
        for pattern in dangerous_patterns:
            if pattern in file_str:
                raise SecurityValidationError(f"Dangerous pattern in path: {pattern}")

        return True

    async def save_file(
        self,
        file_path: Path,
        content: Union[str, bytes],
        allowed_extensions: Optional[List[str]] = None,
        create_directories: bool = True,
    ) -> Dict[str, Any]:
        """
        Save file content to storage.

        Args:
            file_path: Path where to save the file
            content: File content (string or bytes)
            allowed_extensions: List of allowed file extensions
            create_directories: Whether to create parent directories

        Returns:
            Dictionary with file metadata

        Raises:
            FileStorageError: If save operation fails
        """
        try:
            # Validate path
            self.validate_file_path(file_path, allowed_extensions)

            # Create parent directories if needed
            if create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            if isinstance(content, str):
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)
            else:
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)

            # Get file metadata
            stat = file_path.stat()
            file_hash = await self.calculate_file_hash(file_path)

            metadata = {
                "path": str(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                "hash": file_hash,
                "extension": file_path.suffix,
            }

            return metadata

        except Exception as e:
            raise FileStorageError(f"Failed to save file {file_path}: {str(e)}")

    async def load_file(self, file_path: Path, mode: str = "r") -> Union[str, bytes]:
        """
        Load file content from storage.

        Args:
            file_path: Path to file to load
            mode: File read mode ('r' for text, 'rb' for binary)

        Returns:
            File content

        Raises:
            FileNotFoundError: If file doesn't exist
            FileStorageError: If load operation fails
        """
        try:
            # Validate path
            self.validate_file_path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Read file
            async with aiofiles.open(file_path, mode) as f:
                return await f.read()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise FileStorageError(f"Failed to load file {file_path}: {str(e)}")

    async def delete_file(self, file_path: Path) -> bool:
        """
        Delete a file from storage.

        Args:
            file_path: Path to file to delete

        Returns:
            True if file was deleted

        Raises:
            FileStorageError: If delete operation fails
        """
        try:
            # Validate path
            self.validate_file_path(file_path)

            if file_path.exists():
                await asyncio.to_thread(file_path.unlink)
                return True
            return False

        except Exception as e:
            raise FileStorageError(f"Failed to delete file {file_path}: {str(e)}")

    async def calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """
        Calculate hash of a file.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm to use

        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)

        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    async def backup_directory(
        self,
        source_dir: Path,
        backup_name: Optional[str] = None,
        compression: bool = True,
    ) -> Path:
        """
        Create backup of a directory.

        Args:
            source_dir: Directory to backup
            backup_name: Name for backup file
            compression: Whether to compress the backup

        Returns:
            Path to backup file
        """
        try:
            if not source_dir.exists():
                raise FileNotFoundError(f"Source directory not found: {source_dir}")

            # Generate backup name
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{source_dir.name}_{timestamp}"

            backup_dir = self.repo_root / "backups"
            backup_dir.mkdir(exist_ok=True)

            if compression:
                backup_path = backup_dir / f"{backup_name}.zip"
                await self._create_zip_backup(source_dir, backup_path)
            else:
                backup_path = backup_dir / backup_name
                await asyncio.to_thread(shutil.copytree, source_dir, backup_path)

            return backup_path

        except Exception as e:
            raise FileStorageError(f"Failed to create backup: {str(e)}")

    async def _create_zip_backup(self, source_dir: Path, backup_path: Path) -> None:
        """Create a compressed zip backup."""

        def create_zip():
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zipf.write(file_path, arcname)

        await asyncio.to_thread(create_zip)

    async def restore_backup(self, backup_path: Path, target_dir: Path) -> None:
        """
        Restore a backup to target directory.

        Args:
            backup_path: Path to backup file
            target_dir: Directory where to restore
        """
        try:
            # Validate paths
            self.validate_file_path(backup_path)
            self.validate_file_path(target_dir)

            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Remove target directory if it exists
            if target_dir.exists():
                await asyncio.to_thread(shutil.rmtree, target_dir)

            target_dir.parent.mkdir(parents=True, exist_ok=True)

            if backup_path.suffix == ".zip":
                await self._extract_zip_backup(backup_path, target_dir)
            else:
                await asyncio.to_thread(shutil.copytree, backup_path, target_dir)

        except Exception as e:
            raise FileStorageError(f"Failed to restore backup: {str(e)}")

    async def _extract_zip_backup(self, backup_path: Path, target_dir: Path) -> None:
        """Extract a zip backup."""

        def extract_zip():
            with zipfile.ZipFile(backup_path, "r") as zipf:
                zipf.extractall(target_dir)

        await asyncio.to_thread(extract_zip)

    async def save_poem_data(self, poem_id: str, poem_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save poem data to structured file storage.

        Args:
            poem_id: Unique identifier for the poem
            poem_data: Poem data dictionary

        Returns:
            Dictionary with save metadata
        """
        poem_dir = self.get_poem_directory(poem_id)
        poem_file = poem_dir / "poem.json"

        return await self.save_file(
            poem_file,
            json.dumps(poem_data, indent=2, ensure_ascii=False),
            allowed_extensions=[".json"],
        )

    async def load_poem_data(self, poem_id: str) -> Dict[str, Any]:
        """
        Load poem data from file storage.

        Args:
            poem_id: Unique identifier for the poem

        Returns:
            Poem data dictionary

        Raises:
            FileNotFoundError: If poem file doesn't exist
        """
        poem_file = self.get_poem_directory(poem_id) / "poem.json"
        content = await self.load_file(poem_file, "r")
        return json.loads(content)

    async def save_translation_data(self, translation_id: str, translation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save translation data to structured file storage.

        Args:
            translation_id: Unique identifier for the translation
            translation_data: Translation data dictionary

        Returns:
            Dictionary with save metadata
        """
        translation_dir = self.get_translation_directory(translation_id)
        translation_file = translation_dir / "translation.json"

        return await self.save_file(
            translation_file,
            json.dumps(translation_data, indent=2, ensure_ascii=False),
            allowed_extensions=[".json"],
        )

    async def load_translation_data(self, translation_id: str) -> Dict[str, Any]:
        """
        Load translation data from file storage.

        Args:
            translation_id: Unique identifier for the translation

        Returns:
            Translation data dictionary

        Raises:
            FileNotFoundError: If translation file doesn't exist
        """
        translation_file = self.get_translation_directory(translation_id) / "translation.json"
        content = await self.load_file(translation_file, "r")
        return json.loads(content)

    async def list_files(self, directory: Path, pattern: str = "*", recursive: bool = False) -> List[Dict[str, Any]]:
        """
        List files in a directory with metadata.

        Args:
            directory: Directory to list
            pattern: Glob pattern for matching files
            recursive: Whether to search recursively

        Returns:
            List of file metadata dictionaries
        """
        try:
            self.validate_file_path(directory)

            if not directory.exists():
                return []

            files = []
            glob_pattern = directory.rglob(pattern) if recursive else directory.glob(pattern)

            for file_path in glob_pattern:
                if file_path.is_file():
                    stat = file_path.stat()
                    file_hash = await self.calculate_file_hash(file_path)

                    files.append(
                        {
                            "path": str(file_path),
                            "name": file_path.name,
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
                            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                            "hash": file_hash,
                            "extension": file_path.suffix,
                            "relative_path": str(file_path.relative_to(self.repo_root)),
                        }
                    )

            return sorted(files, key=lambda x: x["name"])

        except Exception as e:
            raise FileStorageError(f"Failed to list files in {directory}: {str(e)}")

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.

        Args:
            max_age_hours: Maximum age in hours for temp files

        Returns:
            Number of files cleaned up
        """
        try:
            temp_dir = self.repo_root / "temp"
            if not temp_dir.exists():
                return 0

            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            cleaned_count = 0

            for file_path in temp_dir.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    await self.delete_file(file_path)
                    cleaned_count += 1

            return cleaned_count

        except Exception as e:
            raise FileStorageError(f"Failed to cleanup temp files: {str(e)}")

    async def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            stats = {"total_size": 0, "file_count": 0, "directory_sizes": {}}

            for directory in self.repo_root.iterdir():
                if directory.is_dir():
                    dir_size = 0
                    dir_files = 0

                    for file_path in directory.rglob("*"):
                        if file_path.is_file():
                            dir_size += file_path.stat().st_size
                            dir_files += 1

                    stats["directory_sizes"][directory.name] = {
                        "size": dir_size,
                        "file_count": dir_files,
                    }
                    stats["total_size"] += dir_size
                    stats["file_count"] += dir_files

            return stats

        except Exception as e:
            raise FileStorageError(f"Failed to get storage stats: {str(e)}")


# Global file storage manager instance
_file_storage_manager: Optional[FileStorageManager] = None


def get_file_storage_manager(
    repo_root: Optional[Path] = None,
) -> FileStorageManager:
    """
    Get the global file storage manager instance.

    Args:
        repo_root: Repository root directory

    Returns:
        Global FileStorageManager instance
    """
    global _file_storage_manager
    if _file_storage_manager is None:
        _file_storage_manager = FileStorageManager(repo_root)
    return _file_storage_manager
