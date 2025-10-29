"""
VPSWeb Web UI - Translation API Endpoints v0.3.1

API endpoints for translation management and workflow operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.schemas import (
    TranslationCreate,
    TranslationUpdate,
    TranslationResponse,
    AILogCreate,
    HumanNoteCreate,
    TranslationWorkflowStepResponse,
)
from ..schemas import (
    TranslationFormCreate,
    TranslationFormRequest,
    WebAPIResponse,
    TranslationFormResponse,
    TranslatorType,
    WorkflowMode,
)

router = APIRouter()


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


@router.get("/", response_model=List[TranslationResponse])
async def list_translations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of records to return"
    ),
    poem_id: Optional[str] = Query(None, description="Filter by poem ID"),
    target_language: Optional[str] = Query(
        None, description="Filter by target language"
    ),
    translator_type: Optional[str] = Query(
        None, description="Filter by translator type"
    ),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get list of translations with optional filtering and pagination.

    **Parameters:**
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **poem_id**: Filter translations by poem ID
    - **target_language**: Filter translations by target language
    - **translator_type**: Filter translations by translator type

    **Returns:**
    - List of translations matching the criteria
    """
    translations = service.translations.get_multi(
        skip=skip,
        limit=limit,
        poem_id=poem_id,
        target_language=target_language,
        translator_type=translator_type,
    )

    # Convert database models to Pydantic response models with workflow fields
    result = []
    for translation in translations:
        # Load workflow_mode for AI translations
        workflow_mode = None
        if translation.translator_type == "ai":
            ai_logs = service.ai_logs.get_by_translation(translation.id)
            workflow_mode = ai_logs[0].workflow_mode if ai_logs else None

        # Convert to dict first - now the schema handles workflow fields automatically
        translation_dict = TranslationResponse.model_validate(translation).model_dump()

        # Add workflow_mode to the response
        translation_dict["workflow_mode"] = workflow_mode

        result.append(translation_dict)

    return result


