"""
VPSWeb Repository Web UI - FastAPI Application v0.3.2

Main FastAPI application entrypoint for the poetry translation repository.
Provides web interface and API endpoints for managing poems and translations.
"""

from fastapi import FastAPI, Request, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
    StreamingResponse,
)
from sse_starlette import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import time
import logging
import asyncio
import json
import threading
import httpx

from src.vpsweb.repository.database import init_db, get_db
from src.vpsweb.repository.models import Poem
from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.service import RepositoryWebService
from .api import poems, translations, statistics, poets
from .config import settings
from .services.poem_service import PoemService

# TranslationService removed - dead code (not used in current codebase)
from .services.vpsweb_adapter import (
    VPSWebWorkflowAdapter,
    get_vpsweb_adapter,
    WorkflowTimeoutError,
)
from .task_models import TaskStatus


# Pydantic models for workflow endpoints
class TranslationRequest(BaseModel):
    poem_id: str
    source_lang: str
    target_lang: str
    workflow_mode: str = "hybrid"


class TranslationValidationRequest(BaseModel):
    poem_id: str
    source_lang: str
    target_lang: str
    workflow_mode: str = "hybrid"


# Create FastAPI application instance
app = FastAPI(
    title="VPSWeb Repository v0.3.1",
    description="Local poetry translation repository with AI integration",
    version="0.3.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize app.state for in-memory task tracking
app.state.tasks = {}  # task_id -> TaskStatus
app.state.task_locks = {}  # task_id -> threading.Lock

# Performance monitoring middleware
logger = logging.getLogger(__name__)


@app.middleware("http")
async def performance_monitoring_middleware(request: Request, call_next):
    """Monitor API performance and log slow requests"""
    start_time = time.time()

    # Process the request
    response = await call_next(request)

    # Calculate processing time
    process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

    # Add performance headers
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    # Log performance for monitoring
    log_level = logging.INFO
    if process_time > 1000:  # > 1 second
        log_level = logging.WARNING
    elif process_time > 500:  # > 500ms
        log_level = logging.INFO

    logger.log(
        log_level,
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms",
    )

    return response


# Global exception handler for improved error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with appropriate response format"""

    # Check if this is a web request (browser request) - prefers HTML
    accept_header = request.headers.get("accept", "")
    is_web_request = "text/html" in accept_header or request.url.path.startswith("/")

    if is_web_request and exc.status_code in [404, 403, 401, 422]:
        # Return HTML error page for common HTTP errors in web interface
        template_context = {
            "request": request,
            "error_details": f"{request.method} {request.url.path}",
            "error_id": f"HTTP{exc.status_code}-{int(time.time()) % 10000:04d}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if exc.status_code == 404:
            return templates.TemplateResponse(
                "404.html", template_context, status_code=404
            )
        elif exc.status_code == 403:
            template_context["error_details"] = (
                "You don't have permission to access this resource."
            )
            return templates.TemplateResponse(
                "403.html", template_context, status_code=403
            )
        elif exc.status_code == 401:
            template_context["error_details"] = (
                "Authentication required to access this resource."
            )
            return templates.TemplateResponse(
                "403.html", template_context, status_code=401
            )
        elif exc.status_code == 422:
            template_context["error_details"] = f"Validation error: {exc.detail}"
            return templates.TemplateResponse(
                "422.html", template_context, status_code=422
            )

    # Return JSON response for API requests
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "error_code": exc.status_code,
            "timestamp": time.time(),
        },
    )


