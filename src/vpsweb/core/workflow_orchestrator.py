"""
Phase 3B: Interface-based Workflow Orchestrator Implementation.

This module implements the IWorkflowOrchestrator interface to provide
clean separation of concerns and better testability for workflow execution.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from vpsweb.utils.tools_phase3a import (ErrorCollector, PerformanceMonitor,
                                        ResourceManager)

from .container import DIContainer
from .interfaces import (Event, IConfigurationService, IEventBus, ILLMFactory,
                         ILogger, IMetricsCollector, IOutputParser,
                         IPromptService, IRetryService, IWorkflowOrchestrator,
                         LLMRequest, LLMResponse, WorkflowConfig,
                         WorkflowResult, WorkflowStatus, WorkflowStep)


class WorkflowStepStatus(Enum):
    """Status of individual workflow steps."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStepResult:
    """Result of a single workflow step execution."""

    step_name: str
    status: WorkflowStepStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float = 0.0
    tokens_used: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowExecutionContext:
    """Context for workflow execution."""

    workflow_id: str
    input_data: Dict[str, Any]
    config: WorkflowConfig
    start_time: datetime
    progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowOrchestratorV2(IWorkflowOrchestrator):
    """
    Phase 3B implementation of IWorkflowOrchestrator interface.

    This orchestrator provides:
    - Clean interface-based architecture
    - Dependency injection support
    - Comprehensive error handling and logging
    - Performance monitoring and metrics
    - Event-driven progress tracking
    - Resource management and cleanup
    """

    def __init__(
        self,
        container: DIContainer,
        event_bus: Optional[IEventBus] = None,
        logger: Optional[ILogger] = None,
        metrics_collector: Optional[IMetricsCollector] = None,
        retry_service: Optional[IRetryService] = None,
    ):
        """
        Initialize the workflow orchestrator.

        Args:
            container: DI container for service resolution
            event_bus: Optional event bus for progress tracking
            logger: Optional logger service
            metrics_collector: Optional metrics collector
            retry_service: Optional retry service
        """
        self.container = container
        self.event_bus = event_bus
        self.logger = logger
        self.metrics_collector = metrics_collector
        self.retry_service = retry_service

        # Active workflow tracking
        self._active_workflows: Dict[str, WorkflowExecutionContext] = {}
        self._workflow_results: Dict[str, List[WorkflowStepResult]] = {}

        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.resource_manager = ResourceManager()
        self.error_collector = ErrorCollector()

        # Component services (resolved via DI)
        self._llm_factory: Optional[ILLMFactory] = None
        self._prompt_service: Optional[IPromptService] = None
        self._output_parser: Optional[IOutputParser] = None
        self._config_service: Optional[IConfigurationService] = None

        self._log_debug("WorkflowOrchestratorV2 initialized")

    def _resolve_services(self) -> None:
        """Resolve required services from DI container."""
        if self._llm_factory is None and self.container.is_registered(ILLMFactory):
            self._llm_factory = self.container.resolve(ILLMFactory)

        if self._prompt_service is None and self.container.is_registered(
            IPromptService
        ):
            self._prompt_service = self.container.resolve(IPromptService)

        if self._output_parser is None and self.container.is_registered(IOutputParser):
            self._output_parser = self.container.resolve(IOutputParser)

        if self._config_service is None and self.container.is_registered(
            IConfigurationService
        ):
            self._config_service = self.container.resolve(IConfigurationService)

    def _log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        if self.logger:
            self.logger.debug(message, "WorkflowOrchestrator", **kwargs)

    def _log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        if self.logger:
            self.logger.info(message, "WorkflowOrchestrator", **kwargs)

    def _log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        if self.logger:
            self.logger.warning(message, "WorkflowOrchestrator", **kwargs)

    def _log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        if self.logger:
            self.logger.error(message, "WorkflowOrchestrator", **kwargs)

    def _emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Emit an event if event bus is available."""
        if self.event_bus:
            try:
                event = Event(
                    name=event_name, data=data, source="WorkflowOrchestratorV2"
                )
                # Note: This should be awaited if event_bus.publish is async
                # For now, we'll fire and forget
                asyncio.create_task(self._emit_event_async(event))
            except Exception as e:
                self._log_warning(f"Failed to emit event {event_name}: {e}")

    async def _emit_event_async(self, event: Event) -> None:
        """Async event emission helper."""
        try:
            await self.event_bus.publish(event)
        except Exception as e:
            self._log_warning(f"Failed to emit event async: {e}")

    async def execute_workflow(
        self,
        config: WorkflowConfig,
        input_data: Dict[str, Any],
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """
        Execute a complete workflow.

        Args:
            config: Workflow configuration
            input_data: Input data for the workflow
            progress_callback: Optional progress callback

        Returns:
            Workflow execution result
        """
        # Resolve services on first execution
        self._resolve_services()

        # Generate workflow ID
        workflow_id = str(uuid.uuid4())

        # Create execution context
        context = WorkflowExecutionContext(
            workflow_id=workflow_id,
            input_data=input_data,
            config=config,
            start_time=datetime.now(timezone.utc),
            progress_callback=progress_callback,
            metadata={"steps_executed": 0, "total_tokens": 0},
        )

        # Track active workflow
        self._active_workflows[workflow_id] = context
        self._workflow_results[workflow_id] = []

        self._log_info(f"Starting workflow execution", workflow_id=workflow_id)
        self._emit_event(
            "workflow.started",
            {"workflow_id": workflow_id, "config": config.name},
        )

        try:
            # Execute workflow with performance monitoring
            with self.performance_monitor.measure_operation("workflow_execution"):
                results = []
                total_tokens = 0
                total_steps = len(config.steps)

                # Execute each step
                for i, step in enumerate(config.steps):
                    step_progress = (i + 1) / total_steps * 100

                    # Update progress
                    if progress_callback:
                        await self._safe_progress_callback(
                            progress_callback,
                            step.name,
                            {"status": "running", "progress": step_progress},
                        )

                    self._emit_event(
                        "step.started",
                        {
                            "workflow_id": workflow_id,
                            "step_name": step.name,
                            "step_number": i + 1,
                            "total_steps": total_steps,
                        },
                    )

                    # Execute step
                    step_result = await self.execute_step(step, input_data)
                    self._workflow_results[workflow_id].append(step_result)

                    if step_result.status == WorkflowStepStatus.COMPLETED:
                        results.append(step_result.result or {})
                        total_tokens += step_result.tokens_used

                        # Update progress for completed step
                        if progress_callback:
                            await self._safe_progress_callback(
                                progress_callback,
                                step.name,
                                {
                                    "status": "completed",
                                    "progress": step_progress,
                                    "tokens_used": step_result.tokens_used,
                                },
                            )

                        self._emit_event(
                            "step.completed",
                            {
                                "workflow_id": workflow_id,
                                "step_name": step.name,
                                "duration": step_result.duration,
                                "tokens_used": step_result.tokens_used,
                            },
                        )

                    else:
                        # Step failed
                        error_msg = step_result.error or "Unknown error"
                        self._log_error(f"Step {step.name} failed: {error_msg}")

                        if progress_callback:
                            await self._safe_progress_callback(
                                progress_callback,
                                step.name,
                                {"status": "failed", "error": error_msg},
                            )

                        self._emit_event(
                            "step.failed",
                            {
                                "workflow_id": workflow_id,
                                "step_name": step.name,
                                "error": error_msg,
                            },
                        )

                        # Add error to collector
                        self.error_collector.add_error(
                            Exception(f"Step {step.name} failed: {error_msg}"),
                            {
                                "workflow_id": workflow_id,
                                "step_name": step.name,
                            },
                        )

                        # For now, continue execution even if a step fails
                        # This could be configurable based on step configuration

                # Calculate execution time
                execution_time = (
                    datetime.now(timezone.utc) - context.start_time
                ).total_seconds()

                # Create workflow result
                workflow_result = WorkflowResult(
                    status=WorkflowStatus.COMPLETED,
                    steps_executed=len(results),
                    total_tokens_used=total_tokens,
                    execution_time=execution_time,
                    results=self._merge_step_results(results),
                    errors=(
                        self._get_workflow_errors(workflow_id)
                        if self.error_collector.has_errors()
                        else None
                    ),
                    metadata={
                        **context.metadata,
                        "workflow_id": workflow_id,
                        "performance_metrics": self.performance_monitor.get_all_metrics(),
                    },
                )

                # Final progress update
                if progress_callback:
                    await self._safe_progress_callback(
                        progress_callback,
                        "workflow_completed",
                        {"status": "completed", "progress": 100},
                    )

                self._emit_event(
                    "workflow.completed",
                    {
                        "workflow_id": workflow_id,
                        "status": "completed",
                        "execution_time": execution_time,
                        "total_tokens": total_tokens,
                    },
                )

                self._log_info(
                    f"Workflow completed successfully",
                    workflow_id=workflow_id,
                    steps_executed=workflow_result.steps_executed,
                    tokens_used=workflow_result.total_tokens_used,
                    execution_time=workflow_result.execution_time,
                )

                return workflow_result

        except Exception as e:
            # Workflow failed
            execution_time = (
                datetime.now(timezone.utc) - context.start_time
            ).total_seconds()
            error_msg = str(e)

            self._log_error(f"Workflow execution failed: {error_msg}", exc_info=True)
            self.error_collector.add_error(e, {"workflow_id": workflow_id})

            # Final progress update for failure
            if progress_callback:
                await self._safe_progress_callback(
                    progress_callback,
                    "workflow_failed",
                    {"status": "failed", "error": error_msg},
                )

            self._emit_event(
                "workflow.failed",
                {
                    "workflow_id": workflow_id,
                    "error": error_msg,
                    "execution_time": execution_time,
                },
            )

            return WorkflowResult(
                status=WorkflowStatus.FAILED,
                steps_executed=len(self._workflow_results.get(workflow_id, [])),
                total_tokens_used=0,
                execution_time=execution_time,
                results={},
                errors=[error_msg],
                metadata={
                    "workflow_id": workflow_id,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        finally:
            # Cleanup
            self._cleanup_workflow(workflow_id)

    async def execute_step(
        self, step: WorkflowStep, input_data: Dict[str, Any]
    ) -> WorkflowStepResult:
        """
        Execute a single workflow step.

        Args:
            step: Workflow step to execute
            input_data: Input data for the step

        Returns:
            Step execution result
        """
        # Resolve services on first step execution
        self._resolve_services()

        step_start_time = datetime.now(timezone.utc)

        self._log_info(f"Executing step: {step.name}")

        try:
            # Validate step configuration
            self._validate_step_config(step)

            # Resolve LLM provider
            if not self._llm_factory:
                raise RuntimeError("LLM factory not available")

            llm_provider = self._llm_factory.get_provider(step.provider)

            # Create LLM request
            request = await self._create_llm_request(step, input_data)

            # Execute with retry if configured
            if self.retry_service and step.retry_attempts > 1:
                from .interfaces import RetryPolicy

                retry_policy = RetryPolicy(
                    max_attempts=step.retry_attempts,
                    base_delay=1.0,
                    max_delay=step.timeout,
                    backoff_factor=2.0,
                )

                response = await self.retry_service.execute_with_retry(
                    llm_provider.generate, retry_policy, request
                )
            else:
                response = await llm_provider.generate(request)

            # Parse and validate response
            parsed_result = await self._parse_llm_response(response, step)

            # Calculate duration
            duration = (datetime.now(timezone.utc) - step_start_time).total_seconds()

            # Record metrics
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "workflow_step_executed",
                    tags={"step_name": step.name, "provider": step.provider},
                )
                self.metrics_collector.record_timing(
                    "workflow_step_duration",
                    duration,
                    tags={"step_name": step.name},
                )

            return WorkflowStepResult(
                step_name=step.name,
                status=WorkflowStepStatus.COMPLETED,
                result=parsed_result,
                duration=duration,
                tokens_used=response.tokens_used or 0,
                metadata={
                    "provider": step.provider,
                    "model": response.model,
                    "temperature": step.temperature,
                },
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - step_start_time).total_seconds()
            error_msg = str(e)

            self._log_error(f"Step {step.name} failed: {error_msg}", exc_info=True)

            # Record error metrics
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "workflow_step_failed",
                    tags={
                        "step_name": step.name,
                        "error_type": type(e).__name__,
                    },
                )

            return WorkflowStepResult(
                step_name=step.name,
                status=WorkflowStepStatus.FAILED,
                error=error_msg,
                duration=duration,
                tokens_used=0,
                metadata={
                    "provider": step.provider,
                    "error_type": type(e).__name__,
                },
            )

    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """
        Get the status of a running workflow.

        Args:
            workflow_id: Workflow ID to check

        Returns:
            Current workflow status or None if not found
        """
        context = self._active_workflows.get(workflow_id)
        if not context:
            return None

        # Check if workflow is still in active workflows
        results = self._workflow_results.get(workflow_id, [])

        # If workflow has results, it might be completed or failed
        if results:
            # Check if any steps failed
            failed_steps = [r for r in results if r.status == WorkflowStepStatus.FAILED]
            if failed_steps:
                return WorkflowStatus.FAILED

            # Check if all steps completed
            completed_steps = [
                r for r in results if r.status == WorkflowStepStatus.COMPLETED
            ]
            if len(completed_steps) == len(context.config.steps):
                return WorkflowStatus.COMPLETED

        return WorkflowStatus.RUNNING

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: Workflow ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        if workflow_id not in self._active_workflows:
            return False

        self._active_workflows[workflow_id]

        # Mark as cancelled (implementation depends on specific cancellation strategy)
        self._log_info(f"Cancelling workflow: {workflow_id}")
        self._emit_event("workflow.cancelled", {"workflow_id": workflow_id})

        # Cleanup workflow
        self._cleanup_workflow(workflow_id)

        return True

    def list_workflows(self) -> List[str]:
        """
        List all available workflow configurations.

        Returns:
            List of workflow configuration names
        """
        if not self._config_service:
            return []

        # This would depend on how workflows are stored/registered
        # For now, return a placeholder list
        return [
            "translation_hybrid",
            "translation_reasoning",
            "translation_non_reasoning",
        ]

    async def _safe_progress_callback(
        self,
        callback: Callable[[str, Dict[str, Any]], None],
        step_name: str,
        data: Dict[str, Any],
    ) -> None:
        """Safely call progress callback without affecting main execution."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(step_name, data)
            else:
                callback(step_name, data)
        except Exception as e:
            self._log_warning(f"Progress callback failed: {e}")

    def _validate_step_config(self, step: WorkflowStep) -> None:
        """Validate workflow step configuration."""
        if not step.provider:
            raise ValueError(f"Step {step.name} missing provider")

        if not step.model:
            raise ValueError(f"Step {step.name} missing model")

        if not step.prompt_template:
            raise ValueError(f"Step {step.name} missing prompt template")

    async def _create_llm_request(
        self, step: WorkflowStep, input_data: Dict[str, Any]
    ) -> LLMRequest:
        """Create LLM request from step configuration and input data."""
        # Render prompt template
        if not self._prompt_service:
            raise RuntimeError("Prompt service not available")

        system_prompt, user_prompt = await self._prompt_service.render_prompt(
            step.prompt_template, input_data
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})

        return LLMRequest(
            messages=messages,
            temperature=step.temperature,
            max_tokens=step.max_tokens,
            model=step.model,
            timeout=step.timeout,
        )

    async def _parse_llm_response(
        self, response: LLMResponse, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Parse and validate LLM response."""
        if not self._output_parser:
            # Fallback to basic parsing
            return {"content": response.content}

        try:
            parsed = self._output_parser.parse_xml(
                response.content, step.required_fields
            )

            if parsed.result_type.value == "failed":
                raise ValueError(f"Failed to parse LLM response: {parsed.errors}")

            return parsed.content

        except Exception as e:
            self._log_warning(f"Failed to parse LLM response: {e}, using raw content")
            return {"content": response.content}

    def _merge_step_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple workflow steps."""
        merged = {}

        for result in results:
            if isinstance(result, dict):
                merged.update(result)

        return merged

    def _get_workflow_errors(self, workflow_id: str) -> List[str]:
        """Get all errors for a workflow."""
        errors = []

        # Get errors from step results
        step_results = self._workflow_results.get(workflow_id, [])
        for result in step_results:
            if result.error:
                errors.append(f"{result.step_name}: {result.error}")

        # Get errors from error collector
        workflow_errors = self.error_collector.get_errors()
        for error in workflow_errors:
            if error.context and error.context.get("workflow_id") == workflow_id:
                errors.append(f"{error.error_type}: {error.message}")

        return errors

    def _cleanup_workflow(self, workflow_id: str) -> None:
        """Clean up workflow resources."""
        # Remove from active workflows
        self._active_workflows.pop(workflow_id, None)

        # Keep results for some time for status queries, then cleanup
        # This could be configurable

        # Reset performance metrics for this workflow
        self.performance_monitor.reset_metrics()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        return {
            "performance_monitor": self.performance_monitor.get_all_metrics(),
            "error_collector": {
                "has_errors": self.error_collector.has_errors(),
                "error_count": len(self.error_collector.get_errors()),
                "error_summary": self.error_collector.get_error_summary(),
            },
            "active_workflows": len(self._active_workflows),
            "resource_manager": {
                "managed_resources": len(self.resource_manager.resources)
            },
        }

    async def cleanup(self) -> None:
        """Cleanup all resources and finalize monitoring."""
        self._log_info("Cleaning up WorkflowOrchestratorV2")

        # Cancel all active workflows
        for workflow_id in list(self._active_workflows.keys()):
            await self.cancel_workflow(workflow_id)

        # Cleanup resources
        self.resource_manager.cleanup_all()

        # Final metrics
        if self.metrics_collector:
            final_metrics = self.get_performance_metrics()
            self._log_info("Final performance metrics", **final_metrics)