@router.post("/", response_model=TranslationResponse)
async def create_translation(
    translation_data: TranslationFormCreate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Create a new human translation.

    **Request Body:**
    - **poem_id**: ID of the poem to translate
    - **target_language**: Target language code (2-10 chars)
    - **translator_name**: Human translator name (max 200 chars)
    - **translated_text**: Translated text (required, min 1 char)
    - **quality_rating**: Quality rating (1-5)

    **Returns:**
    - Created translation with generated ID and timestamps
    """
    # Check if poem exists
    poem = service.poems.get_by_id(translation_data.poem_id)
    if not poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{translation_data.poem_id}' not found",
        )

    # Convert form schema to creation schema
    translation_create = TranslationCreate(
        poem_id=translation_data.poem_id,
        translator_type=TranslatorType.HUMAN,
        translator_info=translation_data.translator_name or "Anonymous",
        target_language=translation_data.target_language,
        translated_text=translation_data.translated_text,
        translated_poem_title=translation_data.translated_poem_title
        or "",  # 🎯 Add for consistency (typically empty for human translations)
        translated_poet_name=translation_data.translated_poet_name
        or "",  # 🎯 Add for consistency (typically empty for human translations)
        quality_rating=translation_data.quality_rating,
    )

    try:
        translation = service.translations.create(translation_create)
        # Convert to response format
        return {
            "id": translation.id,
            "poem_id": translation.poem_id,
            "translator_type": translation.translator_type,
            "translator_info": translation.translator_info,
            "target_language": translation.target_language,
            "translated_text": translation.translated_text,
            "quality_rating": translation.quality_rating,
            "created_at": translation.created_at,
            "translation_id": translation.id,
            "model_name": (
                translation.translator_info
                if translation.translator_type == "ai"
                else None
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to create translation: {str(e)}"
        )


@router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(
    translation_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Get detailed information about a specific translation.

    **Path Parameters:**
    - **translation_id**: ULID of the translation to retrieve

    **Returns:**
    - Complete translation information including associated logs and notes
    """
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Normalize language code format (e.g., 'zh-cn' -> 'zh-CN')
    target_language = translation.target_language
    if "-" in target_language and len(target_language.split("-")) == 2:
        lang, country = target_language.split("-")
        target_language = f"{lang}-{country.upper()}"

    # Convert to response format
    return {
        "id": translation.id,
        "poem_id": translation.poem_id,
        "translator_type": translation.translator_type,
        "translator_info": translation.translator_info,
        "target_language": target_language,
        "translated_text": translation.translated_text,
        "translated_poem_title": translation.translated_poem_title,
        "translated_poet_name": translation.translated_poet_name,
        "quality_rating": translation.quality_rating,
        "raw_path": translation.raw_path,
        "created_at": translation.created_at,
        "translation_id": translation.id,
        "model_name": (
            translation.translator_info if translation.translator_type == "ai" else None
        ),
    }


@router.put("/{translation_id}", response_model=TranslationResponse)
async def update_translation(
    translation_id: str,
    translation_data: TranslationFormCreate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Update an existing translation.

    **Path Parameters:**
    - **translation_id**: ULID of the translation to update

    **Request Body:**
    - Same as create translation endpoint

    **Returns:**
    - Updated translation information
    """
    # Check if translation exists
    existing_translation = service.translations.get_by_id(translation_id)
    if not existing_translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Convert form schema to update schema
    translation_update = TranslationUpdate(
        translator_info=translation_data.translator_name or "Anonymous",
        target_language=translation_data.target_language,
        translated_text=translation_data.translated_text,
        quality_rating=translation_data.quality_rating,
    )

    try:
        updated_translation = service.translations.update(
            translation_id, translation_update
        )
        # Convert to response format
        return {
            "id": updated_translation.id,
            "poem_id": updated_translation.poem_id,
            "translator_type": updated_translation.translator_type,
            "translator_info": updated_translation.translator_info,
            "target_language": updated_translation.target_language,
            "translated_text": updated_translation.translated_text,
            "quality_rating": updated_translation.quality_rating,
            "created_at": updated_translation.created_at,
            "translation_id": updated_translation.id,
            "model_name": (
                updated_translation.translator_info
                if updated_translation.translator_type == "ai"
                else None
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to update translation: {str(e)}"
        )


@router.delete("/{translation_id}", response_model=WebAPIResponse)
async def delete_translation(
    translation_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Delete a translation and its associated logs and notes.

    **Path Parameters:**
    - **translation_id**: ULID of the translation to delete

    **Returns:**
    - Success/failure status
    """
    # Check if translation exists
    existing_translation = service.translations.get_by_id(translation_id)
    if not existing_translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    try:
        service.translations.delete(translation_id)
        return WebAPIResponse(success=True, message="Translation deleted successfully")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to delete translation: {str(e)}"
        )


@router.post("/trigger", response_model=TranslationFormResponse)
async def trigger_translation_workflow(
    workflow_request: TranslationFormRequest,
    background_tasks: BackgroundTasks,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Trigger an AI translation workflow for a poem.

    **Request Body:**
    - **poem_id**: ID of the poem to translate
    - **target_lang**: Target language code (2-10 chars)
    - **workflow_mode**: Translation workflow mode (reasoning/non_reasoning/hybrid)

    **Returns:**
    - Translation workflow initiation response
    """
    # Check if poem exists
    poem = service.poems.get_by_id(workflow_request.poem_id)
    if not poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{workflow_request.poem_id}' not found",
        )

    # Check if translation already exists
    existing_translations = service.translations.get_by_poem_id(
        workflow_request.poem_id, target_language=workflow_request.target_lang
    )
    if existing_translations:
        return TranslationFormResponse(
            success=False,
            message=f"Translation to {workflow_request.target_lang} already exists",
            data={"existing_translations": len(existing_translations)},
        )

    try:
        # For now, create a placeholder translation
        # In a real implementation, this would trigger the actual AI workflow
        placeholder_translation = TranslationCreate(
            poem_id=workflow_request.poem_id,
            translator_type=TranslatorType.AI,
            translator_info="AI Translation System",
            target_language=workflow_request.target_lang,
            translated_text="[Translation in progress...]",
            quality_rating=None,
        )

        translation = service.translations.create(placeholder_translation)

        # Add background task to process the translation
        background_tasks.add_task(
            process_translation_background,
            translation.id,
            poem.original_text,
            workflow_request.target_lang,
            workflow_request.workflow_mode,
        )

        return TranslationFormResponse(
            success=True,
            message="Translation workflow started successfully",
            translation_id=translation.id,
            model_name="AI Translation System",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to trigger translation workflow: {str(e)}"
        )


@router.post("/{translation_id}/notes", response_model=WebAPIResponse)
async def add_human_note(
    translation_id: str,
    note_text: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Add a human note to a translation.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Request Body:**
    - **note_text**: Note text content

    **Returns:**
    - Success/failure status
    """
    # Check if translation exists
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    try:
        note_create = HumanNoteCreate(
            translation_id=translation_id, note_text=note_text
        )
        service.human_notes.create(note_create)

        return WebAPIResponse(success=True, message="Human note added successfully")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to add human note: {str(e)}"
        )


@router.get("/{translation_id}/notes", response_model=List[dict])
async def get_translation_notes(
    translation_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Get all human notes for a translation.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Returns:**
    - List of human notes for the translation
    """
    # Check if translation exists
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Get notes for this translation
    notes = service.human_notes.get_by_translation_id(translation_id)

    return [
        {
            "id": note.id,
            "note_text": note.note_text,
            "created_at": note.created_at.isoformat(),
        }
        for note in notes
    ]


@router.get(
    "/{translation_id}/workflow-steps",
    response_model=List[TranslationWorkflowStepResponse],
)
async def get_translation_workflow_steps(
    translation_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Get all workflow steps for a translation.

    This endpoint provides access to the detailed T-E-T workflow content
    that is now stored in the database instead of just JSON files.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Returns:**
    - List of workflow steps (initial_translation, editor_review, revised_translation)
    - Each step includes content, notes, metrics, and timing information
    """
    # Check if translation exists
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Get workflow steps for this translation
    workflow_steps = service.workflow_steps.get_by_translation(translation_id)

    # Convert to response format
    return [
        TranslationWorkflowStepResponse(
            id=step.id,
            translation_id=step.translation_id,
            ai_log_id=step.ai_log_id,
            workflow_id=step.workflow_id,
            step_type=step.step_type,
            step_order=step.step_order,
            content=step.content,
            notes=step.notes,
            model_info=step.model_info,
            tokens_used=step.tokens_used,
            prompt_tokens=step.prompt_tokens,
            completion_tokens=step.completion_tokens,
            duration_seconds=step.duration_seconds,
            cost=step.cost,
            additional_metrics=step.additional_metrics,
            translated_title=step.translated_title,
            translated_poet_name=step.translated_poet_name,
            timestamp=step.timestamp,
            created_at=step.created_at,
        )
        for step in workflow_steps
    ]


@router.get(
    "/{translation_id}/workflow-steps/{step_id}",
    response_model=TranslationWorkflowStepResponse,
)
async def get_workflow_step(
    translation_id: str,
    step_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get a specific workflow step for a translation.

    This endpoint provides detailed information about a single workflow step
    including all content, metrics, and timing data.

    **Path Parameters:**
    - **translation_id**: ULID of the translation
    - **step_id**: ULID of the specific workflow step

    **Returns:**
    - Detailed workflow step information
    """
    # Check if translation exists
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Get specific workflow step
    workflow_step = service.workflow_steps.get_by_id(step_id)
    if not workflow_step:
        raise HTTPException(
            status_code=404, detail=f"Workflow step with ID '{step_id}' not found"
        )

    # Verify the step belongs to the specified translation
    if workflow_step.translation_id != translation_id:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow step '{step_id}' does not belong to translation '{translation_id}'",
        )

    return TranslationWorkflowStepResponse(
        id=workflow_step.id,
        translation_id=workflow_step.translation_id,
        ai_log_id=workflow_step.ai_log_id,
        workflow_id=workflow_step.workflow_id,
        step_type=workflow_step.step_type,
        step_order=workflow_step.step_order,
        content=workflow_step.content,
        notes=workflow_step.notes,
        model_info=workflow_step.model_info,
        tokens_used=workflow_step.tokens_used,
        prompt_tokens=workflow_step.prompt_tokens,
        completion_tokens=workflow_step.completion_tokens,
        duration_seconds=workflow_step.duration_seconds,
        cost=workflow_step.cost,
        additional_metrics=workflow_step.additional_metrics,
        translated_title=workflow_step.translated_title,
        translated_poet_name=workflow_step.translated_poet_name,
        timestamp=workflow_step.timestamp,
        created_at=workflow_step.created_at,
    )


@router.get("/{translation_id}/workflow-summary")
async def get_workflow_summary(
    translation_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Get a summary of the workflow execution for a translation.

    This endpoint provides aggregated metrics and overview information
    about the complete T-E-T workflow execution.

    **Path Parameters:**
    - **translation_id**: ULID of the translation

    **Returns:**
    - Workflow summary with aggregated metrics
    - Step counts and overall performance data
    """
    # Check if translation exists
    translation = service.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    # Get workflow steps for this translation
    workflow_steps = service.workflow_steps.get_by_translation(translation_id)

    # Get AI log information
    ai_logs = service.ai_logs.get_by_translation(translation_id)
    ai_log = ai_logs[0] if ai_logs else None

    # Calculate aggregated metrics
    total_tokens = sum(step.tokens_used or 0 for step in workflow_steps)
    total_cost = sum(step.cost or 0.0 for step in workflow_steps)
    total_duration = sum(step.duration_seconds or 0.0 for step in workflow_steps)

    # Group by step type
    step_counts = {}
    step_metrics = {}

    for step in workflow_steps:
        step_type = step.step_type
        step_counts[step_type] = step_counts.get(step_type, 0) + 1

        if step_type not in step_metrics:
            step_metrics[step_type] = {
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_duration": 0.0,
                "count": 0,
            }

        step_metrics[step_type]["total_tokens"] += step.tokens_used or 0
        step_metrics[step_type]["total_cost"] += step.cost or 0.0
        step_metrics[step_type]["total_duration"] += step.duration_seconds or 0.0
        step_metrics[step_type]["count"] += 1

    return {
        "translation_id": translation_id,
        "workflow_id": workflow_steps[0].workflow_id if workflow_steps else None,
        "ai_log_id": ai_log.id if ai_log else None,
        "model_name": ai_log.model_name if ai_log else None,
        "workflow_mode": ai_log.workflow_mode if ai_log else None,
        "total_steps": len(workflow_steps),
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "total_duration": total_duration,
        "step_counts": step_counts,
        "step_metrics": step_metrics,
        "created_at": ai_log.created_at.isoformat() if ai_log else None,
        "has_workflow_steps": len(workflow_steps) > 0,
    }


# Background task function (placeholder for actual AI workflow)
async def process_translation_background(
    translation_id: str,
    original_text: str,
    target_language: str,
    workflow_mode: WorkflowMode,
):
    """
    Background task to process AI translation workflow.

    In a real implementation, this would:
    1. Call the AI translation service
    2. Process the result through the workflow
    3. Update the translation with the final result
    4. Log the process and metrics
    """
    # This is a placeholder implementation
    # In production, this would integrate with the actual translation workflow
    pass