@app.exception_handler(WorkflowTimeoutError)
async def workflow_timeout_handler(request: Request, exc: WorkflowTimeoutError):
    """Handle workflow timeout errors with user-friendly response"""

    # Check if this is a web request (browser request) - prefers HTML
    accept_header = request.headers.get("accept", "")
    is_web_request = "text/html" in accept_header or request.url.path.startswith("/")

    if is_web_request:
        # Return HTML error page for web interface using existing 404 template
        template_context = {
            "request": request,
            "error_details": "The translation workflow is taking longer than expected. This could be due to high demand or system load. Please try again in a few minutes, or consider using a simpler workflow mode.",
            "error_id": f"TIMEOUT-{int(time.time()) % 10000:04d}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return templates.TemplateResponse("404.html", template_context, status_code=408)

    # Return JSON response for API requests
    return JSONResponse(
        status_code=408,
        content={
            "success": False,
            "message": f"Translation workflow timed out. {str(exc)}",
            "data": None,
            "error_code": "WORKFLOW_TIMEOUT",
            "error_type": "timeout",
            "timestamp": time.time(),
            "retry_suggested": True,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with appropriate response format"""

    # Generate unique error ID for tracking
    error_id = f"ERR-{int(time.time() * 1000)}"

    # Log the error with details
    logger.error(
        f"Unexpected error {error_id} in {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )

    # Check if this is a web request (browser request) - prefers HTML
    accept_header = request.headers.get("accept", "")
    is_web_request = "text/html" in accept_header or request.url.path.startswith("/")

    if is_web_request:
        # Return HTML error page for web interface
        template_context = {
            "request": request,
            "error_details": (
                str(exc) if settings.debug else "An unexpected error occurred."
            ),
            "error_id": error_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "show_debug": settings.debug,  # Only show debug info in development
        }

        return templates.TemplateResponse("500.html", template_context, status_code=500)

    # Return JSON response for API requests
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error. Please try again later.",
            "data": None,
            "error_code": 500,
            "timestamp": time.time(),
            "error_id": error_id,
        },
    )


# Mount static files directory
app.mount(
    "/static", StaticFiles(directory="src/vpsweb/webui/web/static"), name="static"
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="src/vpsweb/webui/web/templates")


# Add custom Jinja2 filters
def strip_leading_spaces(text):
    """Remove leading whitespace only from the beginning of text (first line)"""
    if not text:
        return text
    # Remove only leading whitespace from the very beginning, preserving internal formatting
    return text.lstrip()


templates.env.filters["strip_leading_spaces"] = strip_leading_spaces

# Include API routers
app.include_router(poems.router, prefix="/api/v1/poems", tags=["poems"])
app.include_router(
    translations.router, prefix="/api/v1/translations", tags=["translations"]
)
app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["statistics"])
app.include_router(poets.router, prefix="/api/v1/poets", tags=["poets"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """
    Dashboard - List all poems in the repository
    """
    poems_list = db.query(Poem).order_by(Poem.created_at.desc()).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "poems": poems_list,
            "title": "VPSWeb Repository - Dashboard",
        },
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {"status": "healthy", "version": "0.3.1"}


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


def get_poem_service(db: Session = Depends(get_db)) -> PoemService:
    """Dependency to get poem service instance"""
    return PoemService(db)


def get_vpsweb_adapter_dependency(
    poem_service: PoemService = Depends(get_poem_service),
    db: Session = Depends(get_db),
) -> VPSWebWorkflowAdapter:
    """Dependency to get VPSWeb workflow adapter instance"""
    repository_service = RepositoryWebService(db)
    # TranslationService removed - dead code (not used in current codebase)
    # Create adapter instance - FastAPI dependencies should be regular functions, not async context managers
    return VPSWebWorkflowAdapter(
        poem_service=poem_service,
        repository_service=repository_service,
        config_path=None,  # Use default config path
    )
    # TranslationService removed - dead code (not used in current codebase)


@app.get("/poems", response_class=HTMLResponse)
async def poems_list(
    request: Request, service: RepositoryService = Depends(get_repository_service)
):
    """
    List all poems with filtering and pagination
    """
    poems_list = service.poems.get_multi(skip=0, limit=100)
    return templates.TemplateResponse(
        "poems_list.html",
        {"request": request, "poems": poems_list, "title": "Poems - VPSWeb Repository"},
    )


@app.get("/poems/new", response_class=HTMLResponse)
async def new_poem_form(request: Request):
    """
    Display form to create a new poem
    """
    return templates.TemplateResponse(
        "poem_new.html",
        {"request": request, "title": "Add New Poem - VPSWeb Repository"},
    )


@app.get("/poems/{poem_id}", response_class=HTMLResponse)
async def poem_detail(
    poem_id: str,
    request: Request,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Display detailed view of a specific poem with translations
    """
    poem = service.poems.get_by_id(poem_id)

    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    return templates.TemplateResponse(
        "poem_detail.html",
        {
            "request": request,
            "poem": poem,
            "title": f"{poem.poem_title} - VPSWeb Repository",
        },
    )


@app.get("/poems/{poem_id}/compare", response_class=HTMLResponse)
async def poem_compare(poem_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Display comparison view for translations of a specific poem
    """
    service = get_repository_service(db)
    poem = service.poems.get_by_id(poem_id)

    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    return templates.TemplateResponse(
        "poem_compare.html",
        {
            "request": request,
            "poem": poem,
            "title": f"Compare Translations - {poem.poem_title} - VPSWeb Repository",
        },
    )


@app.get("/translations/{translation_id}/notes", response_class=HTMLResponse)
async def translation_notes(
    translation_id: str, request: Request, db: Session = Depends(get_db)
):
    """
    Display translation notes with detailed T-E-T workflow steps
    """
    service = get_repository_service(db)

    # Get translation and poem information
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    poem = service.poems.get_by_id(translation.poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Get workflow data for AI translations
    workflow_data = None
    workflow_steps = None
    if translation.translator_type.lower() == "ai" and translation.has_workflow_steps:
        try:
            # Make internal requests to workflow endpoints
            async with httpx.AsyncClient() as client:
                # Get workflow summary
                summary_response = await client.get(
                    f"http://localhost:8000/api/v1/translations/{translation_id}/workflow-summary",
                    timeout=10.0,
                )
                if summary_response.status_code == 200:
                    workflow_data = summary_response.json()

                # Get workflow steps
                steps_response = await client.get(
                    f"http://localhost:8000/api/v1/translations/{translation_id}/workflow-steps",
                    timeout=10.0,
                )
                if steps_response.status_code == 200:
                    workflow_steps = steps_response.json()
                    # Parse model_info JSON strings for each step
                    import json

                    for step in workflow_steps:
                        if step.get("model_info") and isinstance(
                            step["model_info"], str
                        ):
                            try:
                                step["parsed_model_info"] = json.loads(
                                    step["model_info"]
                                )
                            except json.JSONDecodeError:
                                step["parsed_model_info"] = {}
        except Exception as e:
            # Log error but don't fail the page load
            logging.warning(
                f"Failed to load workflow data for translation {translation_id}: {e}"
            )
            workflow_data = None
            workflow_steps = None

    return templates.TemplateResponse(
        "translation_notes.html",
        {
            "request": request,
            "poem": poem,
            "translation": translation,
            "workflow_data": workflow_data,
            "workflow_steps": workflow_steps,
            "title": f"Translation Notes - {poem.poem_title} - VPSWeb Repository",
        },
    )


@app.get("/translations", response_class=HTMLResponse)
async def translations_list(request: Request, db: Session = Depends(get_db)):
    """
    List all translations with filtering options
    """
    service = get_repository_service(db)
    translations_list = service.translations.get_multi(skip=0, limit=100)
    return templates.TemplateResponse(
        "translations_list.html",
        {
            "request": request,
            "translations": translations_list,
            "title": "Translations - VPSWeb Repository",
        },
    )


@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, db: Session = Depends(get_db)):
    """
    Display repository statistics and analytics
    """
    service = get_repository_service(db)
    stats = service.get_repository_stats()
    return templates.TemplateResponse(
        "statistics.html",
        {"request": request, "stats": stats, "title": "Statistics - VPSWeb Repository"},
    )


# Poet Browsing Routes
@app.get("/poets", response_class=HTMLResponse)
async def poets_list(
    request: Request,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    min_poems: Optional[int] = None,
    min_translations: Optional[int] = None,
):
    """
    Display list of all poets with statistics and activity metrics
    """
    try:
        service = RepositoryWebService(db)

        # Get poets data with filters
        poets_data = service.get_all_poets(
            skip=0,
            limit=50,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            min_poems=min_poems,
            min_translations=min_translations,
        )

        return templates.TemplateResponse(
            "poets_list.html",
            {
                "request": request,
                "poets": poets_data["poets"],
                "total_count": poets_data["total_count"],
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "min_poems": min_poems,
                "min_translations": min_translations,
                "title": "Poets - VPSWeb Repository",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/poets/{poet_name}", response_class=HTMLResponse)
async def poet_detail(
    poet_name: str,
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    language: Optional[str] = None,
    has_translations: Optional[bool] = None,
    sort_by: Optional[str] = "title",
    sort_order: Optional[str] = "asc",
):
    """
    Display detailed view of a specific poet with their poems and statistics
    """
    try:
        service = RepositoryWebService(db)

        # Get poet statistics
        stats = service.get_poet_statistics(poet_name)

        # Get poet's poems with filters
        poems_data = service.get_poems_by_poet(
            poet_name=poet_name,
            skip=skip,
            limit=limit,
            language=language,
            has_translations=has_translations,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Get poet's recent translations
        translations_data = service.get_translations_by_poet(
            poet_name=poet_name,
            skip=0,
            limit=5,
            sort_by="created_at",
            sort_order="desc",
        )

        return templates.TemplateResponse(
            "poet_detail.html",
            {
                "request": request,
                "poet_name": poet_name,
                "poem_stats": stats["poem_statistics"],
                "translation_stats": stats["translation_statistics"],
                "poems": poems_data["poems"],
                "total_poems": poems_data["total_count"],
                "recent_translations": translations_data["translations"],
                "language": language,
                "has_translations": has_translations,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "title": f"{poet_name} - VPSWeb Repository",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api-docs", response_class=HTMLResponse)
async def api_documentation(request: Request):
    """
    Display API documentation page
    """
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request, "title": "API Documentation - VPSWeb Repository"},
    )


# Workflow Integration API Endpoints


@app.post("/api/v1/workflow/translate")
async def start_translation_workflow(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Start a new translation workflow using VPSWeb engine

    This endpoint integrates the existing VPSWeb translation workflow with the web interface,
    allowing users to execute high-quality poetry translations with background processing.
    """
    try:
        result = await adapter.execute_translation_workflow(
            poem_id=request.poem_id,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            workflow_mode=request.workflow_mode,
            background_tasks=background_tasks,
            synchronous=False,
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Translation workflow started successfully",
                "data": result,
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Failed to start translation workflow: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.post("/api/v1/workflow/translate/sync")
async def execute_translation_workflow_sync(
    request: TranslationRequest,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Execute a translation workflow synchronously and return the result

    This endpoint executes the VPSWeb translation workflow synchronously and returns
    the complete translation result. May take significant time for complex poems.
    """
    try:
        result = await adapter.execute_translation_workflow(
            poem_id=request.poem_id,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            workflow_mode=request.workflow_mode,
            background_tasks=None,
            synchronous=True,
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Translation workflow completed successfully",
                "data": result,
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Translation workflow failed: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.post("/api/v1/workflow/validate")
async def validate_translation_workflow(
    request: TranslationValidationRequest,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Validate translation workflow input without executing

    This endpoint validates the translation request parameters and checks if the
    VPSWeb configuration is properly set up for execution.
    """
    try:
        result = await adapter.validate_workflow_input(
            poem_id=request.poem_id,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            workflow_mode=request.workflow_mode,
        )

        return JSONResponse(
            {"success": True, "message": "Validation completed", "data": result}
        )

    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"Validation failed: {str(e)}", "data": None},
            status_code=500,
        )


@app.delete("/api/v1/poems/{poem_id}")
async def delete_poem(poem_id: str, db: Session = Depends(get_db)):
    """
    Delete a poem and all its related translations

    This endpoint allows deletion of poems and all associated data including translations.
    """
    try:
        service = get_repository_service(db)
        success = service.delete_poem(poem_id)

        if success:
            return JSONResponse(
                {"success": True, "message": "Poem deleted successfully"},
                status_code=200,
            )
        else:
            return JSONResponse(
                {"success": False, "message": "Poem not found"}, status_code=404
            )

    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"Failed to delete poem: {str(e)}"},
            status_code=500,
        )


@app.delete("/api/v1/translations/{translation_id}")
async def delete_translation(translation_id: str, db: Session = Depends(get_db)):
    """
    Delete a translation

    This endpoint allows deletion of individual translations while preserving the original poem.
    """
    try:
        service = get_repository_service(db)
        success = service.delete_translation(translation_id)

        if success:
            return JSONResponse(
                {"success": True, "message": "Translation deleted successfully"},
                status_code=200,
            )
        else:
            return JSONResponse(
                {"success": False, "message": "Translation not found"}, status_code=404
            )

    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"Failed to delete translation: {str(e)}"},
            status_code=500,
        )


