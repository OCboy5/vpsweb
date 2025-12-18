"""
Storage Handler for Vox Poetica Studio Web.

This module provides file-based storage for translation outputs with proper
serialization/deserialization of Pydantic models and comprehensive error handling.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.translation import TranslationOutput
from .filename_utils import (
    extract_poet_and_title,
    generate_translation_filename,
)
from .markdown_export import MarkdownExporter

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""


class SaveError(StorageError):
    """Raised when saving a translation fails."""


class LoadError(StorageError):
    """Raised when loading a translation fails."""


class StorageHandler:
    """
    Handles storage operations for translation outputs.

    Provides methods for saving, loading, and listing translation outputs
    with proper file naming, JSON serialization, and error handling.
    """

    def __init__(self, output_dir: str = "outputs"):
        """
        Initialize the storage handler.

        Args:
            output_dir: Directory where translation files will be stored.
                       Will be created if it doesn't exist.

        Raises:
            StorageError: If the output directory cannot be created
        """
        self.output_dir = Path(output_dir)
        self.json_dir = self.output_dir / "json"

        try:
            # Create output directories if they don't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.json_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Storage handler initialized with output directory: {self.output_dir.absolute()}"
            )
            logger.info(
                f"JSON files will be stored in: {self.json_dir.absolute()}"
            )

            # Initialize markdown exporter
            self.markdown_exporter = MarkdownExporter(output_dir)

        except Exception as e:
            logger.error(
                f"Failed to create output directory '{self.output_dir}': {e}"
            )
            raise StorageError(
                f"Could not create output directory '{self.output_dir}': {e}"
            )

    def save_translation(
        self,
        output: TranslationOutput,
        workflow_mode: str = None,
        include_mode_tag: bool = False,
    ) -> Path:
        """
        Save a translation output to a timestamped JSON file.

        Args:
            output: TranslationOutput instance to save
            workflow_mode: Workflow mode used for the translation
            include_mode_tag: Whether to include workflow mode in filename

        Returns:
            Path to the saved file

        Raises:
            SaveError: If saving fails due to file I/O or serialization issues
        """
        try:
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Extract poet and title information
            poet, title = extract_poet_and_title(
                output.input.original_poem, output.input.metadata
            )

            # Generate new descriptive filename
            filename = generate_translation_filename(
                poet=poet,
                title=title,
                source_lang=output.input.source_lang,
                target_lang=output.input.target_lang,
                timestamp=timestamp,
                workflow_id=output.workflow_id,
                workflow_mode=workflow_mode,
                file_format="json",
                is_log=False,
            )

            file_path = self.json_dir / filename

            # Convert to dictionary for JSON serialization
            output_dict = output.to_dict()

            # Save as formatted JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"Translation saved to: {file_path}")
            logger.debug(
                f"Workflow ID: {output.workflow_id}, Total tokens: {output.total_tokens}"
            )
            logger.info(
                f"Generated filename with poet '{poet}' and title '{title}'"
            )

            return file_path

        except Exception as e:
            logger.error(
                f"JSON serialization failed for workflow {output.workflow_id}: {e}"
            )
            raise SaveError(f"Failed to serialize translation output: {e}")
        except IOError as e:
            logger.error(f"File I/O error while saving translation: {e}")
            raise SaveError(f"Failed to write translation file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while saving translation: {e}")
            raise SaveError(f"Failed to save translation: {e}")

    def load_translation(self, file_path: Path) -> TranslationOutput:
        """
        Load a translation output from a JSON file.

        Args:
            file_path: Path to the translation JSON file

        Returns:
            TranslationOutput instance

        Raises:
            LoadError: If loading fails due to file I/O, JSON parsing, or validation issues
        """
        try:
            # Validate file exists and is readable
            if not file_path.exists():
                raise LoadError(f"Translation file not found: {file_path}")

            if not file_path.is_file():
                raise LoadError(f"Path is not a file: {file_path}")

            # Load JSON data
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse into TranslationOutput model
            translation_output = TranslationOutput.from_dict(data)

            logger.info(f"Translation loaded from: {file_path}")
            logger.debug(f"Workflow ID: {translation_output.workflow_id}")

            return translation_output

        except Exception as e:
            logger.error(f"JSON parsing failed for file {file_path}: {e}")
            raise LoadError(f"Invalid JSON format in translation file: {e}")
        except KeyError as e:
            logger.error(
                f"Missing required field in translation file {file_path}: {e}"
            )
            raise LoadError(f"Translation file missing required field: {e}")
        except ValueError as e:
            logger.error(f"Data validation failed for file {file_path}: {e}")
            raise LoadError(f"Translation data validation failed: {e}")
        except IOError as e:
            logger.error(f"File I/O error while loading translation: {e}")
            raise LoadError(f"Failed to read translation file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while loading translation: {e}")
            raise LoadError(f"Failed to load translation: {e}")

    def list_translations(self) -> List[Path]:
        """
        List all translation files in the JSON subdirectory.

        Returns:
            List of Path objects for all translation JSON files

        Raises:
            StorageError: If directory listing fails
        """
        try:
            # Find all JSON files in json subdirectory
            # Support both new naming (poet-led) and legacy naming (translation_-prefixed)
            translation_files = list(self.json_dir.glob("*.json"))

            # Sort by modification time (newest first)
            translation_files.sort(
                key=lambda x: x.stat().st_mtime, reverse=True
            )

            logger.debug(
                f"Found {len(translation_files)} translation files in {self.json_dir}"
            )

            return translation_files

        except Exception as e:
            logger.error(
                f"Failed to list translation files in {self.json_dir}: {e}"
            )
            raise StorageError(f"Failed to list translation files: {e}")

    def get_translation_by_id(
        self, workflow_id: str
    ) -> Optional[TranslationOutput]:
        """
        Find and load a translation by workflow ID.

        Args:
            workflow_id: The workflow ID to search for

        Returns:
            TranslationOutput if found, None otherwise

        Raises:
            StorageError: If search operation fails
        """
        try:
            translation_files = self.list_translations()

            for file_path in translation_files:
                try:
                    translation = self.load_translation(file_path)
                    if translation.workflow_id == workflow_id:
                        logger.info(
                            f"Found translation with workflow ID: {workflow_id}"
                        )
                        return translation
                except LoadError:
                    # Skip files that can't be loaded
                    continue

            logger.debug(
                f"No translation found with workflow ID: {workflow_id}"
            )
            return None

        except Exception as e:
            logger.error(
                f"Failed to search for translation with ID {workflow_id}: {e}"
            )
            raise StorageError(f"Failed to search for translation: {e}")

    def delete_translation(self, file_path: Path) -> bool:
        """
        Delete a translation file.

        Args:
            file_path: Path to the translation file to delete

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            StorageError: If deletion fails
        """
        try:
            # Ensure the file is within our output directory for safety
            if not file_path.is_relative_to(self.output_dir):
                logger.warning(
                    f"Attempted to delete file outside output directory: {file_path}"
                )
                return False

            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                logger.info(f"Translation file deleted: {file_path}")
                return True
            else:
                logger.warning(
                    f"Translation file not found for deletion: {file_path}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to delete translation file {file_path}: {e}")
            raise StorageError(f"Failed to delete translation file: {e}")

    def save_translation_with_markdown(
        self,
        output: TranslationOutput,
        workflow_mode: str = None,
        include_mode_tag: bool = False,
    ) -> Dict[str, Path]:
        """
        Save a translation output to both JSON and markdown files.

        Args:
            output: TranslationOutput instance to save
            workflow_mode: Workflow mode used for the translation
            include_mode_tag: Whether to include workflow mode in filename

        Returns:
            Dictionary with paths to saved files:
            {
                'json': Path to JSON file,
                'markdown_final': Path to final translation markdown,
                'markdown_log': Path to full log markdown
            }

        Raises:
            SaveError: If saving fails due to file I/O or serialization issues
        """
        try:
            # Save JSON file (existing functionality)
            json_path = self.save_translation(
                output, workflow_mode, include_mode_tag
            )

            # Save markdown files (new functionality)
            markdown_paths = self.markdown_exporter.export_both(output)

            result = {
                "json": json_path,
                "markdown_final": Path(markdown_paths["final_translation"]),
                "markdown_log": Path(markdown_paths["full_log"]),
            }

            logger.info(f"Translation saved to multiple formats:")
            logger.info(f"  JSON: {result['json']}")
            logger.info(f"  Markdown (final): {result['markdown_final']}")
            logger.info(f"  Markdown (log): {result['markdown_log']}")

            return result

        except Exception as e:
            logger.error(f"Failed to save translation with markdown: {e}")
            raise SaveError(f"Failed to save translation with markdown: {e}")

    def get_storage_info(self) -> dict:
        """
        Get information about the storage directory.

        Returns:
            Dictionary with storage statistics

        Raises:
            StorageError: If statistics collection fails
        """
        try:
            translation_files = self.list_translations()
            total_size = sum(
                file_path.stat().st_size for file_path in translation_files
            )

            return {
                "output_directory": str(self.output_dir.absolute()),
                "total_files": len(translation_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_file": (
                    min(
                        translation_files, key=lambda x: x.stat().st_mtime
                    ).name
                    if translation_files
                    else None
                ),
                "newest_file": (
                    max(
                        translation_files, key=lambda x: x.stat().st_mtime
                    ).name
                    if translation_files
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            raise StorageError(f"Failed to get storage information: {e}")

    # Enhanced Poet-Based Organization Methods
    def save_translation_with_poet_dir(
        self,
        output: TranslationOutput,
        poet_name: str,
        workflow_mode: str = None,
        include_mode_tag: bool = False,
    ) -> Path:
        """
        Save a translation output to a poet-based subdirectory structure.

        Structure: outputs/json/poets/{poet_name}/{filename}.json

        Args:
            output: TranslationOutput instance to save
            poet_name: Name of the poet for subdirectory organization
            workflow_mode: Workflow mode used for the translation
            include_mode_tag: Whether to include workflow mode in filename

        Returns:
            Path to the saved file in poet subdirectory

        Raises:
            SaveError: If saving fails due to file I/O or serialization issues
        """
        try:
            # Create poet subdirectory structure
            poets_dir = self.json_dir / "poets"
            poet_dir = poets_dir / poet_name

            # Create directories if they don't exist
            poets_dir.mkdir(exist_ok=True)
            poet_dir.mkdir(exist_ok=True)

            # Generate timestamp and filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            poet, title = extract_poet_and_title(
                output.input.original_poem, output.input.metadata
            )

            # Use provided poet_name or extracted poet
            effective_poet_name = poet_name or poet

            filename = generate_translation_filename(
                poet=effective_poet_name,
                title=title,
                source_lang=output.input.source_lang,
                target_lang=output.input.target_lang,
                timestamp=timestamp,
                workflow_id=output.workflow_id,
                workflow_mode=workflow_mode,
                file_format="json",
                is_log=False,
            )

            # Save to poet subdirectory
            poet_file_path = poet_dir / filename

            # Convert to dictionary for JSON serialization
            output_dict = output.to_dict()

            # Save to poet subdirectory
            with open(poet_file_path, "w", encoding="utf-8") as f:
                json.dump(output_dict, f, ensure_ascii=False, indent=2)

            logger.info(
                f"Translation saved to poet directory: {poet_file_path}"
            )

            return poet_file_path

        except Exception as e:
            logger.error(
                f"Failed to save translation with poet directory: {e}"
            )
            raise SaveError(
                f"Failed to save translation with poet directory: {e}"
            )

    def get_poet_directories(self) -> List[str]:
        """
        Get list of all poet subdirectories.

        Returns:
            List of poet names that have subdirectories

        Raises:
            StorageError: If directory listing fails
        """
        try:
            poets_dir = self.json_dir / "poets"

            if not poets_dir.exists():
                return []

            poet_dirs = []
            for item in poets_dir.iterdir():
                if item.is_dir():
                    poet_dirs.append(item.name)

            return sorted(poet_dirs)

        except Exception as e:
            logger.error(f"Failed to get poet directories: {e}")
            raise StorageError(f"Failed to get poet directories: {e}")

    def get_poet_files(self, poet_name: str) -> List[Path]:
        """
        Get all translation files for a specific poet.

        Args:
            poet_name: Name of the poet

        Returns:
            List of paths to poet's translation files

        Raises:
            StorageError: If file listing fails
        """
        try:
            poet_dir = self.json_dir / "poets" / poet_name

            if not poet_dir.exists():
                return []

            files = []
            for file_path in poet_dir.glob("*.json"):
                if file_path.is_file():
                    files.append(file_path)

            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            return files

        except Exception as e:
            logger.error(f"Failed to get poet files for '{poet_name}': {e}")
            raise StorageError(
                f"Failed to get poet files for '{poet_name}': {e}"
            )

    def __repr__(self) -> str:
        """String representation of the storage handler."""
        return f"StorageHandler(output_dir='{self.output_dir}')"
