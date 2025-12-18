"""
VPSWeb Web UI - WeChat Article Generation API Endpoints

API endpoints for generating WeChat articles from translation workflow data.
Integrates the CLI WeChat article generation workflow with the WebUI.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from vpsweb.repository.crud import RepositoryService
from vpsweb.repository.database import get_db
from vpsweb.repository.models import Translation
from vpsweb.services.config import ConfigFacade, get_config_facade

from ..services.vpsweb_adapter import VPSWebWorkflowAdapterV2
from ..utils.wechat_article_runner import WeChatArticleRunner

router = APIRouter()


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


def get_config_facade_dependency() -> ConfigFacade:
    """Dependency to get ConfigFacade instance"""
    return get_config_facade()


class WeChatArticleGenerateRequest(BaseModel):
    """Request model for WeChat article generation"""

    author: Optional[str] = None
    digest: Optional[str] = None
    dry_run: bool = False


class WeChatArticleResponse(BaseModel):
    """Response model for WeChat article generation"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


def get_vpsweb_adapter(
    db: Session = Depends(get_db),
) -> VPSWebWorkflowAdapterV2:
    """Dependency to get VPSWeb workflow adapter instance"""
    from vpsweb.core.container import DIContainer
    from vpsweb.core.workflow_orchestrator import WorkflowOrchestratorV2
    from vpsweb.repository.service import RepositoryWebService

    from ..services.poem_service import PoemService
    from ..services.vpsweb_adapter import VPSWebWorkflowAdapterV2

    poem_service = PoemService(db)
    repository_service = RepositoryWebService(db)

    # Create workflow orchestrator for the adapter
    container = DIContainer()
    workflow_orchestrator = WorkflowOrchestratorV2(container=container)

    return VPSWebWorkflowAdapterV2(
        poem_service=poem_service,
        repository_service=repository_service,
        workflow_orchestrator=workflow_orchestrator,
        config_service=None,  # Use default config service
    )


