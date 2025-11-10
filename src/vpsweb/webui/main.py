"""
Phase 3C: Refactored Main Application Router with Service Layer.

This module provides a clean separation of concerns using dependency injection
and the service layer pattern. It replaces the monolithic main.py architecture.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette import EventSourceResponse
import asyncio
import json
import time

from .services.interfaces import (
    IPoemServiceV2,
    ITranslationServiceV2,
    IWorkflowServiceV2,
    IStatisticsServiceV2,
    ITemplateServiceV2,
    IExceptionHandlerServiceV2,
    IPerformanceServiceV2,
    ISSEServiceV2,
    IConfigServiceV2,
)
from .services.services import (
    PoemServiceV2,
    TranslationServiceV2,
    PoetServiceV2,
    WorkflowServiceV2,
    StatisticsServiceV2,
    TemplateServiceV2,
    ExceptionHandlerServiceV2,
    PerformanceServiceV2,
    TaskManagementServiceV2,
    SSEServiceV2,
    ConfigServiceV2,
)
from .services.interfaces import ITaskManagementServiceV2
from vpsweb.core.container import DIContainer
from vpsweb.webui.container import container
from sqlalchemy.orm import Session
from vpsweb.repository.service import RepositoryWebService
from vpsweb.repository.crud import RepositoryService
from vpsweb.repository.database import get_db
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import WorkflowConfig, WorkflowMode
from vpsweb.utils.config_loader import load_config
from vpsweb.webui.api import poems, translations, statistics, poets, wechat, workflow
from .task_models import TaskStatus, TaskStatusEnum

from vpsweb.utils.storage import StorageHandler
import logging


async def create_translation_events_from_app_state(request: Request, task_id: str):
    """
    Create translation progress events from app.state.tasks (like original working design).
    This function reads TaskStatus objects directly from app.state.tasks and streams updates.
    """
    import asyncio
    import json
    import time

    try:
        # Get app from request to access app.state.tasks
        app = request.app

        # Initialize app.state.tasks if not present
        if not hasattr(app.state, "tasks"):
            app.state.tasks = {}

        # Debug: Print app.state.tasks info
        print(
            f"[SSE APP_STATE] Looking for task {task_id} in app.state.tasks. Total tasks: {len(app.state.tasks)}"
        )
        print(f"[SSE APP_STATE] Available task IDs: {list(app.state.tasks.keys())}")

        # Check if task exists in app.state.tasks
        if task_id not in app.state.tasks:
            print(f"[SSE APP_STATE] Task {task_id} not found in app.state.tasks")
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "task_id": task_id,
                        "message": "Task not found",
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                ),
            }
            return

        task_status = app.state.tasks[task_id]
        print(
            f"[SSE APP_STATE] SSE connection established for task {task_id}, current status: {task_status.get('status')}, progress: {task_status.get('progress', 0)}%"
        )

        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps(
                {
                    "task_id": task_id,
                    "status": task_status.get("status", "unknown"),
                    "progress": task_status.get("progress", 0),
                    "timestamp": asyncio.get_event_loop().time(),
                }
            ),
        }

        # Send current task status
        yield {
            "event": "status",
            "data": json.dumps(
                {
                    "task_id": task_id,
                    "status": task_status.get("status", "unknown"),
                    "progress": task_status.get("progress", 0),
                    "current_step": task_status.get("current_step"),
                    "step_states": task_status.get("step_states", {}),
                    "step_progress": task_status.get("step_progress", {}),
                    "timestamp": asyncio.get_event_loop().time(),
                }
            ),
        }

        # If task is already completed, send completion event and exit
        if task_status.get("status") == "completed":
            yield {
                "event": "completed",
                "data": json.dumps(
                    {
                        "task_id": task_id,
                        "message": "✅ Translation workflow completed successfully!",
                        "progress": 100,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                ),
            }
            return

        # Listen for task status changes by polling app.state.tasks
        last_status = task_status.get("status")
        last_progress = task_status.get("progress", 0)
        last_step = task_status.get("current_step")

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                print(f"[SSE APP_STATE] Client disconnected from task {task_id}")
                break

            # Get current task status from app.state.tasks
            current_task = app.state.tasks.get(task_id)
            if not current_task:
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {
                            "task_id": task_id,
                            "message": "Task disappeared from app.state.tasks",
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    ),
                }
                break

            # Check for status changes
            status_changed = current_task.get("status") != last_status
            progress_changed = current_task.get("progress", 0) != last_progress
            step_changed = current_task.get("current_step") != last_step

            if status_changed or progress_changed or step_changed:
                print(
                    f"[SSE APP_STATE] Task {task_id} status changed: {current_task.get('status')}, progress: {current_task.get('progress', 0)}%, step: {current_task.get('current_step')}"
                )

                # Send update event
                yield {
                    "event": "status",
                    "data": json.dumps(
                        {
                            "task_id": task_id,
                            "status": current_task.get("status"),
                            "progress": current_task.get("progress", 0),
                            "current_step": current_task.get("current_step"),
                            "step_states": current_task.get("step_states", {}),
                            "step_progress": current_task.get("step_progress", {}),
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    ),
                }

                # Send step-specific events
                if step_changed and last_step != current_task.get("current_step"):
                    # Send step_change event (frontend expects this)
                    yield {
                        "event": "step_change",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "status": current_task.get("status"),
                                "progress": current_task.get("progress", 0),
                                "current_step": current_task.get("current_step"),
                                "step_states": current_task.get("step_states", {}),
                                "step_progress": current_task.get("step_progress", {}),
                                "step_details": current_task.get("step_details", {}),
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        ),
                    }

                    # Create step to number mapping
                    step_to_number = {
                        "Initial Translation": 1,
                        "Editor Review": 2,
                        "Translator Revision": 3,
                    }

                    if current_task.get("step_states") and current_task.get(
                        "current_step"
                    ) in current_task.get("step_states", {}):
                        step_state = current_task.get("step_states", {})[
                            current_task.get("current_step")
                        ]
                        step_number = step_to_number.get(
                            current_task.get("current_step"), 1
                        )

                        if step_state == "running":
                            yield {
                                "event": "step_start",
                                "data": json.dumps(
                                    {
                                        "task_id": task_id,
                                        "step": step_number,
                                        "message": f"Step started: {current_task.get('current_step')}",
                                        "timestamp": asyncio.get_event_loop().time(),
                                    }
                                ),
                            }
                        elif step_state == "completed":
                            yield {
                                "event": "step_complete",
                                "data": json.dumps(
                                    {
                                        "task_id": task_id,
                                        "step": step_number,
                                        "message": f"Step completed: {current_task.get('current_step')}",
                                        "timestamp": asyncio.get_event_loop().time(),
                                    }
                                ),
                            }

                # If task completed, send completion event
                if current_task.get("status") == "completed":
                    yield {
                        "event": "completed",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "message": "✅ Translation workflow completed successfully!",
                                "progress": 100,
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        ),
                    }
                    break
                elif current_task.get("status") == "failed":
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {
                                "task_id": task_id,
                                "message": f"Translation failed: {current_task.get('current_step')}",
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        ),
                    }
                    break

                # Update last known values
                last_status = current_task.get("status")
                last_progress = current_task.get("progress", 0)
                last_step = current_task.get("current_step")

            # Wait before next check (poll every 500ms for responsiveness)
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"[SSE APP_STATE] Error generating events for task {task_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps(
                {
                    "task_id": task_id,
                    "message": f"Error: {str(e)}",
                    "timestamp": asyncio.get_event_loop().time(),
                }
            ),
        }


class ApplicationRouterV2:
    """
    Refactored main application router using dependency injection
    and service layer pattern for clean separation of concerns.
    """

    def __init__(
        self,
        app: FastAPI,
        container: DIContainer,
        poem_service: IPoemServiceV2,
        translation_service: ITranslationServiceV2,
        workflow_service: IWorkflowServiceV2,
        statistics_service: IStatisticsServiceV2,
        template_service: ITemplateServiceV2,
        error_handler: IExceptionHandlerServiceV2,
        performance_service: IPerformanceServiceV2,
        sse_service: ISSEServiceV2,
        config_service: IConfigServiceV2,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the application router with injected dependencies.

        Args:
            app: The FastAPI application instance.
            container: DI container for service resolution
            poem_service: Service for poem-related operations
            translation_service: Service for translation-related operations
            workflow_service: Service for workflow orchestration
            statistics_service: Service for analytics and statistics
            template_service: Service for template rendering
            error_handler: Service for error handling and responses
            performance_service: Service for performance monitoring
            sse_service: Service for Server-Sent Events
            config_service: Service for configuration management
            logger: Logger instance
        """
        self.app = app
        self.container = container
        self.poem_service = poem_service
        self.translation_service = translation_service
        self.workflow_service = workflow_service
        self.statistics_service = statistics_service
        self.template_service = template_service
        self.error_handler = error_handler
        self.performance_service = performance_service
        self.sse_service = sse_service
        self.config_service = config_service
        self.logger = logger or logging.getLogger(__name__)

        # Initialize translation task manager for SSE

        self._configure_app()

    def _configure_app(self):
        """Configure the FastAPI application."""
        # Set up lifecycle management
        self.app.on_event("startup")(self._startup_event)
        self.app.on_event("shutdown")(self._shutdown_event)

        # Add middleware
        self.app.middleware("http")(self._performance_middleware)
        self.app.add_exception_handler(Exception, self._general_exception_handler)

        # Add routes
        self._add_routes(self.app)

        # Include API routers
        self._include_api_routers(self.app)

        # Mount static files
        self._mount_static_files(self.app)

    async def _startup_event(self):
        """Application startup event."""
        self.logger.info("VPSWeb Application starting up...")

        # Initialize any startup tasks
        # For example: start background task cleanup, validate services, etc.

        self.logger.info("VPSWeb Application startup complete")

    async def _shutdown_event(self):
        """Application shutdown event."""
        self.logger.info("VPSWeb Application shutting down...")

        # Cleanup resources
        # For example: cleanup tasks, close connections, etc.

        self.logger.info("VPSWeb Application shutdown complete")

    async def _performance_middleware(self, request: Request, call_next):
        """Performance monitoring middleware."""
        import time

        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate processing time
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Log performance metrics
        await self.performance_service.log_request_performance(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=process_time,
            additional_data={
                "user_agent": request.headers.get("user-agent"),
                "content_length": response.headers.get("content-length"),
            },
        )

        # Add performance header
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        return response

    async def _general_exception_handler(self, request: Request, exc: Exception):
        """General exception handler using the error service."""
        error_id = self.error_handler.generate_error_id()

        # Determine if this is a web request
        is_web_request = self._is_web_request(request)

        # Handle the error using the error service
        return await self.error_handler.handle_general_error(
            error=exc, request=request, error_id=error_id, is_web_request=is_web_request
        )

    def _add_routes(self, app: FastAPI):
        """Add application routes."""

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """Dashboard - List all poems in the repository."""
            try:
                # Get poems using service layer
                poems_result = await self.poem_service.get_poem_list(skip=0, limit=50)

                # Render template
                template_context = {
                    "request": request,
                    "poems": poems_result["poems"],
                    "total_count": poems_result["total_count"],
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "index.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poems", response_class=HTMLResponse)
        async def poems_list(request: Request):
            """Poems listing page with search and filtering."""
            try:
                # Render template
                template_context = {
                    "request": request,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poems_list.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poets", response_class=HTMLResponse)
        async def poets_list(request: Request):
            """Display list of all poets with statistics and activity metrics."""
            try:
                # Get query parameters
                search = request.query_params.get("search", "")
                sort_by = request.query_params.get("sort_by", "name")
                sort_order = request.query_params.get("sort_order", "asc")

                # Get poets data with filters
                poets_data = self.poem_service.repository_service.get_all_poets(
                    skip=0,
                    limit=50,
                    search=search if search else None,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    min_poems=None,
                    min_translations=None,
                )

                # Keep datetime objects for template rendering (template will handle formatting)

                template_context = {
                    "request": request,
                    "poets": poets_data["poets"],
                    "total_count": poets_data["total_count"],
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poets_list.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/translations", response_class=HTMLResponse)
        async def translations_list(request: Request):
            """List all translations with filtering options."""
            try:
                # Get query parameters
                search = request.query_params.get("search", "")
                sort_by = request.query_params.get("sort_by", "created_at")
                sort_order = request.query_params.get("sort_order", "desc")

                # Get translations data
                translations_data = (
                    self.poem_service.repository_service.repo.translations.get_multi(
                        skip=0, limit=50
                    )
                )

                template_context = {
                    "request": request,
                    "translations": translations_data,
                    "search": search,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "translations_list.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poems/new", response_class=HTMLResponse)
        async def new_poem(request: Request):
            """New poem creation page."""
            try:
                template_context = {
                    "request": request,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poem_new.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poems/{poem_id}", response_class=HTMLResponse)
        async def poem_detail(
            request: Request, poem_id: str, db: Session = Depends(get_db)
        ):
            """Individual poem detail page with translations."""
            try:
                # Use same pattern as API - fresh database session via dependency injection
                repository_service = RepositoryService(db)
                poem = repository_service.poems.get_by_id(poem_id)
                if not poem:
                    raise Exception(f"Poem with ID {poem_id} not found")

                # Convert to dictionary format expected by templates
                poem_data = {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "content": poem.original_text,
                    "metadata_json": poem.metadata_json,
                    "created_at": (
                        poem.created_at.isoformat() if poem.created_at else None
                    ),
                    "updated_at": (
                        poem.updated_at.isoformat() if poem.updated_at else None
                    ),
                    "translation_count": poem.translation_count,
                    "ai_translation_count": poem.ai_translation_count,
                    "human_translation_count": poem.human_translation_count,
                }

                template_context = {
                    "request": request,
                    "poem_id": poem_id,
                    "poem": poem_data,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poem_detail.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        # Original working design SSE endpoints - reusing proven callback-based approach
        @app.get("/api/v1/workflow/tasks/{task_id}/stream")
        async def stream_workflow_task_status(
            task_id: str,
            request: Request,
        ):
            """
            Stream real-time workflow task progress using Server-Sent Events (SSE)

            This endpoint provides real-time updates for translation workflow progress
            through FastAPI app.state, reusing the original working design with heartbeat support.
            """

            async def event_generator():
                import json  # Local import to avoid scoping issues

                # Check if task exists in app.state
                if not hasattr(app.state, "tasks") or task_id not in app.state.tasks:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Task not found"}),
                    }
                    return

                # Send initial status
                task_status = app.state.tasks[task_id]
                initial_status = task_status.to_dict()
                yield {"event": "status", "data": json.dumps(initial_status)}
                print(
                    f"📡 [SSE] Initial status sent for task {task_id}: {initial_status['status']} - {initial_status['current_step']}"
                )

                # Stream for updates with real-time app.state access (original working design)
                max_iterations = (
                    3000  # 10 minutes with 0.2-second intervals (600 / 0.2 = 3000)
                )
                last_status = None
                consecutive_errors = 0
                max_consecutive_errors = 5
                last_update_time = time.time()

                for i in range(max_iterations):
                    # Check if client disconnected
                    if await request.is_disconnected():
                        print(f"🔌 Client disconnected from task {task_id} SSE stream")
                        break

                    await asyncio.sleep(
                        0.2
                    )  # Check every 200ms for better responsiveness (faster than before)

                    try:
                        # Reset consecutive errors counter on successful iteration
                        consecutive_errors = 0
                        current_time = time.time()

                        # Get current task status from app.state
                        if task_id in app.state.tasks:
                            current_task = app.state.tasks[task_id]
                            current_dict = current_task.to_dict()

                            # Enhanced change detection - focus on step changes, not progress percentage
                            has_progress_change = (
                                last_status is None
                                or current_dict["status"] != last_status["status"]
                                or current_dict["current_step"]
                                != last_status["current_step"]
                            )

                            # Specific step change detection - check for step status transitions
                            has_step_change = False
                            if last_status is not None:
                                current_step_details = current_dict.get(
                                    "step_details", {}
                                )
                                last_step_details = last_status.get("step_details", {})

                                # Check if current step status changed (running -> completed)
                                if current_step_details.get(
                                    "step_status"
                                ) != last_step_details.get("step_status"):
                                    has_step_change = True
                                    print(
                                        f"🔍 [SSE] Step status change detected: {last_step_details.get('step_status')} -> {current_step_details.get('step_status')}"
                                    )

                                # Check if any step states changed
                                current_step_states = current_dict.get(
                                    "step_states", {}
                                )
                                last_step_states = last_status.get("step_states", {})
                                if current_step_states != last_step_states:
                                    has_step_change = True
                                    print(f"🔍 [SSE] Step states changed detected")

                            # Additional check for task timestamp changes (more sensitive detection)
                            has_time_change = (
                                last_status is not None
                                and "updated_at" in current_dict
                                and "updated_at" in last_status
                                and current_dict["updated_at"]
                                != last_status["updated_at"]
                            )

                            # Send update if any significant field changed OR timestamp changed OR step changed
                            if (
                                has_progress_change
                                or has_step_change
                                or has_time_change
                            ):
                                last_status = current_dict.copy()
                                last_update_time = current_time

                                # Determine event type based on what changed
                                event_type = "status"
                                if has_step_change and last_status is not None:
                                    event_type = "step_change"

                                yield {
                                    "event": event_type,
                                    "data": json.dumps(current_dict),
                                }
                                step_states = current_dict.get("step_states", {})
                                current_step_state = step_states.get(
                                    current_dict["current_step"], "unknown"
                                )
                                step_details = current_dict.get("step_details", {})
                                step_status = step_details.get("step_status", "unknown")

                                print(
                                    f"📡 [SSE] {event_type.upper()} sent for task {task_id}: {current_dict['status']} - {current_dict['current_step']} ({step_status})"
                                )

                            # Stop streaming if task is complete - but add a brief delay to ensure final state is captured
                            if current_task.status.value in ["completed", "failed"]:
                                # Wait a moment to ensure the final state is stable
                                await asyncio.sleep(0.5)

                                # Get final state one more time
                                final_dict = current_task.to_dict()
                                yield {
                                    "event": current_task.status.value,
                                    "data": json.dumps(final_dict),
                                }
                                print(
                                    f"📡 [SSE] Final status sent for task {task_id}: {current_task.status.value} - {final_dict['current_step']}"
                                )
                                break

                            # Force periodic updates every 5 seconds to ensure connection stays alive (heartbeat)
                            if current_time - last_update_time > 5.0:
                                last_update_time = current_time
                                yield {
                                    "event": "heartbeat",
                                    "data": json.dumps({"timestamp": current_time}),
                                }

                        else:
                            # Task was removed from app.state
                            yield {
                                "event": "error",
                                "data": json.dumps(
                                    {"message": "Task disappeared from memory"}
                                ),
                            }
                            break

                    except asyncio.CancelledError:
                        print(f"⏹️ SSE stream cancelled for task {task_id}")
                        break
                    except Exception as e:
                        consecutive_errors += 1
                        print(
                            f"❌ [SSE] Error {consecutive_errors}/{max_consecutive_errors} in stream for task {task_id}: {str(e)}"
                        )

                        if consecutive_errors >= max_consecutive_errors:
                            yield {
                                "event": "error",
                                "data": json.dumps(
                                    {"message": f"SSE stream error: {str(e)}"}
                                ),
                            }
                            break

                        # Continue after a brief delay for non-critical errors
                        await asyncio.sleep(1.0)

                # Send completion event if timed out
                if i >= max_iterations - 1:
                    yield {
                        "event": "timeout",
                        "data": json.dumps(
                            {"message": "Workflow timed out after 10 minutes"}
                        ),
                    }

                print(f"🏁 SSE stream ended for task {task_id} after {i+1} iterations")

            return EventSourceResponse(
                event_generator(),
                ping=30,  # Ping every 30 seconds to keep connection alive (reduced frequency)
                send_timeout=60,  # Timeout for sending events
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

        @app.get("/poems/{poem_id}/compare", response_class=HTMLResponse)
        async def poem_compare(request: Request, poem_id: str):
            """Display comparison view for translations of a specific poem."""
            try:
                # Get poem data directly from repository
                poem = self.poem_service.repository_service.repo.poems.get_by_id(
                    poem_id
                )
                if not poem:
                    raise Exception(f"Poem with ID {poem_id} not found")

                # Convert to dictionary format expected by templates
                poem_data = {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "original_text": poem.original_text,
                    "metadata_json": poem.metadata_json,
                    "created_at": (
                        poem.created_at.isoformat() if poem.created_at else None
                    ),
                    "updated_at": (
                        poem.updated_at.isoformat() if poem.updated_at else None
                    ),
                    "translation_count": poem.translation_count,
                    "ai_translation_count": poem.ai_translation_count,
                    "human_translation_count": poem.human_translation_count,
                }

                # Get translations for this poem using the repository service through poem_service
                translations = (
                    self.poem_service.repository_service.repo.translations.get_multi(
                        poem_id=poem_id, limit=100
                    )
                )

                template_context = {
                    "request": request,
                    "poem_id": poem_id,
                    "poem": poem_data,
                    "translations": translations,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poem_compare.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poems/{poem_id}/translate", response_class=HTMLResponse)
        async def poem_translate(request: Request, poem_id: str):
            """Display translation creation page for a specific poem."""
            try:
                # Get poem data directly from repository
                poem = self.poem_service.repository_service.repo.poems.get_by_id(
                    poem_id
                )
                if not poem:
                    raise Exception(f"Poem with ID {poem_id} not found")

                # Convert to dictionary format expected by templates
                poem_data = {
                    "id": poem.id,
                    "poet_name": poem.poet_name,
                    "poem_title": poem.poem_title,
                    "source_language": poem.source_language,
                    "content": poem.original_text,
                    "metadata_json": poem.metadata_json,
                    "created_at": (
                        poem.created_at.isoformat() if poem.created_at else None
                    ),
                    "updated_at": (
                        poem.updated_at.isoformat() if poem.updated_at else None
                    ),
                    "translation_count": poem.translation_count,
                    "ai_translation_count": poem.ai_translation_count,
                    "human_translation_count": poem.human_translation_count,
                }

                template_context = {
                    "request": request,
                    "poem_id": poem_id,
                    "poem": poem_data,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poem_detail.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/translations/{translation_id}/notes", response_class=HTMLResponse)
        async def translation_notes(request: Request, translation_id: str):
            """Display translation notes and AI workflow details for a specific translation."""
            try:
                # Get translation data
                translation_data = (
                    await self.translation_service.get_translation_detail(
                        translation_id
                    )
                )
                if not translation_data:
                    raise Exception(f"Translation with ID {translation_id} not found")

                # Get workflow steps for AI translations
                workflow_steps = []
                translation = translation_data.get("translation")
                if (
                    translation
                    and translation.translator_type.lower() == "ai"
                    and translation.has_workflow_steps
                ):
                    workflow_steps = await self.translation_service.get_workflow_steps(
                        translation_id
                    )

                # Calculate workflow data for Performance Summary
                workflow_data = None
                if workflow_steps:
                    total_tokens = sum(
                        step.get("tokens_used", 0) or 0 for step in workflow_steps
                    )
                    total_cost = sum(
                        step.get("cost", 0) or 0 for step in workflow_steps
                    )
                    total_duration = sum(
                        step.get("duration_seconds", 0) or 0 for step in workflow_steps
                    )

                    workflow_data = {
                        "total_tokens": total_tokens,
                        "total_cost": total_cost,
                        "total_duration": total_duration,
                    }

                template_context = {
                    "request": request,
                    "translation_id": translation_id,
                    "translation": translation_data.get("translation"),
                    "poem": translation_data.get("poem"),
                    "workflow_steps": workflow_steps,
                    "workflow_data": workflow_data,
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "translation_notes.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/poets/{poet_name}", response_class=HTMLResponse)
        async def poet_detail(request: Request, poet_name: str):
            """Display poet page with their poems and statistics."""
            try:
                # Get poet statistics using repository service
                stats = self.poem_service.repository_service.get_poet_statistics(
                    poet_name
                )

                # Get poet's poems with filters
                poems_data = self.poem_service.repository_service.get_poems_by_poet(
                    poet_name=poet_name,
                    skip=0,
                    limit=20,
                    language=None,
                    has_translations=None,
                    sort_by="title",
                    sort_order="asc",
                )

                # Get poet's recent translations
                translations_data = (
                    self.poem_service.repository_service.get_translations_by_poet(
                        poet_name=poet_name,
                        skip=0,
                        limit=5,
                        sort_by="created_at",
                        sort_order="desc",
                    )
                )

                template_context = {
                    "request": request,
                    "poet_name": poet_name,
                    "poem_stats": stats["poem_statistics"],
                    "translation_stats": stats["translation_statistics"],
                    "poems": poems_data["poems"],
                    "total_poems": poems_data["total_count"],
                    "recent_translations": translations_data["translations"],
                    "title": await self.config_service.get_setting(
                        "app_name", "VPSWeb Repository"
                    ),
                }

                return await self.template_service.render_template(
                    "poet_detail.html", template_context, request
                )

            except Exception as e:
                return await self.error_handler.handle_general_error(
                    error=e,
                    request=request,
                    error_id=self.error_handler.generate_error_id(),
                    is_web_request=True,
                )

        @app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring."""
            try:
                # Get basic health status from services
                app_name = await self.config_service.get_setting("app_name", "VPSWeb")
                app_version = await self.config_service.get_setting("version", "0.3.12")

                return {
                    "status": "healthy",
                    "app_name": app_name,
                    "version": app_version,
                    "services": {
                        "poem_service": "healthy",
                        "translation_service": "healthy",
                        "workflow_service": "healthy",
                        "statistics_service": "healthy",
                    },
                }

            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": self._get_current_timestamp(),
                    },
                )

        @app.get("/dashboard/stats")
        async def dashboard_statistics():
            """Get statistics for the dashboard."""
            try:
                # Get comprehensive statistics
                stats = await self.statistics_service.get_repository_statistics()

                # Add dashboard-specific metrics
                dashboard_stats = {
                    **stats,
                    "recent_activity": {
                        "last_24h": await self._get_recent_activity_count(24),
                        "last_7d": await self._get_recent_activity_count(7 * 24),
                    },
                    "system_info": {
                        "version": await self.config_service.get_setting("version"),
                        "debug": await self.config_service.get_setting("debug", False),
                    },
                }

                return dashboard_stats

            except Exception as e:
                self.logger.error(f"Dashboard statistics error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to load dashboard statistics"},
                )

        @app.get("/api/v1/translations/{task_id}/events")
        async def translation_events(request: Request, task_id: str):
            """SSE endpoint for real-time translation progress updates from app.state.tasks (like original working design)."""
            return EventSourceResponse(
                create_translation_events_from_app_state(request, task_id),
                ping=15,  # Send ping every 15 seconds
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

    def _include_api_routers(self, app: FastAPI):
        """Include API routers."""
        app.include_router(poems.router, prefix="/api/v1/poems", tags=["poems"])
        app.include_router(
            translations.router, prefix="/api/v1/translations", tags=["translations"]
        )
        app.include_router(
            statistics.router, prefix="/api/v1/statistics", tags=["statistics"]
        )
        app.include_router(poets.router, prefix="/api/v1/poets", tags=["poets"])
        app.include_router(wechat.router, prefix="/api/v1/wechat", tags=["wechat"])
        app.include_router(
            workflow.router, prefix="/api/v1/workflow", tags=["workflow"]
        )

    def _mount_static_files(self, app: FastAPI):
        """Mount static file directories."""
        try:
            # Mount static files directory
            app.mount(
                "/static",
                StaticFiles(directory="src/vpsweb/webui/web/static"),
                name="static",
            )
        except Exception as e:
            self.logger.warning(f"Failed to mount static files: {e}")

    def _is_web_request(self, request: Request) -> bool:
        """Determine if this is a web request (browser request)."""
        accept_header = request.headers.get("accept", "")
        path = str(request.url.path)

        # Consider it a web request if:
        # 1. Accept header contains text/html
        # 2. Path starts with / (not /api/)
        # 3. No Accept header (likely browser)
        return (
            "text/html" in accept_header
            or (path.startswith("/") and not path.startswith("/api/"))
            or not accept_header
        )

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()

    async def _get_recent_activity_count(self, hours: int) -> int:
        """Get activity count for the last N hours."""
        try:
            from datetime import datetime, timezone, timedelta

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)

            # This would use the statistics service
            # For now, return placeholder
            return 0

        except Exception as e:
            self.logger.error(f"Error getting recent activity: {e}")
            return 0

    def get_app(self) -> FastAPI:
        """Get the configured FastAPI application."""
        return self.app


class ApplicationFactoryV2:
    """
    Factory for creating the VPSWeb application with all dependencies
    properly configured and injected.
    """

    @staticmethod
    def create_application(
        repository_service: Optional[RepositoryWebService] = None,
        logger: Optional[logging.Logger] = None,
    ) -> FastAPI:
        """
        Create and configure the VPSWeb application.

        Args:
            repository_service: Repository service instance (optional for testing)
            logger: Logger instance (optional)

        Returns:
            Configured FastAPI application
        """
        # Initialize logger
        app_logger = logger or logging.getLogger(__name__)

        # Create FastAPI app instance first to access app.state
        app = FastAPI(
            title="VPSWeb Repository v0.3.12",
            description="Poetry translation repository with AI integration",
            version="0.3.12",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        app.state.tasks = {}

        # Create DI container and clear any existing registrations
        container.clear()
        app.container = container

        # Create and register TaskManagementServiceV2 instance
        task_service = TaskManagementServiceV2(
            tasks_store=app.state.tasks, logger=app_logger
        )
        container.register_instance(ITaskManagementServiceV2, task_service)

        # Register core services as singletons
        container.register_singleton(IPerformanceServiceV2, PerformanceServiceV2)
        container.register_singleton(
            IExceptionHandlerServiceV2, ExceptionHandlerServiceV2
        )
        container.register_singleton(ISSEServiceV2, SSEServiceV2)
        container.register_singleton(IConfigServiceV2, ConfigServiceV2)

        # Resolve core services
        performance_service = container.resolve(IPerformanceServiceV2)
        error_handler = container.resolve(IExceptionHandlerServiceV2)
        sse_service = container.resolve(ISSEServiceV2)
        config_service = container.resolve(IConfigServiceV2)

        # Create or use provided repository service
        if repository_service is None:
            # Create repository service with database session dependency
            # Use create_session to get an actual session instance
            from vpsweb.repository.database import create_session

            repository_service = RepositoryWebService(create_session())

        # Register and resolve business services
        container.register_instance(
            ITemplateServiceV2, TemplateServiceV2(logger=app_logger)
        )
        container.register_instance(
            IPoemServiceV2,
            PoemServiceV2(
                repository_service=repository_service,
                performance_service=performance_service,
                logger=app_logger,
            ),
        )
        container.register_instance(
            ITranslationServiceV2,
            TranslationServiceV2(
                repository_service=repository_service,
                performance_service=performance_service,
                logger=app_logger,
            ),
        )
        container.register_instance(
            IStatisticsServiceV2,
            StatisticsServiceV2(
                repository_service=repository_service,
                performance_service=performance_service,
                logger=app_logger,
            ),
        )

        storage_handler = StorageHandler()
        container.register_instance(
            IWorkflowServiceV2,
            WorkflowServiceV2(
                repository_service=repository_service,
                storage_handler=storage_handler,
                task_service=task_service,
                logger=app_logger,
            ),
        )

        # Resolve all services
        poem_service = container.resolve(IPoemServiceV2)
        translation_service = container.resolve(ITranslationServiceV2)
        workflow_service = container.resolve(IWorkflowServiceV2)
        statistics_service = container.resolve(IStatisticsServiceV2)
        template_service = container.resolve(ITemplateServiceV2)

        # Create application router
        router = ApplicationRouterV2(
            app=app,
            container=container,
            poem_service=poem_service,
            translation_service=translation_service,
            workflow_service=workflow_service,
            statistics_service=statistics_service,
            template_service=template_service,
            error_handler=error_handler,
            performance_service=performance_service,
            sse_service=sse_service,
            config_service=config_service,
            logger=app_logger,
        )

        return router.get_app()


# Convenience function for creating the application
def create_app() -> FastAPI:
    """
    Convenience function to create the VPSWeb application.

    This is the main entry point that replaces the original app.py pattern.
    """
    return ApplicationFactoryV2.create_application()


# For backward compatibility - the original app variable
app = create_app()
