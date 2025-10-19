"""
VPSWeb Repository Web UI - FastAPI Application v0.3.1

Main FastAPI application entrypoint for the poetry translation repository.
Provides web interface and API endpoints for managing poems and translations.
"""

from fastapi import FastAPI, Request, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import time
import logging

from src.vpsweb.repository.database import init_db, get_db
from src.vpsweb.repository.models import Poem
from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.service import RepositoryWebService
from .api import poems, translations, statistics
from .config import settings
from .services.poem_service import PoemService
from .services.translation_service import TranslationService
from .services.vpsweb_adapter import VPSWebWorkflowAdapter, get_vpsweb_adapter


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
    """Handle HTTP exceptions with consistent error response format"""
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


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with consistent error response format"""
    logger.error(
        f"Unexpected error in {request.method} {request.url.path}: {exc}", exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error. Please try again later.",
            "data": None,
            "error_code": 500,
            "timestamp": time.time(),
            "error_id": f"ERR_{int(time.time() * 1000)}",  # Unique error ID for tracking
        },
    )


# Mount static files directory
app.mount(
    "/static", StaticFiles(directory="src/vpsweb/webui/web/static"), name="static"
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory="src/vpsweb/webui/web/templates")

# Include API routers
app.include_router(poems.router, prefix="/api/v1/poems", tags=["poems"])
app.include_router(
    translations.router, prefix="/api/v1/translations", tags=["translations"]
)
app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["statistics"])


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


def get_translation_service(db: Session = Depends(get_db)) -> TranslationService:
    """Dependency to get translation service instance"""
    return TranslationService(db)


async def get_vpsweb_adapter_dependency(
    poem_service: PoemService = Depends(get_poem_service),
    translation_service: TranslationService = Depends(get_translation_service),
    db: Session = Depends(get_db),
) -> VPSWebWorkflowAdapter:
    """Dependency to get VPSWeb workflow adapter instance"""
    repository_service = RepositoryWebService(db)
    async with get_vpsweb_adapter(
        poem_service, translation_service, repository_service
    ) as adapter:
        yield adapter


@app.get("/poems", response_class=HTMLResponse)
async def poems_list(request: Request, db: Session = Depends(get_db)):
    """
    List all poems with filtering and pagination
    """
    service = get_repository_service(db)
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
async def poem_detail(poem_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Display detailed view of a specific poem with translations
    """
    service = get_repository_service(db)
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


@app.get("/api/v1/workflow/tasks/{task_id}")
async def get_workflow_task_status(
    task_id: str,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Get the status of a background translation workflow task

    This endpoint allows monitoring of long-running translation workflows
    that were started with the background processing option.
    """
    try:
        result = await adapter.get_task_status(task_id)

        if result is None:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"Task not found: {task_id}",
                    "data": None,
                },
                status_code=404,
            )

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


@app.get("/api/v1/workflow/tasks")
async def list_workflow_tasks(
    limit: int = 50,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    List active and recent background translation workflow tasks

    This endpoint provides a list of recent translation tasks for monitoring
    and management purposes.
    """
    try:
        result = await adapter.list_active_tasks(limit=limit)

        return JSONResponse(
            {"success": True, "message": "Tasks retrieved successfully", "data": result}
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
async def cancel_workflow_task(
    task_id: str,
    adapter: VPSWebWorkflowAdapter = Depends(get_vpsweb_adapter_dependency),
):
    """
    Cancel a background translation workflow task

    This endpoint allows cancellation of pending or running translation tasks.
    Completed tasks cannot be cancelled.
    """
    try:
        cancelled = await adapter.cancel_task(task_id)

        if not cancelled:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"Task not found or cannot be cancelled: {task_id}",
                    "data": None,
                },
                status_code=404,
            )

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