@app.get("/api/v1/workflow/tasks/{task_id}")
async def get_workflow_task_status(task_id: str):
    """
    Get the status of a background translation workflow task

    This endpoint allows monitoring of long-running translation workflows
    using FastAPI app.state for real-time status tracking.
    """
    try:
        # Check if task exists in app.state
        if not hasattr(app.state, "tasks") or task_id not in app.state.tasks:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"Task not found: {task_id}",
                    "data": None,
                },
                status_code=404,
            )

        # Get task status from app.state
        task_status = app.state.tasks[task_id]
        result = task_status.to_dict()

        return JSONResponse(
            {
                "success": True,
                "message": "Task status retrieved successfully",
                "data": result,
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Failed to get task status: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.get("/api/v1/workflow/tasks/{task_id}/stream")
async def stream_workflow_task_status(
    task_id: str,
    request: Request,
):
    """
    Stream real-time workflow task progress using Server-Sent Events (SSE)

    This endpoint provides real-time updates for translation workflow progress
    through FastAPI app.state, eliminating the need for database polling.
    """

    async def event_generator():
        import json  # Local import to avoid scoping issues

        # Check if task exists in app.state
        if not hasattr(app.state, "tasks") or task_id not in app.state.tasks:
            yield {"event": "error", "data": json.dumps({"message": "Task not found"})}
            return

        # Send initial status
        task_status = app.state.tasks[task_id]
        initial_status = task_status.to_dict()
        yield {"event": "status", "data": json.dumps(initial_status)}
        print(
            f"📡 [SSE] Initial status sent for task {task_id}: {initial_status['status']} - {initial_status['current_step']}"
        )

        # Stream for updates with real-time app.state access
        max_iterations = 3000  # 10 minutes with 0.2-second intervals (600 / 0.2 = 3000)
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
                        or current_dict["current_step"] != last_status["current_step"]
                    )

                    # Specific step change detection - check for step status transitions
                    has_step_change = False
                    if last_status is not None:
                        current_step_details = current_dict.get("step_details", {})
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
                        current_step_states = current_dict.get("step_states", {})
                        last_step_states = last_status.get("step_states", {})
                        if current_step_states != last_step_states:
                            has_step_change = True
                            print(f"🔍 [SSE] Step states changed detected")

                    # Additional check for task timestamp changes (more sensitive detection)
                    has_time_change = (
                        last_status is not None
                        and "updated_at" in current_dict
                        and "updated_at" in last_status
                        and current_dict["updated_at"] != last_status["updated_at"]
                    )

                    # Send update if any significant field changed OR timestamp changed OR step changed
                    if has_progress_change or has_step_change or has_time_change:
                        last_status = current_dict.copy()
                        last_update_time = current_time

                        # Determine event type based on what changed
                        event_type = "status"
                        if has_step_change and last_status is not None:
                            event_type = "step_change"

                        yield {"event": event_type, "data": json.dumps(current_dict)}
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

                    # Force periodic updates every 5 seconds to ensure connection stays alive
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
                        "data": json.dumps({"message": "Task disappeared from memory"}),
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
                        "data": json.dumps({"message": f"SSE stream error: {str(e)}"}),
                    }
                    break

                # Continue after a brief delay for non-critical errors
                await asyncio.sleep(1.0)

        # Send completion event if timed out
        if i >= max_iterations - 1:
            yield {
                "event": "timeout",
                "data": json.dumps({"message": "Workflow timed out after 10 minutes"}),
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


@app.get("/api/v1/workflow/tasks")
async def list_workflow_tasks(limit: int = 50):
    """
    List active and recent background translation workflow tasks

    This endpoint provides a list of recent translation tasks from app.state
    for monitoring and management purposes.
    """
    try:
        # Get tasks from app.state
        if not hasattr(app.state, "tasks"):
            return JSONResponse(
                {
                    "success": True,
                    "message": "Tasks retrieved successfully",
                    "data": {"tasks": []},
                }
            )

        # Convert tasks to dict format and sort by creation time (newest first)
        tasks = []
        for task_id, task_status in app.state.tasks.items():
            tasks.append({"task_id": task_id, **task_status.to_dict()})

        # Sort by created_at (newest first) and limit
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        limited_tasks = tasks[:limit]

        return JSONResponse(
            {
                "success": True,
                "message": "Tasks retrieved successfully",
                "data": {"tasks": limited_tasks, "total_count": len(tasks)},
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Failed to list tasks: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.delete("/api/v1/workflow/tasks/{task_id}")
async def cancel_workflow_task(task_id: str):
    """
    Cancel a background translation workflow task

    This endpoint allows cancellation of pending or running translation tasks
    using FastAPI app.state for task management.
    """
    try:
        # Check if task exists in app.state
        if not hasattr(app.state, "tasks") or task_id not in app.state.tasks:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"Task not found: {task_id}",
                    "data": None,
                },
                status_code=404,
            )

        # Check if task can be cancelled (not completed)
        task_status = app.state.tasks[task_id]
        if task_status.status.value in ["completed", "failed"]:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"Task cannot be cancelled (already {task_status.status.value}): {task_id}",
                    "data": None,
                },
                status_code=404,
            )

        # Mark task as cancelled
        print(f"[WORKFLOW] 🚫 CANCELLATION REQUESTED for task {task_id}")
        with app.state.task_locks[task_id]:
            task_status.set_failed(
                error="Task cancelled by user",
                message="Task was cancelled by user request",
            )
        print(f"[WORKFLOW] ✅ Task {task_id} marked as CANCELLED in app.state")

        return JSONResponse(
            {
                "success": True,
                "message": "Task cancelled successfully",
                "data": {"task_id": task_id},
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Failed to cancel task: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.post("/api/v1/workflow/tasks/{task_id}/cancel")
async def cancel_workflow_task_post(task_id: str):
    """
    Cancel a background translation workflow task (POST endpoint for frontend compatibility)

    This endpoint provides the same functionality as the DELETE endpoint but uses POST
    method with /cancel suffix for frontend compatibility.
    """
    # Reuse the DELETE endpoint logic
    return await cancel_workflow_task(task_id)


@app.get("/api/v1/workflow/modes")
async def get_workflow_modes(
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Get available VPSWeb workflow modes

    This endpoint returns information about available translation workflow modes
    and their characteristics.
    """
    try:
        result = await adapter.get_workflow_modes()

        return JSONResponse(
            {
                "success": True,
                "message": "Workflow modes retrieved successfully",
                "data": result,
            }
        )

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "message": f"Failed to get workflow modes: {str(e)}",
                "data": None,
            },
            status_code=500,
        )


@app.on_event("startup")
async def startup_event():
    """
    Initialize database on application startup
    """
    # P0.3: Add startup guard for public binding
    import os

    # Check if host is set to bind to all interfaces (0.0.0.0)
    if settings.host == "0.0.0.0":
        # Only allow public binding if explicitly authorized
        allow_public = os.getenv("VPSWEB_ALLOW_PUBLIC", "").lower() in (
            "true",
            "1",
            "yes",
        )

        if not allow_public:
            print("❌ SECURITY WARNING: Refusing to bind to 0.0.0.0 (public interface)")
            print("   VPSWeb is designed for local use only by default.")
            print("   To enable public binding, set VPSWEB_ALLOW_PUBLIC=true")
            print("   Use uvicorn --host 127.0.0.1 for local access only")
            import sys

            sys.exit(1)
        else:
            print("⚠️  WARNING: Binding to public interface (0.0.0.0)")
            print("   Ensure you understand the security implications.")
            print("   This application is designed for local use.")

    print("✅ Security check passed - local-only mode by default")

    init_db()


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting VPSWeb Repository v0.3.1...")
    print(f"📍 Local URL: http://{settings.host}:{settings.port}")
    print(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
