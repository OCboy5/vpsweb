"""
VPSWeb Integration Adapter for Repository System - Streamlined Prototype

This module provides a simple adapter interface for integrating with the VPSWeb
translation workflow system, enabling direct async communication between the repository
and VPSWeb's translation capabilities.

Features:
- Simple direct async calls to VPSWeb
- Basic error handling and retry logic
- Configuration management for VPSWeb integration
- Simple job tracking for translation workflows
- Data mapping between repository and VPSWeb formats
"""

import asyncio
import logging
import importlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, validator

from .models import PoemCreate, TranslationCreate, AiLogCreate, HumanNoteCreate
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


class VPSWebIntegrationStatus(str, Enum):
    """VPSWeb integration status enumeration."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    CONFIGURATION_ERROR = "configuration_error"
    VERSION_MISMATCH = "version_mismatch"
    UNKNOWN_ERROR = "unknown_error"


class WorkflowMode(str, Enum):
    """VPSWeb workflow mode enumeration matching VPSWeb configuration."""
    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"


@dataclass
class TranslationJobRequest:
    """
    Request for a translation job through VPSWeb.

    Contains all necessary information for VPSWeb to process
    a translation job and return structured results.
    """

    poem_id: Optional[str] = None
    original_text: str
    source_language: str
    target_language: str
    workflow_mode: WorkflowMode
    metadata: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate request after initialization."""
        if not self.original_text.strip():
            raise ValueError("Original text cannot be empty")
        if self.source_language == self.target_language:
            raise ValueError("Source and target languages must be different")


@dataclass
class TranslationJobResult:
    """
    Result from a VPSWeb translation job.

    Contains the complete translation result with metadata,
    performance metrics, and structured data for repository storage.
    """

    success: bool
    request: TranslationJobRequest
    translation_id: str
    translated_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    raw_output: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class VPSWebAdapterConfig(BaseModel):
    """
    Configuration for VPSWeb adapter integration.

    Defines connection parameters, workflow settings,
    and operational configuration for VPSWeb integration.
    """

    # VPSWeb Configuration
    vpsweb_config_path: str = Field(
        default="config",
        description="Path to VPSWeb configuration directory"
    )
    workflow_mode: WorkflowMode = Field(
        default=WorkflowMode.HYBRID,
        description="Default workflow mode for translations"
    )

    # Integration Settings
    enable_progress_tracking: bool = Field(
        default=True,
        description="Enable detailed progress tracking for translation jobs"
    )
    enable_retry: bool = Field(
        default=True,
        description="Enable automatic retry for failed translations"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum retry attempts for failed translations"
    )
    retry_delay_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Delay between retry attempts in seconds"
    )

    # Performance Settings
    timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Timeout for translation jobs in seconds"
    )
    max_concurrent_jobs: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent translation jobs"
    )

    # Quality Settings
    enable_quality_scoring: bool = Field(
        default=True,
        description="Enable quality scoring for translations"
    )
    min_quality_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum quality threshold for translations"
    )


