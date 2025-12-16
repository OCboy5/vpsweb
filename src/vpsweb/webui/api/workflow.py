"""
VPSWeb Web UI - Workflow API Endpoints v0.3.12

API endpoints for managing and executing translation workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from vpsweb.repository.database import get_db
from vpsweb.webui.services.interfaces import (
    IWorkflowServiceV2,
    ITaskManagementServiceV2,
)
from vpsweb.webui.services.services import (
    WorkflowServiceV2,
    TaskManagementServiceV2,
)
from vpsweb.webui.schemas import TranslationRequest, WebAPIResponse
from vpsweb.core.container import get_container, DIContainer

router = APIRouter()


def get_workflow_service(db: Session = Depends(get_db)) -> IWorkflowServiceV2:
    """Dependency to get workflow service instance."""
    from vpsweb.core.container import get_container

    try:
        # Use the global container that's configured in the main app
        container = get_container()
        return container.resolve(IWorkflowServiceV2)
    except RuntimeError:
        # Fallback: if no global container is set, create and configure one
        from vpsweb.webui.main import ApplicationFactoryV2
        from vpsweb.repository.database import create_session

        # Create a minimal container with just the workflow service
        from vpsweb.core.container import DIContainer
        from vpsweb.webui.services.services import (
            WorkflowServiceV2,
            TaskManagementServiceV2,
        )
        from vpsweb.webui.services.interfaces import ITaskManagementServiceV2

        container = DIContainer()
        # Register minimal dependencies needed for workflow service
        container.register_instance(
            ITaskManagementServiceV2, TaskManagementServiceV2({}, logger=None)
        )
        container.register_singleton(IWorkflowServiceV2, WorkflowServiceV2)

        return container.resolve(IWorkflowServiceV2)


@router.post("/translate", response_model=WebAPIResponse)
async def start_translation_workflow(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    workflow_service: IWorkflowServiceV2 = Depends(get_workflow_service),
):
    """
    Start a new translation workflow as a background task.
    """
    try:
        # Fetch the poem to get the source language
        poem = workflow_service.repository_service.repo.poems.get_by_id(request.poem_id)
        if not poem:
            raise HTTPException(
                status_code=404, detail=f"Poem with ID {request.poem_id} not found"
            )

        source_lang = poem.source_language

        task_id = await workflow_service.start_translation_workflow(
            poem_id=request.poem_id,
            source_lang=source_lang,
            target_lang=request.target_lang,
            workflow_mode=request.workflow_mode,
            background_tasks=background_tasks,
        )
        return WebAPIResponse(
            success=True,
            message="Translation workflow started successfully.",
            data={"task_id": task_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel")
async def cancel_workflow_task(
    task_id: str,
    workflow_service: IWorkflowServiceV2 = Depends(get_workflow_service),
):
    """
    Cancel a background translation workflow task.
    """
    try:
        # Get the task first
        task = await workflow_service.get_task_status(task_id)

        if task.get("status") == "completed":
            raise HTTPException(
                status_code=404, detail="Task not found or already completed."
            )

        success = await workflow_service.cancel_task(task_id)

        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Task cancelled successfully.",
                }
            )
        else:
            raise HTTPException(
                status_code=404, detail="Task not found or already completed."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
