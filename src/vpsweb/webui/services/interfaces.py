"""
Phase 3C: Service Layer Interfaces for Web Application Architecture.

This module defines interfaces for the service layer that will be used to
refactor the monolithic Main Application Router into a clean, testable architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import BackgroundTasks

from vpsweb.repository.service import RepositoryWebService


class IPoemServiceV2(ABC):
    """Enhanced interface for poem-related business logic."""

    @abstractmethod
    async def get_poem_list(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of poems with filtering options."""
        pass

    @abstractmethod
    async def get_poem_detail(self, poem_id: str) -> Dict[str, Any]:
        """Get detailed poem information including translations."""
        pass

    @abstractmethod
    async def create_poem(self, poem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new poem with validation."""
        pass

    @abstractmethod
    async def update_poem(self, poem_id: str, poem_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing poem."""
        pass

    @abstractmethod
    async def delete_poem(self, poem_id: str) -> bool:
        """Delete a poem and related data."""
        pass

    @abstractmethod
    async def get_poem_statistics(self) -> Dict[str, Any]:
        """Get overall poem statistics."""
        pass


class ITranslationServiceV2(ABC):
    """Enhanced interface for translation-related business logic."""

    @abstractmethod
    async def get_translation_list(
        self,
        skip: int = 0,
        limit: int = 100,
        poem_id: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get paginated list of translations with filtering."""
        pass

    @abstractmethod
    async def get_translation_detail(self, translation_id: str) -> Dict[str, Any]:
        """Get detailed translation information."""
        pass

    @abstractmethod
    async def get_translation_comparison(self, translation_id: str) -> Dict[str, Any]:
        """Get comparison data for a translation."""
        pass

    @abstractmethod
    async def create_translation(self, translation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new translation with validation."""
        pass

    @abstractmethod
    async def delete_translation(self, translation_id: str) -> bool:
        """Delete a translation."""
        pass

    @abstractmethod
    async def get_workflow_summary(self, translation_id: str) -> Dict[str, Any]:
        """Get workflow execution summary for a translation."""
        pass

    @abstractmethod
    async def get_workflow_steps(self, translation_id: str) -> List[Dict[str, Any]]:
        """Get detailed workflow steps for a translation."""
        pass


class IPoetServiceV2(ABC):
    """Interface for poet-related business logic."""

    @abstractmethod
    async def get_poets_list(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        min_poems: Optional[int] = None,
        min_translations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get paginated list of poets with statistics."""
        pass

    @abstractmethod
    async def get_poet_detail(
        self,
        poet_name: str,
        skip: int = 0,
        limit: int = 20,
        language: Optional[str] = None,
        has_translations: Optional[bool] = None,
        sort_by: str = "title",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Get detailed poet information with poems and statistics."""
        pass

    @abstractmethod
    async def get_poet_statistics(self, poet_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a specific poet."""
        pass

    @abstractmethod
    async def get_all_poets_statistics(self) -> Dict[str, Any]:
        """Get statistics for all poets."""
        pass


class IWorkflowServiceV2(ABC):
    """Interface for workflow management and execution."""

    @abstractmethod
    async def start_translation_workflow(
        self,
        poem_id: str,
        target_lang: str,
        workflow_mode: str,
        background_tasks: "BackgroundTasks",
        user_id: Optional[str] = None
    ) -> str:
        """Start a new translation workflow."""
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a workflow task."""
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        """Cancel a workflow task."""
        pass

    @abstractmethod
    async def list_tasks(
        self,
        limit: int = 50,
        user_id: Optional[str] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """List workflow tasks with filtering."""
        pass

    @abstractmethod
    async def get_workflow_modes(self) -> Dict[str, Any]:
        """Get available workflow modes."""
        pass

    @abstractmethod
    async def validate_workflow_input(
        self,
        poem_id: str,
        source_lang: str,
        target_lang: str,
        workflow_mode: str
    ) -> Dict[str, Any]:
        """Validate workflow input parameters."""
        pass


class IStatisticsServiceV2(ABC):
    """Interface for analytics and statistics."""

    @abstractmethod
    async def get_repository_statistics(self) -> Dict[str, Any]:
        """Get comprehensive repository statistics."""
        pass

    @abstractmethod
    async def get_translation_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get translation trends over time."""
        pass

    @abstractmethod
    async def get_poet_activity_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get poet activity statistics."""
        pass

    @abstractmethod
    async def get_workflow_performance_stats(self) -> Dict[str, Any]:
        """Get workflow performance metrics."""
        pass


class ITemplateServiceV2(ABC):
    """Interface for template rendering and management."""

    @abstractmethod
    async def render_template(
        self,
        template_name: str,
        context: Dict[str, Any],
        request: Optional[Any] = None
    ) -> str:
        """Render a template with context."""
        pass

    @abstractmethod
    async def get_template_list(self, category: Optional[str] = None) -> List[str]:
        """Get list of available templates."""
        pass

    @abstractmethod
    async def validate_template_data(
        self,
        template_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate template data before rendering."""
        pass


class IExceptionHandlerServiceV2(ABC):
    """Interface for error handling and response formatting."""

    @abstractmethod
    async def handle_http_error(
        self,
        error: Exception,
        request: Any,
        is_web_request: bool
    ) -> Any:
        """Handle HTTP errors with appropriate formatting."""
        pass

    @abstractmethod
    async def handle_general_error(
        self,
        error: Exception,
        request: Any,
        error_id: str,
        is_web_request: bool
    ) -> Any:
        """Handle general exceptions with logging and formatting."""
        pass

    @abstractmethod
    def generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        pass


class IPerformanceServiceV2(ABC):
    """Interface for performance monitoring and optimization."""

    @abstractmethod
    async def log_request_performance(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log request performance metrics."""
        pass

    @abstractmethod
    async def get_performance_summary(
        self,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance summary for specified time period."""
        pass

    @abstractmethod
    def should_log_slow_request(self, duration: float) -> bool:
        """Determine if request is slow enough to log."""
        pass


class ITaskManagementServiceV2(ABC):
    """Interface for background task management."""

    @abstractmethod
    async def create_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new background task."""
        pass

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        pass

    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        pass

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update task status."""
        pass

    @abstractmethod
    async def update_task_progress(
        self,
        task_id: str,
        step: str,
        progress: int,
        details: Dict[str, Any],
    ) -> None:
        """Update task progress."""
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information."""
        pass

    @abstractmethod
    async def cleanup_expired_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up expired tasks."""
        pass


class ISSEServiceV2(ABC):
    """Interface for Server-Sent Events (SSE) functionality."""

    @abstractmethod
    async def create_sse_stream(
        self,
        task_id: str,
        request: Any
    ) -> Any:
        """Create SSE stream for real-time updates."""
        pass

    @abstractmethod
    async def send_sse_event(
        self,
        task_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Send SSE event to connected clients."""
        pass

    @abstractmethod
    def should_send_heartbeat(self, last_update_time: float) -> bool:
        """Determine if heartbeat event should be sent."""
        pass


class IConfigServiceV2(ABC):
    """Interface for application configuration management."""

    @abstractmethod
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get configuration setting."""
        pass

    @abstractmethod
    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        pass

    @abstractmethod
    async def update_setting(self, key: str, value: Any) -> bool:
        """Update configuration setting."""
        pass

    @abstractmethod
    async def validate_setting(self, key: str, value: Any) -> bool:
        """Validate configuration setting value."""
        pass