class VPSWebAdapter:
    """
    Adapter for VPSWeb integration with clean interface.

    Provides a clean abstraction layer between the repository system
    and VPSWeb's translation workflow, enabling seamless integration
    while maintaining separation of concerns.
    """

    def __init__(self, config: VPSWebAdapterConfig):
        """
        Initialize the VPSWeb adapter.

        Args:
            config: Adapter configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.VPSWebAdapter")
        self._vpsweb_available = False
        self._vpsweb_module = None
        self._workflow_class = None
        self._config_class = None

        # Statistics
        self._stats = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "total_translations": 0,
            "average_duration_seconds": 0.0,
            "last_job_time": None,
        }

    async def initialize(self) -> VPSWebIntegrationStatus:
        """
        Initialize the VPSWeb adapter and check availability.

        Returns:
            Integration status
        """
        try:
            # Try to import VPSWeb modules
            self._vpsweb_module = importlib.import_module("vpsweb")
            self._workflow_class = getattr(self._vpsweb_module.core.workflow, "TranslationWorkflow")
            self._config_class = getattr(self._vpsweb_module.models.config, "WorkflowConfig")

            # Load VPSWeb configuration
            vpsweb_config = self._load_vpsweb_config()

            # Test VPSWeb availability
            test_result = await self._test_vpsweb_availability(vpsweb_config)

            if test_result:
                self._vpsweb_available = True
                self.logger.info("VPSWeb adapter initialized successfully")
                return VPSWebIntegrationStatus.AVAILABLE
            else:
                return VPSWebIntegrationStatus.UNKNOWN_ERROR

        except ImportError as e:
            self.logger.error(f"Failed to import VPSWeb: {e}")
            return VPSWebIntegrationStatus.UNAVAILABLE
        except Exception as e:
            self.logger.error(f"VPSWeb adapter initialization failed: {e}")
            return VPSWebIntegrationStatus.CONFIGURATION_ERROR

    def _load_vpsweb_config(self) -> Any:
        """
        Load VPSWeb configuration.

        Returns:
            VPSWeb configuration object
        """
        try:
            # Try to load VPSWeb configuration using standard loader
            from vpsweb.utils.config_loader import load_config
            return load_config()
        except ImportError:
            # Fallback to basic configuration
            self.logger.warning("VPSWeb config loader not available, using basic configuration")
            return self._create_basic_config()

    def _create_basic_config(self) -> Any:
        """
        Create basic VPSWeb configuration.

        Returns:
            Basic configuration object
        """
        # This would need to match VPSWeb's configuration structure
        return {
            "models": {
                "provider": "tongyi",
                "model_name": "qwen-max",
                "workflow_mode": self.config.workflow_mode.value,
            }
        }

    async def _test_vpsweb_availability(self, config: Any) -> bool:
        """
        Test VPSWeb availability and configuration.

        Args:
            config: VPSWeb configuration

        Returns:
            True if VPSWeb is available and properly configured
        """
        try:
            # Try to create workflow instance
            workflow = self._workflow_class(config)

            # Test basic workflow functionality
            # This is a simple availability test
            return hasattr(workflow, 'execute') and callable(getattr(workflow, 'execute'))

        except Exception as e:
            self.logger.error(f"VPSWeb availability test failed: {e}")
            return False

    async def create_translation_job(
        self,
        request: TranslationJobRequest,
        background_tasks: Any = None
    ) -> str:
        """
        Create and submit a translation job to VPSWeb.

        Args:
            request: Translation job request
            background_tasks: FastAPI BackgroundTasks instance

        Returns:
            Job identifier
        """
        if not self._vpsweb_available:
            raise RuntimeError("VPSWeb is not available")

        job_id = f"translation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hash(request.original_text) % 10000:04d}"

        # Add to background tasks if provided
        if background_tasks:
            background_tasks.add_task(
                self._execute_translation_job_direct,
                job_id,
                request
            )
        else:
            # Execute directly if no background tasks
            await self._execute_translation_job_direct(job_id, request)

        self.logger.info(
            "Created translation job",
            job_id=job_id,
            source_lang=request.source_language,
            target_lang=request.target_language,
            workflow_mode=request.workflow_mode.value
        )

        return job_id

    async def _execute_translation_job_direct(
        self,
        job_id: str,
        request: TranslationJobRequest
    ) -> TranslationJobResult:
        """
        Execute a translation job using VPSWeb with direct async call.

        Args:
            job_id: Job identifier
            request: Translation job request

        Returns:
            Translation job result
        """
        start_time = datetime.now(timezone.utc)

        try:
            self.logger.info(f"Starting translation job: {job_id}")

            # Create VPSWeb translation input
            vpsweb_input = self._create_vpsweb_input(request)

            # Load VPSWeb configuration
            vpsweb_config = self._load_vpsweb_config()

            # Create workflow instance
            workflow = self._workflow_class(vpsweb_config)

            # Execute translation workflow
            vpsweb_output = await self._execute_workflow_safely(workflow, vpsweb_input)

            # Parse results
            result = self._parse_vpsweb_output(vpsweb_output, request, start_time)

            # Update statistics
            self._update_statistics(result, start_time)

            self.logger.info(
                f"Translation job completed successfully: {job_id}",
                duration_seconds=result.duration_seconds
            )

            return result

        except Exception as e:
            # Create failed result
            result = TranslationJobResult(
                success=False,
                request=request,
                translation_id=job_id,
                translated_text="",
                error=e,
                created_at=start_time
            )

            self.logger.error(
                f"Translation job failed: {job_id}",
                error=str(e)
            )

            return result

    def _create_vpsweb_input(self, request: TranslationJobRequest) -> Any:
        """
        Create VPSWeb input from translation request.

        Args:
            request: Translation job request

        Returns:
            VPSWeb input object
        """
        try:
            # Import VPSWeb models
            from vpsweb.models.translation import TranslationInput

            # Create metadata
            metadata = request.metadata.copy()
            if request.poem_id:
                metadata["poem_id"] = request.poem_id

            return TranslationInput(
                original_poem=request.original_text,
                source_lang=self._map_language(request.source_language),
                target_lang=self._map_language(request.target_language),
                metadata=metadata
            )

        except ImportError:
            # Fallback input creation
            self.logger.warning("VPSWeb TranslationInput not available, creating basic input")
            return {
                "original_poem": request.original_text,
                "source_lang": request.source_language,
                "target_lang": request.target_language,
                "metadata": request.metadata
            }

    def _map_language(self, language: str) -> str:
        """
        Map language codes to VPSWeb format.

        Args:
            language: Language code

        Returns:
            VPSWeb language code
        """
        language_mapping = {
            "English": "English",
            "en": "English",
            "Chinese": "Chinese",
            "zh": "Chinese",
            "zh-Hans": "Chinese",
            "zh-Hant": "Chinese",
            "Polish": "Polish",
            "pl": "Polish",
        }

        return language_mapping.get(language, language)

    async def _execute_workflow_safely(self, workflow: Any, vpsweb_input: Any) -> Any:
        """
        Execute VPSWeb workflow safely with timeout.

        Args:
            workflow: VPSWeb workflow instance
            vpsweb_input: VPSWeb input object

        Returns:
            VPSWeb workflow output
        """
        try:
            # Execute with timeout
            if self.config.timeout_seconds > 0:
                return await asyncio.wait_for(
                    self._run_workflow(workflow, vpsweb_input),
                    timeout=self.config.timeout_seconds
                )
            else:
                return await self._run_workflow(workflow, vpsweb_input)

        except asyncio.TimeoutError as e:
            raise Exception(f"Translation workflow timed out after {self.config.timeout_seconds} seconds") from e

    async def _run_workflow(self, workflow: Any, vpsweb_input: Any) -> Any:
        """
        Run VPSWeb workflow.

        Args:
            workflow: VPSWeb workflow instance
            vpsweb_input: VPSWeb input object

        Returns:
            VPSWeb workflow output
        """
        # Check if workflow has async execute method
        if hasattr(workflow, 'execute') and asyncio.iscoroutinefunction(workflow.execute):
            return await workflow.execute(vpsweb_input)
        elif hasattr(workflow, 'execute'):
            # Run sync method in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, workflow.execute, vpsweb_input)
        else:
            raise Exception("VPSWeb workflow does not have execute method")

    def _parse_vpsweb_output(
        self,
        vpsweb_output: Any,
        request: TranslationJobRequest,
        start_time: datetime
    ) -> TranslationJobResult:
        """
        Parse VPSWeb output into repository format.

        Args:
            vpsweb_output: VPSWeb workflow output
            request: Original translation request
            start_time: Job start time

        Returns:
            Translation job result
        """
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()

        try:
            # Extract translation text and metadata
            translated_text = self._extract_translation_text(vpsweb_output)
            metadata = self._extract_metadata(vpsweb_output)
            performance_metrics = self._extract_performance_metrics(vpsweb_output)

            return TranslationJobResult(
                success=True,
                request=request,
                translation_id=f"vpsweb_{hash(translated_text) % 10000:04d}",
                translated_text=translated_text,
                metadata=metadata,
                performance_metrics={**performance_metrics, "duration_seconds": duration_seconds},
                raw_output=self._serialize_output(vpsweb_output),
                created_at=start_time,
                completed_at=end_time
            )

        except Exception as e:
            raise Exception(f"Failed to parse VPSWeb output: {e}") from e

    def _extract_translation_text(self, vpsweb_output: Any) -> str:
        """
        Extract translated text from VPSWeb output.

        Args:
            vpsweb_output: VPSWeb workflow output

        Returns:
            Translated text
        """
        # This would need to match VPSWeb's output structure
        if hasattr(vpsweb_output, 'revised_translation'):
            return vpsweb_output.revised_translation
        elif hasattr(vpsweb_output, 'final_translation'):
            return vpsweb_output.final_translation
        elif hasattr(vpsweb_output, 'translation'):
            return vpsweb_output.translation
        else:
            # Fallback to string representation
            return str(vpsweb_output)

    def _extract_metadata(self, vpsweb_output: Any) -> Dict[str, Any]:
        """
        Extract metadata from VPSWeb output.

        Args:
            vpsweb_output: VPSWeb workflow output

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Extract common metadata fields
        for field in ['provider', 'model_name', 'workflow_mode', 'tokens_used', 'cost']:
            if hasattr(vpsweb_output, field):
                metadata[field] = getattr(vpsweb_output, field)

        return metadata

    def _extract_performance_metrics(self, vpsweb_output: Any) -> Dict[str, Any]:
        """
        Extract performance metrics from VPSWeb output.

        Args:
            vpsweb_output: VPSWeb workflow output

        Returns:
            Performance metrics dictionary
        """
        metrics = {}

        # Extract performance fields
        for field in ['duration_seconds', 'api_calls', 'response_time']:
            if hasattr(vpsweb_output, field):
                metrics[field] = getattr(vpsweb_output, field)

        return metrics

    def _serialize_output(self, vpsweb_output: Any) -> Optional[Dict[str, Any]]:
        """
        Serialize VPSWeb output to dictionary.

        Args:
            vpsweb_output: VPSWeb workflow output

        Returns:
            Serialized output or None
        """
        try:
            if hasattr(vpsweb_output, 'dict'):
                return vpsweb_output.dict()
            elif hasattr(vpsweb_output, '__dict__'):
                return vpsweb_output.__dict__
            else:
                return None
        except Exception:
            return None

    def _update_statistics(self, result: TranslationJobResult, start_time: datetime) -> None:
        """
        Update adapter statistics.

        Args:
            result: Translation job result
            start_time: Job start time
        """
        self._stats["total_jobs"] += 1

        if result.success:
            self._stats["successful_jobs"] += 1
            self._stats["total_translations"] += 1
        else:
            self._stats["failed_jobs"] += 1

        # Update average duration
        duration_seconds = result.performance_metrics.get("duration_seconds", 0)
        if duration_seconds:
            current_avg = self._stats["average_duration_seconds"]
            total_jobs = self._stats["total_jobs"]
            self._stats["average_duration_seconds"] = (
                (current_avg * (total_jobs - 1) + duration_seconds) / total_jobs
            )

        self._stats["last_job_time"] = datetime.now(timezone.utc)

    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get VPSWeb integration status and statistics.

        Returns:
            Integration status information
        """
        return {
            "available": self._vpsweb_available,
            "status": VPSWebIntegrationStatus.AVAILABLE if self._vpsweb_available else VPSWebIntegrationStatus.UNAVAILABLE,
            "configuration": {
                "workflow_mode": self.config.workflow_mode.value,
                "enable_progress_tracking": self.config.enable_progress_tracking,
                "max_concurrent_jobs": self.config.max_concurrent_jobs,
                "timeout_seconds": self.config.timeout_seconds,
            },
            "statistics": self._stats.copy(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of VPSWeb integration.

        Returns:
            Health check results
        """
        status = "healthy"
        issues = []

        if not self._vpsweb_available:
            status = "unhealthy"
            issues.append("VPSWeb is not available")

        # Test VPSWeb configuration
        try:
            vpsweb_config = self._load_vpsweb_config()
            if not vpsweb_config:
                status = "degraded"
                issues.append("VPSWeb configuration could not be loaded")
        except Exception as e:
            status = "unhealthy"
            issues.append(f"VPSWeb configuration error: {str(e)}")

        # Test VPSWeb functionality
        try:
            vpsweb_config = self._load_vpsweb_config()
            workflow = self._workflow_class(vpsweb_config)
            if not hasattr(workflow, 'execute'):
                status = "degraded"
                issues.append("VPSWeb workflow execute method not available")
        except Exception as e:
            status = "unhealthy"
            issues.append(f"VPSWeb workflow test failed: {str(e)}")

        return {
            "status": status,
            "issues": issues,
            "statistics": self.get_integration_status(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global VPSWeb adapter instance
_vpsweb_adapter: Optional[VPSWebAdapter] = None


def get_vpsweb_adapter(config: Optional[VPSWebAdapterConfig] = None) -> VPSWebAdapter:
    """
    Get or create the global VPSWeb adapter instance.

    Args:
        config: Optional adapter configuration

    Returns:
        VPSWebAdapter: Global adapter instance
    """
    global _vpsweb_adapter
    if _vpsweb_adapter is None:
        _vpsweb_adapter = VPSWebAdapter(
            config or VPSWebAdapterConfig()
        )
    return _vpsweb_adapter


async def initialize_vpsweb_adapter(
    config: Optional[VPSWebAdapterConfig] = None
) -> VPSWebAdapter:
    """
    Initialize the global VPSWeb adapter.

    Args:
        config: Optional adapter configuration

    Returns:
        VPSWebAdapter: Initialized adapter
    """
    adapter = get_vpsweb_adapter(config)
    await adapter.initialize()
    return adapter