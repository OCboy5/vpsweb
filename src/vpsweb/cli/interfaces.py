"""
Phase 3C: CLI Service Layer Interfaces.

This module defines interfaces for CLI operations that will be used to
refactor the monolithic CLI module into a clean, testable architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from vpsweb.models.translation import TranslationInput, TranslationOutput
from vpsweb.models.config import WorkflowMode


class ICLIInputServiceV2(ABC):
    """Interface for CLI input handling operations."""

    @abstractmethod
    async def read_poem_from_input(
        self,
        input_path: Optional[str] = None
    ) -> str:
        """Read poem text from file or stdin."""
        pass

    @abstractmethod
    def validate_translation_input(
        self,
        source_lang: str,
        target_lang: str,
        poem_text: str
    ) -> Dict[str, Any]:
        """Validate translation input parameters."""
        pass

    @abstractmethod
    def create_translation_input(
        self,
        poem_text: str,
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TranslationInput:
        """Create TranslationInput object from parameters."""
        pass


class ICLIConfigurationServiceV2(ABC):
    """Interface for CLI configuration management."""

    @abstractmethod
    async def load_configuration(
        self,
        config_path: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Load and validate configuration."""
        pass

    @abstractmethod
    async def validate_configuration(
        self,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate configuration files."""
        pass

    @abstractmethod
    def get_workflow_modes(self) -> List[Dict[str, Any]]:
        """Get available workflow modes."""
        pass

    @abstractmethod
    async def setup_logging(
        self,
        verbose: bool = False
    ) -> None:
        """Setup logging configuration."""
        pass


class ICLIWorkflowServiceV2(ABC):
    """Interface for CLI workflow execution."""

    @abstractmethod
    async def initialize_workflow(
        self,
        config: Dict[str, Any],
        workflow_mode: WorkflowMode
    ) -> Any:
        """Initialize translation workflow."""
        pass

    @abstractmethod
    async def execute_translation_workflow(
        self,
        workflow: Any,
        input_data: TranslationInput,
        workflow_mode: str,
        show_progress: bool = True
    ) -> TranslationOutput:
        """Execute translation workflow."""
        pass

    @abstractmethod
    async def validate_workflow_input(
        self,
        input_data: TranslationInput,
        config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate workflow input without execution."""
        pass


class ICLIStorageServiceV2(ABC):
    """Interface for CLI storage operations."""

    @abstractmethod
    async def setup_storage_handler(
        self,
        output_dir: Optional[str] = None
    ) -> Any:
        """Setup storage handler for results."""
        pass

    @abstractmethod
    async def save_translation_results(
        self,
        translation_output: TranslationOutput,
        workflow_mode: str,
        include_mode_tag: bool = False
    ) -> Dict[str, Path]:
        """Save translation results to storage."""
        pass


class ICLIOutputServiceV2(ABC):
    """Interface for CLI output formatting and display."""

    @abstractmethod
    async def display_translation_summary(
        self,
        translation_output: TranslationOutput,
        saved_files: Dict[str, Path]
    ) -> None:
        """Display translation workflow summary."""
        pass

    @abstractmethod
    def format_workflow_progress(
        self,
        step_name: str,
        progress_data: Dict[str, Any]
    ) -> str:
        """Format workflow progress information."""
        pass

    @abstractmethod
    def format_error_message(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format error message for CLI display."""
        pass


class ICLIWeChatServiceV2(ABC):
    """Interface for CLI WeChat operations."""

    @abstractmethod
    async def generate_wechat_article(
        self,
        input_json_path: Path,
        output_dir: Optional[Path] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        model_type: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Generate WeChat article from translation."""
        pass

    @abstractmethod
    async def publish_wechat_article(
        self,
        article_directory: Path,
        config_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Publish WeChat article."""
        pass

    @abstractmethod
    def validate_article_directory(
        self,
        directory: Path
    ) -> Dict[str, Any]:
        """Validate article directory structure."""
        pass

    @abstractmethod
    def extract_article_metadata(
        self,
        directory: Path
    ) -> Dict[str, Any]:
        """Extract article metadata."""
        pass


class ICLICommandServiceV2(ABC):
    """Interface for individual CLI commands."""

    @abstractmethod
    async def execute_translate_command(
        self,
        input_path: Optional[str],
        source_lang: str,
        target_lang: str,
        workflow_mode: str,
        config_path: Optional[str],
        output_dir: Optional[str],
        verbose: bool,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Execute translate command."""
        pass

    @abstractmethod
    async def execute_generate_article_command(
        self,
        input_json: Path,
        output_dir: Optional[Path],
        author: Optional[str],
        digest: Optional[str],
        model_type: Optional[str],
        dry_run: bool,
        verbose: bool
    ) -> Dict[str, Any]:
        """Execute generate-article command."""
        pass

    @abstractmethod
    async def execute_publish_article_command(
        self,
        directory: Path,
        config_path: Optional[Path],
        dry_run: bool,
        verbose: bool
    ) -> Dict[str, Any]:
        """Execute publish-article command."""
        pass


class ICLIErrorHandlerV2(ABC):
    """Interface for CLI error handling."""

    @abstractmethod
    def handle_cli_error(
        self,
        error: Exception,
        command_context: str,
        verbose: bool = False
    ) -> int:
        """Handle CLI errors and return exit code."""
        pass

    @abstractmethod
    def categorize_error(
        self,
        error: Exception
    ) -> str:
        """Categorize error type for appropriate handling."""
        pass

    @abstractmethod
    def should_show_traceback(
        self,
        error: Exception,
        verbose: bool
    ) -> bool:
        """Determine if traceback should be shown."""
        pass


class ICLILoggerServiceV2(ABC):
    """Interface for CLI logging operations."""

    @abstractmethod
    async def setup_command_logging(
        self,
        command_name: str,
        verbose: bool = False
    ) -> None:
        """Setup logging for specific command."""
        pass

    @abstractmethod
    async def log_command_start(
        self,
        command_name: str,
        parameters: Dict[str, Any]
    ) -> None:
        """Log command start with parameters."""
        pass

    @abstractmethod
    async def log_command_success(
        self,
        command_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Log successful command completion."""
        pass

    @abstractmethod
    async def log_command_error(
        self,
        command_name: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Log command error with context."""
        pass