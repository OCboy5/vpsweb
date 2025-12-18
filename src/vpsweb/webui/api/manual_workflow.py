"""
VPSWeb Web UI - Manual Workflow API Endpoints

API endpoints for managing manual translation workflows where users
interact with external LLM services through copy-paste operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vpsweb.repository.database import get_db
from vpsweb.webui.schemas import WebAPIResponse
from vpsweb.webui.services.manual_workflow_service import ManualWorkflowService


# Request models
class ManualWorkflowStartRequest(BaseModel):
    """Request model for starting a manual workflow."""

    target_lang: str = Field(..., description="Target language for translation")


class ManualWorkflowStepRequest(BaseModel):
    """Request model for submitting a manual workflow step."""

    session_id: str = Field(..., description="Manual workflow session ID")
    llm_response: str = Field(..., description="Response from external LLM")
    llm_model_name: str = Field(..., description="Name of the LLM model used")


router = APIRouter()


# Global instance to persist sessions across requests
_manual_workflow_service_instance = None


def get_manual_workflow_service(
    db: Session = Depends(get_db),
) -> ManualWorkflowService:
    """Dependency to get manual workflow service instance."""
    global _manual_workflow_service_instance

    if _manual_workflow_service_instance is not None:
        return _manual_workflow_service_instance

    # Import here to avoid circular imports
    from vpsweb.core.container import get_container

    try:
        container = get_container()

        # Get required services from container
        from vpsweb.repository.service import RepositoryWebService
        from vpsweb.services.parser import OutputParser
        from vpsweb.services.prompts import PromptService
        from vpsweb.utils.storage import StorageHandler
        from vpsweb.webui.services.interfaces import IWorkflowServiceV2

        # Resolve dependencies
        prompt_service = container.resolve_by_type(PromptService)
        output_parser = OutputParser()
        workflow_service = container.resolve(IWorkflowServiceV2)
        repository_service = container.resolve_by_type(RepositoryWebService)
        storage_handler = container.resolve_by_type(StorageHandler)

        # Create and store singleton instance
        _manual_workflow_service_instance = ManualWorkflowService(
            prompt_service=prompt_service,
            output_parser=output_parser,
            workflow_service=workflow_service,
            repository_service=repository_service,
            storage_handler=storage_handler,
        )

    except Exception:
        # Fallback: create services manually
        from vpsweb.core.container import DIContainer
        from vpsweb.repository.service import RepositoryWebService
        from vpsweb.services.parser import OutputParser
        from vpsweb.services.prompts import PromptService
        from vpsweb.utils.storage import StorageHandler
        from vpsweb.webui.services.interfaces import ITaskManagementServiceV2
        from vpsweb.webui.services.services import (TaskManagementServiceV2,
                                                    WorkflowServiceV2)

        # Create container
        container = DIContainer()

        # Register dependencies
        container.register_instance(
            ITaskManagementServiceV2, TaskManagementServiceV2({}, logger=None)
        )
        container.register_singleton(type(WorkflowServiceV2), WorkflowServiceV2)

        # Create services
        repository_service = RepositoryWebService(db)
        prompt_service = PromptService()
        output_parser = OutputParser()
        storage_handler = StorageHandler()
        workflow_service = WorkflowServiceV2(
            repository_service=repository_service,
            storage_handler=storage_handler,
            task_service=TaskManagementServiceV2(),
        )

        # Create and store singleton instance
        _manual_workflow_service_instance = ManualWorkflowService(
            prompt_service=prompt_service,
            output_parser=output_parser,
            workflow_service=workflow_service,
            repository_service=repository_service,
            storage_handler=storage_handler,
        )

    return _manual_workflow_service_instance


@router.post("/poems/{poem_id}/translate/manual/start", response_model=WebAPIResponse)
async def start_manual_workflow(
    poem_id: str,
    request: ManualWorkflowStartRequest,
    manual_workflow_service: ManualWorkflowService = Depends(
        get_manual_workflow_service
    ),
):
    """
    Start a new manual translation workflow session.

    This initializes a session where users can manually interact with external LLMs.
    """
    try:
        # Start the session
        result = await manual_workflow_service.start_session(
            poem_id=poem_id, target_lang=request.target_lang
        )

        return WebAPIResponse(
            success=True,
            message="Manual workflow session started successfully.",
            data=result,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/poems/{poem_id}/translate/manual/step/{step_name}",
    response_model=WebAPIResponse,
)
async def submit_manual_workflow_step(
    poem_id: str,
    step_name: str,
    request: ManualWorkflowStepRequest,
    manual_workflow_service: ManualWorkflowService = Depends(
        get_manual_workflow_service
    ),
):
    """
    Submit a step response in the manual workflow.

    This processes the user's LLM response and either continues to the next step
    or completes the workflow.
    """
    try:
        # Submit the step
        result = await manual_workflow_service.submit_step(
            session_id=request.session_id,
            step_name=step_name,
            llm_response=request.llm_response,
            model_name=request.llm_model_name,
        )

        if result.get("status") == "completed":
            return WebAPIResponse(
                success=True,
                message="Manual workflow completed successfully!",
                data=result,
            )
        else:
            return WebAPIResponse(
                success=True,
                message="Step processed successfully. Ready for next step.",
                data=result,
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/poems/{poem_id}/translate/manual/session/{session_id}",
    response_model=WebAPIResponse,
)
async def get_manual_workflow_session(
    poem_id: str,
    session_id: str,
    manual_workflow_service: ManualWorkflowService = Depends(
        get_manual_workflow_service
    ),
):
    """
    Get the current state of a manual workflow session.
    """
    try:
        session = await manual_workflow_service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Validate session belongs to the specified poem
        if session.get("poem_id") != poem_id:
            raise HTTPException(
                status_code=400, detail="Session does not belong to this poem"
            )

        return WebAPIResponse(
            success=True,
            message="Session retrieved successfully.",
            data=session,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate/manual/cleanup", response_model=WebAPIResponse)
async def cleanup_expired_sessions(
    max_age_hours: int = 24,
    manual_workflow_service: ManualWorkflowService = Depends(
        get_manual_workflow_service
    ),
):
    """
    Clean up expired manual workflow sessions.

    This is a maintenance endpoint that removes old sessions.
    """
    try:
        cleaned_count = manual_workflow_service.cleanup_expired_sessions(max_age_hours)

        return WebAPIResponse(
            success=True,
            message=f"Cleaned up {cleaned_count} expired sessions.",
            data={"cleaned_count": cleaned_count},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