@router.post(
    "/{translation_id}/generate-wechat-article",
    response_model=WeChatArticleResponse,
)
async def generate_wechat_article(
    translation_id: str,
    request_body: WeChatArticleGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    service: RepositoryService = Depends(get_repository_service),
    adapter: VPSWebWorkflowAdapterV2 = Depends(get_vpsweb_adapter),
    config_facade: ConfigFacade = Depends(get_config_facade_dependency),
):
    """
    Generate a WeChat article from translation workflow data.

    This endpoint creates a WeChat-compatible HTML article from AI translation
    workflow data, following the same process as the CLI workflow.

    **Path Parameters:**
    - **translation_id**: ULID of the translation to generate article from

    **Request Body:**
    - **author**: Article author name (optional)
    - **digest**: Custom digest for article (optional)
    - **dry_run**: Generate article without external API calls (default: False)

    **Returns:**
    - Generated article information including file paths and metadata
    """

    print(
        f"🚀 Starting WeChat article generation for translation: {translation_id}"
    )

    # Check if translation exists
    print(f"🔍 Looking up translation {translation_id}...")
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        error_msg = f"Translation with ID '{translation_id}' not found"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)

    print(
        f"✅ Found translation: {translation.id} (type: {translation.translator_type})"
    )

    # Verify it's an AI translation with workflow steps
    if translation.translator_type != "ai":
        error_msg = (
            "WeChat article generation is only available for AI translations"
        )
        print(f"❌ {error_msg} (found: {translation.translator_type})")
        raise HTTPException(status_code=400, detail=error_msg)

    # Check if translation has workflow steps (translation notes)
    print(f"🔍 Checking workflow steps for translation {translation_id}...")
    try:
        workflow_steps = service.workflow_steps.get_by_translation(
            translation_id
        )
        print(f"✅ Found {len(workflow_steps)} workflow steps")
    except Exception as e:
        error_msg = f"Failed to retrieve workflow steps: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

    if not workflow_steps:
        error_msg = "Translation does not have workflow data (translation notes) required for article generation"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    # Get poem information
    print(f"🔍 Looking up poem {translation.poem_id}...")
    poem = service.poems.get_by_id(translation.poem_id)
    if not poem:
        error_msg = (
            f"Associated poem with ID '{translation.poem_id}' not found"
        )
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)

    print(f"✅ Found poem: {poem.poem_title} by {poem.poet_name}")

    try:
        print(f"🔧 Building translation data structure...")
        # Build translation data structure compatible with CLI article generator
        translation_data = await _build_translation_data(
            translation, poem, workflow_steps, service
        )
        print(f"✅ Translation data built successfully")

        print(f"🏃 Initializing WeChat article runner...")
        # Initialize WeChat article runner with ConfigFacade
        runner = WeChatArticleRunner(config_facade=config_facade)
        print(f"✅ WeChat article runner initialized with ConfigFacade")

        print(
            f"📝 Starting article generation (dry_run={request_body.dry_run})..."
        )

        # Generate task ID and start background generation
        import uuid

        task_id = str(uuid.uuid4())

        # Store task in app state for status tracking
        if not hasattr(request.app.state, "wechat_tasks"):
            request.app.state.wechat_tasks = {}

        request.app.state.wechat_tasks[task_id] = {
            "status": "running",
            "translation_id": translation_id,
            "started_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
        }

        # Start background generation
        from concurrent.futures import ThreadPoolExecutor

        # Store app reference for background function
        app_state = request.app.state

        def generate_article_background():
            try:
                print(
                    f"🔧 Background task {task_id}: Starting article generation..."
                )
                result = runner.generate_from_translation_data(
                    translation_data=translation_data,
                    author=request_body.author,
                    digest=request_body.digest,
                    dry_run=request_body.dry_run,
                    custom_metadata={
                        "translation_id": translation_id,
                        "poem_id": translation.poem_id,
                        "generated_from": "webui",
                    },
                )
                print(
                    f"✅ Background task {task_id}: Article generation completed"
                )

                # Get article summary
                article_summary = runner.get_article_summary(result)
                print(
                    f"✅ Background task {task_id}: Article summary retrieved"
                )

                # Update task status
                app_state.wechat_tasks[task_id]["status"] = "completed"
                app_state.wechat_tasks[task_id]["result"] = article_summary
                app_state.wechat_tasks[task_id][
                    "completed_at"
                ] = datetime.now().isoformat()

            except Exception as e:
                print(f"❌ Background task {task_id} failed: {e}")
                app_state.wechat_tasks[task_id]["status"] = "failed"
                app_state.wechat_tasks[task_id]["error"] = str(e)
                app_state.wechat_tasks[task_id][
                    "failed_at"
                ] = datetime.now().isoformat()

        # Start background task
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(generate_article_background)

        print(
            f"🚀 Background task {task_id} started for translation {translation_id}"
        )

        return WeChatArticleResponse(
            success=True,
            message="WeChat article generation started in background",
            data={"task_id": task_id},
        )

    except ImportError as e:
        # Handle import errors specifically
        error_msg = f"Import error in WeChat article generation: {str(e)}"
        print(f"❌ WeChat API Import Error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import required modules for WeChat article generation: {str(e)}",
        )

    except FileNotFoundError as e:
        # Handle file not found errors
        error_msg = (
            f"File not found during WeChat article generation: {str(e)}"
        )
        print(f"❌ WeChat API File Error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Required file not found during article generation: {str(e)}",
        )

    except Exception as e:
        # Handle general errors with detailed logging
        import traceback

        error_msg = f"Failed to generate WeChat article: {str(e)}"
        print(f"❌ WeChat API Error: {error_msg}")
        print(f"🔍 Full traceback: {traceback.format_exc()}")

        # Provide more specific error information
        if "No such file or directory" in str(e):
            detail = f"File system error during article generation: {str(e)}"
        elif "Permission denied" in str(e):
            detail = f"Permission error during article generation: {str(e)}"
        elif "ModuleNotFoundError" in str(e) or "ImportError" in str(e):
            detail = (
                f"Missing required module for article generation: {str(e)}"
            )
        else:
            detail = f"WeChat article generation failed: {str(e)}"

        raise HTTPException(status_code=500, detail=detail)


