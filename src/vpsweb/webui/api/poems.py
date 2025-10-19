"""
VPSWeb Web UI - Poem API Endpoints v0.3.1

API endpoints for poem management operations with comprehensive CRUD functionality.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.schemas import (
    PoemCreate, PoemUpdate, PoemResponse
)
from ..schemas import (
    PoemFormCreate, WebAPIResponse, PaginationInfo
)

router = APIRouter()


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


@router.get("/", response_model=List[PoemResponse])
async def list_poems(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    poet_name: Optional[str] = Query(None, description="Filter by poet name"),
    language: Optional[str] = Query(None, description="Filter by source language"),
    title_search: Optional[str] = Query(None, description="Search in poem title"),
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Get list of poems with optional filtering and pagination.

    **Parameters:**
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **poet_name**: Filter poems by poet name
    - **language**: Filter poems by source language
    - **title_search**: Search poems by title (partial match)

    **Returns:**
    - List of poems matching the criteria
    """
    poems = service.poems.get_multi(
        skip=skip,
        limit=limit,
        poet_name=poet_name,
        language=language,
        title_search=title_search
    )
    return poems


@router.post("/", response_model=PoemResponse)
async def create_poem(
    poem_data: PoemFormCreate,
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Create a new poem in the repository.

    **Request Body:**
    - **poet_name**: Name of the poet (required, 1-200 chars)
    - **poem_title**: Title of the poem (required, 1-300 chars)
    - **source_language**: Source language code (required, 2-10 chars)
    - **original_text**: Original poem text (required, min 1 char)
    - **metadata**: Optional metadata JSON string (max 1000 chars)

    **Returns:**
    - Created poem with generated ID and timestamps
    """
    # Convert form schema to creation schema
    poem_create = PoemCreate(
        poet_name=poem_data.poet_name,
        poem_title=poem_data.poem_title,
        source_language=poem_data.source_language,
        original_text=poem_data.original_text,
        metadata_json=poem_data.metadata
    )

    try:
        poem = service.poems.create(poem_create)
        return poem
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create poem: {str(e)}"
        )


@router.get("/{poem_id}", response_model=PoemResponse)
async def get_poem(
    poem_id: str,
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Get detailed information about a specific poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to retrieve

    **Returns:**
    - Complete poem information including metadata
    """
    poem = service.poems.get_by_id(poem_id)
    if not poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{poem_id}' not found"
        )
    return poem


@router.put("/{poem_id}", response_model=PoemResponse)
async def update_poem(
    poem_id: str,
    poem_data: PoemFormCreate,
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Update an existing poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to update

    **Request Body:**
    - Same as create poem endpoint

    **Returns:**
    - Updated poem information
    """
    # Check if poem exists
    existing_poem = service.poems.get_by_id(poem_id)
    if not existing_poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{poem_id}' not found"
        )

    # Convert form schema to update schema
    poem_update = PoemUpdate(
        poet_name=poem_data.poet_name,
        poem_title=poem_data.poem_title,
        source_language=poem_data.source_language,
        original_text=poem_data.original_text,
        metadata_json=poem_data.metadata
    )

    try:
        updated_poem = service.poems.update(poem_id, poem_update)
        return updated_poem
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update poem: {str(e)}"
        )


@router.delete("/{poem_id}", response_model=WebAPIResponse)
async def delete_poem(
    poem_id: str,
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Delete a poem and all its associated translations.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to delete

    **Returns:**
    - Success/failure status
    """
    # Check if poem exists
    existing_poem = service.poems.get_by_id(poem_id)
    if not existing_poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{poem_id}' not found"
        )

    try:
        service.poems.remove(poem_id)
        return WebAPIResponse(
            success=True,
            message=f"Poem '{existing_poem.poem_title}' deleted successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete poem: {str(e)}"
        )


@router.get("/{poem_id}/translations", response_model=List[dict])
async def get_poem_translations(
    poem_id: str,
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Get all translations for a specific poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem

    **Returns:**
    - List of translations for the poem
    """
    # Check if poem exists
    poem = service.poems.get_by_id(poem_id)
    if not poem:
        raise HTTPException(
            status_code=404,
            detail=f"Poem with ID '{poem_id}' not found"
        )

    # Get translations for this poem
    translations = service.translations.get_by_poem_id(poem_id)

    # Convert to dict format for API response
    return [
        {
            "id": t.id,
            "translator_type": t.translator_type,
            "translator_info": t.translator_info,
            "target_language": t.target_language,
            "quality_rating": t.quality_rating,
            "created_at": t.created_at.isoformat(),
            "translation_count": 1  # Each translation record represents one
        }
        for t in translations
    ]


@router.post("/search", response_model=List[PoemResponse])
async def search_poems(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    search_type: str = Query("title", regex="^(title|poet|text|all)$", description="Search field"),
    service: RepositoryService = Depends(get_repository_service)
):
    """
    Search poems by text content.

    **Request Body:**
    - **query**: Search query string (1-100 chars)
    - **search_type**: Field to search in (title/poet/text/all)

    **Returns:**
    - List of poems matching the search criteria
    """
    # Use the title search functionality from CRUD
    if search_type in ["title", "all"]:
        poems = service.poems.get_multi(title_search=query)
    else:
        # For now, implement simple filtering
        if search_type == "poet":
            poems = service.poems.get_multi(poet_name=query)
        else:  # text search (not implemented yet, return empty)
            poems = []

    return poems