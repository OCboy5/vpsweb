"""
VPSWeb Web UI - Translation API Endpoints v0.3.1

API endpoints for translation management and workflow operations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...repository.database import get_db
from ...repository.service import RepositoryWebService
from ...repository.schemas import (
    TranslationCreate,
    TranslationUpdate,
    TranslationResponse,
    AILogCreate,
    HumanNoteCreate,
    TranslationWorkflowStepResponse,
    TranslatorType,
    WorkflowStepType,
)
from ..schemas import (
    WebAPIResponse,
    WorkflowMode,
    TranslationFormResponse,
    TranslationFormCreate,
    TranslationRequest,
)
from ..services.interfaces import IWorkflowServiceV2
from ..container import container


router = APIRouter(tags=["translations"])


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryWebService:
    """Dependency to get repository service instance"""
    return RepositoryWebService(db)


def get_workflow_service() -> IWorkflowServiceV2:
    """Dependency to get workflow service instance."""
    return container.resolve(IWorkflowServiceV2)


@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_translation(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    workflow_service: IWorkflowServiceV2 = Depends(get_workflow_service),
):
    """
    Trigger a new translation workflow.
    """
    print(
        f"🚀 [API] Trigger endpoint called with poem_id={request.poem_id}, target_lang={request.target_lang}, workflow_mode={request.workflow_mode}"
    )
    print(f"🔧 [API] workflow_service type: {type(workflow_service)}")

    task_id = await workflow_service.start_translation_workflow(
        poem_id=request.poem_id,
        target_lang=request.target_lang,
        workflow_mode=request.workflow_mode,
        background_tasks=background_tasks,
    )

    print(f"✅ [API] Got task_id: {task_id}")

    return {
        "success": True,
        "task_id": task_id,
        "message": "Translation workflow started successfully",
    }


@router.get("/", response_model=Dict[str, Any])
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
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get list of translations with optional filtering and pagination.
    """
    raw_translations = service.repo.translations.get_multi(
        skip=skip,
        limit=limit,
        poem_id=poem_id,
        target_language=target_language,
        translator_type=translator_type,
    )

    # Convert SQLAlchemy models to Pydantic response schemas
    translations = [TranslationResponse.model_validate(t) for t in raw_translations]

    return {
        "translations": translations,
        "total_count": len(translations),
        "skip": skip,
        "limit": limit,
    }


@router.post("/", response_model=TranslationResponse)
async def create_translation(
    translation_data: TranslationCreate,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Create a new human translation.
    """
    poem = service.repo.poems.get_by_id(translation_data.poem_id)
    if not poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{translation_data.poem_id}' not found",
        )

    try:
        translation = service.repo.translations.create(translation_data)
        return translation
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to create translation: {str(e)}"
        )


@router.get("/{translation_id}", response_model=TranslationResponse)
async def get_translation(
    translation_id: str, service: RepositoryWebService = Depends(get_repository_service)
):
    """
    Get detailed information about a specific translation.
    """
    translation = service.repo.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )
    return translation


@router.put("/{translation_id}", response_model=TranslationResponse)
async def update_translation(
    translation_id: str,
    translation_data: TranslationUpdate,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Update an existing translation.
    """
    existing_translation = service.repo.translations.get_by_id(translation_id)
    if not existing_translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    try:
        updated_translation = service.repo.translations.update(
            translation_id, translation_data
        )
        return updated_translation
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to update translation: {str(e)}"
        )


class QualityRatingUpdate(BaseModel):
    """Schema for updating translation quality rating"""

    quality_rating: int = Field(
        ..., ge=0, le=10, description="Quality rating from 0-10 (0 = unrated)"
    )