@router.get(
    "/{translation_id}/wechat-article-status",
    response_model=WeChatArticleResponse,
)
async def check_wechat_article_status(
    translation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Check the status of WeChat article generation for a translation.

    This endpoint checks for background tasks and their completion status.

    **Path Parameters:**
    - **translation_id**: ULID of the translation to check

    **Returns:**
    - Current status of article generation and results if completed
    """

    # Check for existing tasks for this translation
    if not hasattr(request.app.state, "wechat_tasks"):
        return WeChatArticleResponse(
            success=True,
            message="No WeChat article generation tasks found",
            data={
                "status": "not_found",
                "tasks": [],
                "result": None,
                "error": None,
            },
        )

    # Find tasks for this translation
    tasks_for_translation = []
    for task_id, task_info in request.app.state.wechat_tasks.items():
        if task_info.get("translation_id") == translation_id:
            tasks_for_translation.append(
                {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "started_at": task_info.get("started_at"),
                    "completed_at": task_info.get("completed_at"),
                    "failed_at": task_info.get("failed_at"),
                    "error": task_info.get("error"),
                    "result": task_info.get("result"),
                }
            )

    if not tasks_for_translation:
        return WeChatArticleResponse(
            success=True,
            message="No WeChat article generation tasks found for this translation",
            data={
                "status": "not_found",
                "tasks": [],
                "result": None,
                "error": None,
            },
        )

    # Return the most recent task (latest started_at)
    latest_task = max(tasks_for_translation, key=lambda t: t["started_at"])

    return WeChatArticleResponse(
        success=True,
        message=f"WeChat article generation status: {latest_task['status']}",
        data=latest_task,
    )


async def _build_translation_data(
    translation: Translation,
    poem,
    workflow_steps: list,
    service: RepositoryService,
) -> Dict[str, Any]:
    """
    Build translation data structure compatible with CLI article generator.

    Converts WebUI database models to the JSON structure expected by
    the CLI ArticleGenerator class.
    """

    # Validate inputs
    if not translation:
        raise ValueError("Translation data is required")
    if not poem:
        raise ValueError("Poem data is required")
    if not workflow_steps:
        raise ValueError("Workflow steps data is required")

    print(f"🔧 Building translation data for translation {translation.id}")
    print(f"📝 Found {len(workflow_steps)} workflow steps")

    # Get AI log information
    try:
        ai_logs = service.ai_logs.get_by_translation(translation.id)
        ai_log = ai_logs[0] if ai_logs else None
        print(f"🤖 Found AI log: {ai_log is not None}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to get AI logs: {e}")
        ai_log = None

    # Build workflow steps data
    steps_data = {}
    congregated_output = {}

    for step in workflow_steps:
        step_type = step.step_type

        # Build step data
        step_data = {
            "content": step.content,
            "notes": step.notes or "",
            "model_info": step.model_info or {},
            "tokens_used": step.tokens_used or 0,
            "prompt_tokens": step.prompt_tokens or 0,
            "completion_tokens": step.completion_tokens or 0,
            "duration_seconds": step.duration_seconds or 0.0,
            "cost": step.cost or 0.0,
        }

        # Store in appropriate congregated output field
        if step_type == "initial_translation":
            # Format translation for CLI compatibility (prefixes handled by template)
            formatted_translation = f"{translation.translated_poem_title}\n{translation.translated_poet_name}\n\n{step.content}"
            congregated_output["initial_translation"] = formatted_translation
            congregated_output["initial_translation_notes"] = step.notes or ""
            steps_data["initial_translation"] = step_data

        elif step_type == "editor_review":
            congregated_output["editor_review"] = step.content
            congregated_output["editor_suggestions"] = step.notes or ""
            steps_data["editor_review"] = step_data

        elif step_type == "revised_translation":
            # Format translation for CLI compatibility (prefixes handled by template)
            formatted_translation = f"{translation.translated_poem_title}\n{translation.translated_poet_name}\n\n{step.content}"
            congregated_output["revised_translation"] = formatted_translation
            congregated_output["revised_translation_notes"] = step.notes or ""
            steps_data["revised_translation"] = step_data

    # Format original poem for CLI compatibility (prefixes handled by template)
    formatted_poem = (
        f"{poem.poem_title}\n{poem.poet_name}\n\n{poem.original_text}"
    )

    # Build complete translation data structure
    translation_data = {
        "workflow_id": workflow_steps[0].workflow_id if workflow_steps else "",
        "input": {
            "original_poem": formatted_poem,
            "source_lang": poem.source_language,
            "target_lang": translation.target_language,
        },
        "congregated_output": {
            "original_poem": formatted_poem,
            **congregated_output,
        },
        "steps": steps_data,
        "ai_log": (
            {
                "model_name": ai_log.model_name if ai_log else "",
                "workflow_mode": ai_log.workflow_mode if ai_log else "",
                "runtime_seconds": ai_log.runtime_seconds if ai_log else 0.0,
            }
            if ai_log
            else {}
        ),
        "metadata": {
            "translation_id": translation.id,
            "poem_id": poem.id,
            "poem_title": poem.poem_title,
            "poet_name": poem.poet_name,
            "translated_poem_title": translation.translated_poem_title,
            "translated_poet_name": translation.translated_poet_name,
            "created_at": translation.created_at.isoformat(),
        },
    }

    return translation_data


@router.get(
    "/{translation_id}/wechat-articles", response_model=WeChatArticleResponse
)
async def list_wechat_articles(
    translation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    List existing WeChat articles for a translation.

    This endpoint returns information about WeChat articles that have been
    generated from the specified translation using the background task system.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Returns:**
    - List of existing WeChat articles (if any) from completed tasks
    """

    # Check for completed tasks for this translation
    if not hasattr(request.app.state, "wechat_tasks"):
        return WeChatArticleResponse(
            success=True,
            message="No WeChat articles found",
            data={"articles": [], "output_dir": None, "status": "not_found"},
        )

    # Find completed tasks for this translation
    completed_tasks = []
    for task_id, task_info in request.app.state.wechat_tasks.items():
        if (
            task_info.get("translation_id") == translation_id
            and task_info.get("status") == "completed"
            and task_info.get("result")
        ):

            result = task_info["result"]
            completed_tasks.append(
                {
                    "task_id": task_id,
                    "status": task_info["status"],
                    "completed_at": task_info.get("completed_at"),
                    "result": result,
                }
            )

    if not completed_tasks:
        return WeChatArticleResponse(
            success=True,
            message="No completed WeChat articles found for this translation",
            data={"articles": [], "output_dir": None, "status": "not_found"},
        )

    # Return information from the most recent completed task
    latest_task = max(completed_tasks, key=lambda t: t["completed_at"])
    result = latest_task["result"]

    # Build articles list from the result
    articles = []
    if result.get("html_path"):
        articles.append({"type": "html", "file_path": result["html_path"]})

    if result.get("markdown_path"):
        articles.append(
            {"type": "markdown", "file_path": result["markdown_path"]}
        )

    if result.get("metadata_path"):
        articles.append(
            {"type": "metadata", "file_path": result["metadata_path"]}
        )

    return WeChatArticleResponse(
        success=True,
        message=f"Found {len(articles)} WeChat articles",
        data={
            "articles": articles,
            "output_dir": result.get("output_directory"),
            "status": "completed",
            "task_info": {
                "task_id": latest_task["task_id"],
                "completed_at": latest_task["completed_at"],
                "title": result.get("title"),
                "author": result.get("author"),
            },
        },
    )


@router.get("/{translation_id}/metadata", response_model=WeChatArticleResponse)
async def get_wechat_article_metadata(
    translation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get metadata for WeChat articles generated from a translation.

    This endpoint reads the metadata.json file from the generated articles
    and returns it for use in the WebUI.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Returns:**
    - Metadata from the most recent article generation
    """

    # Check for completed tasks for this translation
    if not hasattr(request.app.state, "wechat_tasks"):
        return WeChatArticleResponse(
            success=False,
            message="No WeChat article generation tasks found",
            data=None,
        )

    # Find completed tasks for this translation
    completed_tasks = []
    for task_id, task_info in request.app.state.wechat_tasks.items():
        if (
            task_info.get("translation_id") == translation_id
            and task_info.get("status") == "completed"
        ):
            completed_tasks.append(
                {
                    "task_id": task_id,
                    "completed_at": task_info.get("completed_at"),
                    "result": task_info.get("result"),
                }
            )

    if not completed_tasks:
        return WeChatArticleResponse(
            success=False,
            message="No completed WeChat article generation tasks found for this translation",
            data=None,
        )

    # Get the most recent completed task
    latest_task = max(completed_tasks, key=lambda t: t["completed_at"])

    # Extract output directory from the task result
    result = latest_task.get("result")
    if not result:
        return WeChatArticleResponse(
            success=False,
            message="Could not find result for WeChat articles",
            data=None,
        )

    # The result is the article summary from get_article_summary()
    # It uses "output_directory" field name, not "output_dir"
    output_dir = (
        result.get("output_directory") if isinstance(result, dict) else None
    )
    if not output_dir:
        return WeChatArticleResponse(
            success=False,
            message="Could not find output directory for WeChat articles",
            data=None,
        )

    try:
        # Read metadata.json file
        metadata_path = Path(output_dir) / "metadata.json"
        if not metadata_path.exists():
            return WeChatArticleResponse(
                success=False,
                message=f"Metadata file not found: {metadata_path}",
                data=None,
            )

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return WeChatArticleResponse(
            success=True,
            message="WeChat article metadata retrieved successfully",
            data=metadata,
        )

    except Exception as e:
        return WeChatArticleResponse(
            success=False,
            message=f"Failed to read metadata: {str(e)}",
            data=None,
        )


@router.get("/{translation_id}/wechat-article-view")
async def view_wechat_article_html(
    translation_id: str,
    request: Request,
    db: Session = Depends(get_db),
    service: RepositoryService = Depends(get_repository_service),
    config_facade: ConfigFacade = Depends(get_config_facade_dependency),
):
    """Serve WeChat article HTML content through web endpoint."""
    try:
        from ..utils.wechat_article_runner import WeChatArticleRunner

        # Get metadata to find HTML file path
        runner = WeChatArticleRunner(config_facade=config_facade)

        html_content = None
        content_type = "text/html; charset=utf-8"

        # Fallback: try to find HTML file in metadata
        if not html_content:
            # Check completed tasks for this translation
            completed_tasks = []
            for task_id, task_info in request.app.state.wechat_tasks.items():
                if (
                    task_info.get("translation_id") == translation_id
                    and task_info.get("status") == "completed"
                    and task_info.get("result", {}).get("output_directory")
                ):

                    result = task_info["result"]
                    completed_tasks.append(
                        {
                            "task_id": task_id,
                            "completed_at": task_info.get("completed_at"),
                            "result": result,
                        }
                    )

            if completed_tasks:
                # Get the most recent completed task
                latest_task = max(
                    completed_tasks, key=lambda t: t["completed_at"]
                )
                result = latest_task.get("result")

                if result and result.get("output_directory"):
                    output_dir = Path(result["output_directory"])
                    html_file = output_dir / "article.html"
                    if html_file.exists():
                        html_content = html_file.read_text(encoding="utf-8")

        # Final fallback: try to read from metadata file
        if not html_content:
            try:
                # Get metadata endpoint result
                metadata_response = await get_wechat_article_metadata(
                    translation_id, request, db, service
                )
                if metadata_response.success and metadata_response.data:
                    metadata = metadata_response.data
                    if metadata.get("source_html_path"):
                        html_path = Path(metadata["source_html_path"])
                        if html_path.exists():
                            html_content = html_path.read_text(
                                encoding="utf-8"
                            )
            except Exception as e:
                print(
                    f"⚠️ Warning: Could not read metadata for HTML fallback: {e}"
                )

        if html_content:
            return Response(
                content=html_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'inline; filename="wechat_article_{translation_id}.html"',
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                },
            )
        else:
            raise HTTPException(
                status_code=404, detail="HTML article not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Failed to serve WeChat article HTML: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to serve article: {str(e)}"
        )