@router.put("/{translation_id}/quality", response_model=WebAPIResponse)
async def update_quality_rating(
    translation_id: str,
    rating_data: QualityRatingUpdate,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Update the quality rating of a translation.
    """
    existing_translation = service.repo.translations.get_by_id(translation_id)
    if not existing_translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    try:
        # Update only the quality rating using a raw SQL statement
        from sqlalchemy import text

        result = service.db.execute(
            text("UPDATE translations SET quality_rating = :rating WHERE id = :id"),
            {"rating": rating_data.quality_rating, "id": translation_id},
        )
        service.db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Translation with ID '{translation_id}' not found",
            )

        rating_text = (
            "unrated"
            if rating_data.quality_rating == 0
            else f"{rating_data.quality_rating}/10"
        )
        return WebAPIResponse(
            success=True,
            message=f"Quality rating updated to {rating_text} successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        service.db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Failed to update quality rating: {str(e)}"
        )


@router.delete("/{translation_id}", response_model=WebAPIResponse)
async def delete_translation(
    translation_id: str, service: RepositoryWebService = Depends(get_repository_service)
):
    """
    Delete a translation and its associated logs and notes.
    """
    existing_translation = service.repo.translations.get_by_id(translation_id)
    if not existing_translation:
        raise HTTPException(
            status_code=404, detail=f"Translation with ID '{translation_id}' not found"
        )

    try:
        service.repo.translations.delete(translation_id)
        return WebAPIResponse(success=True, message="Translation deleted successfully")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to delete translation: {str(e)}"
        )


# Human Note Management
class HumanNoteCreateRequest(BaseModel):
    """Schema for creating a human note"""

    translation_id: str = Field(..., description="Translation ID to attach the note to")
    note_text: str = Field(..., min_length=1, description="The note text content")


class HumanNoteResponse(BaseModel):
    """Schema for human note response"""

    id: str
    translation_id: str
    note_text: str
    created_at: str

    @classmethod
    def model_validate(cls, obj):
        """Custom model validation to handle datetime objects"""
        if hasattr(obj, "created_at") and obj.created_at:
            # Convert datetime to string
            created_at_str = (
                obj.created_at.isoformat()
                if hasattr(obj.created_at, "isoformat")
                else str(obj.created_at)
            )
            return cls(
                id=obj.id,
                translation_id=obj.translation_id,
                note_text=obj.note_text,
                created_at=created_at_str,
            )
        return super().model_validate(obj)


@router.post("/human-notes/", response_model=Dict[str, Any])
async def create_human_note(
    note_data: HumanNoteCreateRequest,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Create a new human note for a translation.
    """
    # Verify the translation exists
    translation = service.repo.translations.get_by_id(note_data.translation_id)
    if not translation:
        raise HTTPException(
            status_code=404,
            detail=f"Translation with ID '{note_data.translation_id}' not found",
        )

    # Verify it's a human translation
    if translation.translator_type != "human":
        raise HTTPException(
            status_code=400,
            detail=f"Human notes can only be added to human translations. This translation is of type '{translation.translator_type}'",
        )

    try:
        # Create the human note
        human_note_create = HumanNoteCreate(
            translation_id=note_data.translation_id, note_text=note_data.note_text
        )

        human_note = service.repo.human_notes.create(human_note_create)

        return {
            "success": True,
            "message": "Human note added successfully",
            "data": HumanNoteResponse.model_validate(human_note),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to create human note: {str(e)}"
        )


@router.get("/{translation_id}/human-notes", response_model=Dict[str, Any])
async def list_human_notes(
    translation_id: str,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get all human notes for a specific translation.
    """
    # Verify the translation exists
    translation = service.repo.translations.get_by_id(translation_id)
    if not translation:
        raise HTTPException(
            status_code=404,
            detail=f"Translation with ID '{translation_id}' not found",
        )

    try:
        # Get human notes for this translation
        human_notes = service.repo.human_notes.get_by_translation(translation_id)

        return {
            "success": True,
            "data": [HumanNoteResponse.model_validate(note) for note in human_notes],
            "count": len(human_notes),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch human notes: {str(e)}"
        )


@router.delete("/human-notes/{note_id}", response_model=WebAPIResponse)
async def delete_human_note(
    note_id: str,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Delete a human note.
    """
    try:
        # Check if the note exists
        note = service.repo.human_notes.get_by_id(note_id)
        if not note:
            raise HTTPException(
                status_code=404,
                detail=f"Human note with ID '{note_id}' not found",
            )

        # Delete the note
        service.repo.human_notes.delete(note_id)

        return WebAPIResponse(success=True, message="Human note deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to delete human note: {str(e)}"
        )
