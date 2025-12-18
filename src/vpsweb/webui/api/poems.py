"""
VPSWeb Web UI - Poem API Endpoints v0.3.1

API endpoints for poem management operations with comprehensive CRUD functionality.
"""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.models import Poem, Translation
from src.vpsweb.repository.schemas import (PoemCreate, PoemResponse,
                                           PoemSelectionUpdate, PoemUpdate)
from vpsweb.utils.logger import get_logger

from ..schemas import (PaginatedPoemResponse, PaginationInfo,
                       PoemFilterOptions, PoemFormCreate,
                       PoemTranslationWithWorkflow, WebAPIResponse)
from ..services.interfaces import IBBRServiceV2

router = APIRouter()
logger = get_logger(__name__)


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


def get_bbr_service(db: Session = Depends(get_db)) -> IBBRServiceV2:
    """Dependency to get BBR service instance"""
    from vpsweb.webui.container import container

    return container.resolve(IBBRServiceV2)


@router.get("/", response_model=PaginatedPoemResponse)
async def list_poems(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of items per page (default: 20, max: 100)",
    ),
    poet_name: Optional[str] = Query(None, description="Filter by poet name"),
    language: Optional[str] = Query(None, description="Filter by source language"),
    title_search: Optional[str] = Query(None, description="Search in poem title"),
    selected: Optional[bool] = Query(None, description="Filter by selection status"),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get list of poems with optional filtering and pagination.

    **Parameters:**
    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (1-100, default: 20)
    - **poet_name**: Filter poems by poet name
    - **language**: Filter poems by source language
    - **title_search**: Search poems by title (partial match)
    - **selected**: Filter poems by selection status (true/false)

    **Returns:**
    - Paginated list of poems with pagination metadata
    """
    # Convert page-based pagination to skip/limit
    skip = (page - 1) * page_size

    # Get total count for pagination
    total_count = service.poems.count(
        poet_name=poet_name,
        language=language,
        title_search=title_search,
        selected=selected,
    )

    # Get poems for current page
    poems = service.poems.get_multi(
        skip=skip,
        limit=page_size,
        poet_name=poet_name,
        language=language,
        title_search=title_search,
        selected=selected,
    )

    # Build response data
    response_data = []
    poem_ids = [poem.id for poem in poems]

    # Batch query for all selected fields to avoid N+1 problem
    selected_mapping = {}
    if poem_ids:
        from sqlalchemy import text

        placeholders = ",".join([f":id_{i}" for i in range(len(poem_ids))])
        params = {f"id_{i}": poem_id for i, poem_id in enumerate(poem_ids)}
        selected_results = service.db.execute(
            text(f"SELECT id, selected FROM poems WHERE id IN ({placeholders})"),
            params,
        ).fetchall()

        # Create mapping of poem_id -> selected_value
        for poem_id, selected_val in selected_results:
            if isinstance(selected_val, str):
                selected_mapping[poem_id] = selected_val.lower() in (
                    "true",
                    "1",
                    "t",
                    "yes",
                )
            else:
                selected_mapping[poem_id] = (
                    bool(selected_val) if selected_val is not None else False
                )

    # Build response data for each poem with individual translation counts
    for poem in poems:
        # Calculate translation counts for this specific poem using direct SQL queries
        ai_translation_count = (
            service.db.execute(
                select(func.count(Translation.id)).where(
                    Translation.poem_id == poem.id,
                    Translation.translator_type == "ai",
                )
            ).scalar()
            or 0
        )

        human_translation_count = (
            service.db.execute(
                select(func.count(Translation.id)).where(
                    Translation.poem_id == poem.id,
                    Translation.translator_type == "human",
                )
            ).scalar()
            or 0
        )

        selected_value = selected_mapping.get(poem.id, False)
        poem_dict = {
            "id": poem.id,
            "poet_name": poem.poet_name,
            "poem_title": poem.poem_title,
            "source_language": poem.source_language,
            "original_text": poem.original_text,
            "metadata_json": poem.metadata_json,
            "created_at": poem.created_at,
            "updated_at": poem.updated_at,
            "translation_count": poem.translation_count or 0,
            "ai_translation_count": ai_translation_count,
            "human_translation_count": human_translation_count,
            "selected": selected_value,
        }
        response_data.append(poem_dict)

    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1

    # Build pagination URLs
    base_query_params = []
    if poet_name:
        base_query_params.append(f"poet_name={poet_name}")
    if language:
        base_query_params.append(f"language={language}")
    if title_search:
        base_query_params.append(f"title_search={title_search}")
    if page_size != 20:  # Include page_size if not default
        base_query_params.append(f"page_size={page_size}")

    "&".join(base_query_params) if base_query_params else ""

    next_page_url = None
    if has_next:
        next_params = base_query_params + [f"page={page + 1}"]
        next_page_url = f"/api/v1/poems/?{'&'.join(next_params)}"

    previous_page_url = None
    if has_previous:
        prev_params = base_query_params + [f"page={page - 1}"]
        previous_page_url = f"/api/v1/poems/?{'&'.join(prev_params)}"

    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_items=total_count,
        page_size=page_size,
        has_next=has_next,
        has_previous=has_previous,
        next_page_url=next_page_url,
        previous_page_url=previous_page_url,
    )

    return PaginatedPoemResponse(
        poems=response_data,
        pagination=pagination,
    )


@router.post("/", response_model=PoemResponse)
async def create_poem(
    poem_data: PoemFormCreate,
    service: RepositoryService = Depends(get_repository_service),
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
        metadata_json=poem_data.metadata,
    )

    try:
        poem = service.poems.create(poem_create)
        return poem
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create poem: {str(e)}")


@router.get("/filter-options", response_model=PoemFilterOptions)
async def get_filter_options(
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get global filter options for poems (all poets and languages in the database).

    **Returns:**
    - List of all available poets and languages for filtering
    """
    try:
        # Get all unique poets from database
        poets_query = select(Poem.poet_name).distinct().order_by(Poem.poet_name)
        poets_result = service.db.execute(poets_query).scalars().all()
        poets = [poet for poet in poets_result if poet]  # Filter out None values

        # Get all unique languages from database
        languages_query = (
            select(Poem.source_language).distinct().order_by(Poem.source_language)
        )
        languages_result = service.db.execute(languages_query).scalars().all()
        languages = [
            lang for lang in languages_result if lang
        ]  # Filter out None values

        return PoemFilterOptions(
            poets=poets,
            languages=languages,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get filter options: {str(e)}"
        )


@router.get("/recent-activity", response_model=WebAPIResponse)
async def get_recent_activity(
    limit: int = Query(
        6,
        ge=1,
        le=20,
        description="Maximum number of poems to return (default: 6, max: 20)",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to look back for activity (default: 30, max: 365)",
    ),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get poems with recent activity (new poems, translations, or BBRs).

    This endpoint returns poems that have had recent activity within the specified
    time period, including:
    - Newly added poems
    - New translations for existing poems
    - New Background Briefing Reports (BBRs)

    The results are ordered by the most recent activity across all these types.
    """
    try:
        # Use the PoemServiceV2 to get recent activity
        from vpsweb.webui.container import container

        from ..services.interfaces import IPoemServiceV2

        poem_service = container.resolve(IPoemServiceV2)

        # Get recent activity data
        result = await poem_service.get_recent_activity(limit=limit, days=days)

        return WebAPIResponse(
            success=True,
            message="Recent activity retrieved successfully",
            data=result,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get recent activity: {str(e)}"
        )


@router.get("/{poem_id}", response_model=PoemResponse)
async def get_poem(
    poem_id: str,
    service: RepositoryService = Depends(get_repository_service),
    bbr_service: IBBRServiceV2 = Depends(get_bbr_service),
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
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    # Check if BBR exists
    has_bbr = bbr_service.has_bbr(poem_id)

    # Fix SQLAlchemy boolean mapping issue by getting fresh value directly from database
    from sqlalchemy import text

    result = service.db.execute(
        text("SELECT selected FROM poems WHERE id = :poem_id"),
        {"poem_id": poem_id},
    )
    direct_db_value = result.scalar()

    # Convert the string value from SQLite to proper boolean
    if direct_db_value is not None:
        # Handle SQLite's string boolean representation
        if isinstance(direct_db_value, str):
            selected_value = direct_db_value.lower() in (
                "true",
                "1",
                "t",
                "yes",
            )
        else:
            selected_value = bool(direct_db_value)
    else:
        selected_value = False

    # Convert to PoemResponse model with proper selected field handling
    return PoemResponse(
        id=poem.id,
        poet_name=poem.poet_name,
        poem_title=poem.poem_title,
        source_language=poem.source_language,
        original_text=poem.original_text,
        metadata_json=poem.metadata_json,
        selected=selected_value,
        created_at=poem.created_at,
        updated_at=poem.updated_at,
        translation_count=poem.translation_count,
        ai_translation_count=poem.ai_translation_count,
        human_translation_count=poem.human_translation_count,
        has_bbr=has_bbr,
    )


@router.put("/{poem_id}", response_model=PoemResponse)
async def update_poem(
    poem_id: str,
    poem_data: PoemFormCreate,
    service: RepositoryService = Depends(get_repository_service),
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
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    # Convert form schema to update schema
    poem_update = PoemUpdate(
        poet_name=poem_data.poet_name,
        poem_title=poem_data.poem_title,
        source_language=poem_data.source_language,
        original_text=poem_data.original_text,
        metadata_json=poem_data.metadata,
    )

    try:
        updated_poem = service.poems.update(poem_id, poem_update)
        return updated_poem
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update poem: {str(e)}")


@router.patch("/{poem_id}/selected", response_model=PoemResponse)
async def toggle_poem_selection(
    poem_id: str,
    selection_update: PoemSelectionUpdate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Toggle poem selection status.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to update

    **Request Body:**
    - **selected**: Boolean indicating selection status

    **Returns:**
    - Updated poem object
    """
    # Check if poem exists
    existing_poem = service.poems.get_by_id(poem_id)
    if not existing_poem:
        raise HTTPException(
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    try:
        updated_poem = service.poems.update_selection(
            poem_id, selection_update.selected
        )
        if not updated_poem:
            raise HTTPException(
                status_code=500,
                detail="Failed to update poem selection status",
            )

        return PoemResponse(
            id=updated_poem.id,
            poet_name=updated_poem.poet_name,
            poem_title=updated_poem.poem_title,
            source_language=updated_poem.source_language,
            original_text=updated_poem.original_text,
            metadata_json=updated_poem.metadata_json,
            selected=updated_poem.selected,
            created_at=updated_poem.created_at,
            updated_at=updated_poem.updated_at,
            translation_count=updated_poem.translation_count,
            ai_translation_count=updated_poem.ai_translation_count,
            human_translation_count=updated_poem.human_translation_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update poem selection: {str(e)}",
        )


@router.delete("/{poem_id}", response_model=WebAPIResponse)
async def delete_poem(
    poem_id: str, service: RepositoryService = Depends(get_repository_service)
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
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    try:
        service.poems.delete(poem_id)
        return WebAPIResponse(
            success=True,
            message=f"Poem '{existing_poem.poem_title}' deleted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete poem: {str(e)}")


@router.get("/{poem_id}/translations", response_model=List[dict])
async def get_poem_translations(
    poem_id: str, service: RepositoryService = Depends(get_repository_service)
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
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    # Get translations for this poem
    translations = service.translations.get_by_poem(poem_id)

    # Convert to dict format for API response with poem fallback data
    result = []
    for t in translations:
        # Load workflow_mode for AI translations
        workflow_mode = None
        if t.translator_type == "ai":
            ai_logs = service.ai_logs.get_by_translation(t.id)
            workflow_mode = ai_logs[0].workflow_mode if ai_logs else None

        result.append(
            {
                "id": t.id,
                "translator_type": t.translator_type,
                "translator_info": t.translator_info,
                "target_language": t.target_language,
                "translated_text": t.translated_text,
                "translated_poem_title": t.translated_poem_title,
                "translated_poet_name": t.translated_poet_name,
                "poem_title": poem.poem_title,  # Add original poem title for fallback
                "poet_name": poem.poet_name,  # Add original poet name for fallback
                "quality_rating": t.quality_rating,
                "created_at": t.created_at.isoformat(),
                "translation_count": 1,  # Each translation record represents one
                "workflow_mode": workflow_mode,  # Add workflow mode
            }
        )

    return result


@router.post("/search", response_model=List[PoemResponse])
async def search_poems(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    search_type: str = Query(
        "title", regex="^(title|poet|text|all)$", description="Search field"
    ),
    service: RepositoryService = Depends(get_repository_service),
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


@router.get(
    "/{poem_id}/translations-with-workflows",
    response_model=List[PoemTranslationWithWorkflow],
)
async def get_poem_translations_with_workflows(
    poem_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get all translations for a poem with workflow step indicators.

    This endpoint provides translation information along with whether each translation
    has detailed workflow steps available for viewing in the Translation Notes page.

    **Path Parameters:**
    - **poem_id**: ULID of the poem

    **Returns:**
    - List of translations with workflow step information
    - Includes performance summary for AI translations
    - Indicates which translations have detailed notes available
    """
    # Check if poem exists
    poem = service.poems.get_by_id(poem_id)
    if not poem:
        raise HTTPException(
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    # Get translations for this poem
    translations = service.translations.get_by_poem(poem_id)

    # Build response with workflow information
    result = []
    for translation in translations:
        # Get workflow step information
        has_workflow_steps = translation.has_workflow_steps
        workflow_step_count = translation.workflow_step_count

        # Performance summary for AI translations
        performance_summary = None
        if has_workflow_steps and translation.translator_type.lower() == "ai":
            performance_summary = {
                "total_tokens": translation.total_tokens_used,
                "total_cost": translation.total_cost,
                "total_duration": translation.total_duration,
                "steps_available": workflow_step_count,
            }

        result.append(
            PoemTranslationWithWorkflow(
                translation_id=translation.id,
                translator_info=translation.translator_info,
                target_language=translation.target_language,
                translation_type=translation.translator_type.lower(),
                has_workflow_steps=has_workflow_steps,
                workflow_step_count=workflow_step_count,
                created_at=translation.created_at,
                quality_rating=translation.quality_rating,
                performance_summary=performance_summary,
            )
        )

    return result


# BBR Endpoints - Background Briefing Report Management


@router.post("/{poem_id}/bbr/generate", response_model=WebAPIResponse)
async def generate_bbr(
    poem_id: str,
    background_tasks: BackgroundTasks,
    bbr_service: IBBRServiceV2 = Depends(get_bbr_service),
    repository_service: RepositoryService = Depends(get_repository_service),
):
    """
    Generate a Background Briefing Report for a poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to generate BBR for

    **Returns:**
    - Success/failure status with task information for async generation
    """
    try:
        # Verify poem exists
        poem = repository_service.poems.get_by_id(poem_id)
        if not poem:
            raise HTTPException(
                status_code=404, detail=f"Poem with ID '{poem_id}' not found"
            )

        # Check if BBR already exists
        if bbr_service.has_bbr(poem_id):
            # Return existing BBR instead of generating new one
            existing_bbr = await bbr_service.get_bbr(poem_id)
            return WebAPIResponse(
                success=True,
                message="Background Briefing Report already exists",
                data={"bbr": existing_bbr, "regenerated": False},
            )

        # Generate BBR asynchronously
        result = await bbr_service.generate_bbr(poem_id, background_tasks)

        return WebAPIResponse(
            success=True,
            message="Background Briefing Report generation started",
            data=result,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BBR generation failed: {str(e)}")


@router.get("/{poem_id}/bbr", response_model=WebAPIResponse)
async def get_bbr(
    poem_id: str,
    bbr_service: IBBRServiceV2 = Depends(get_bbr_service),
    repository_service: RepositoryService = Depends(get_repository_service),
):
    """
    Get the Background Briefing Report for a poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to get BBR for

    **Returns:**
    - BBR data if it exists, or status indicating no BBR found
    """
    try:
        # Verify poem exists
        poem = repository_service.poems.get_by_id(poem_id)
        if not poem:
            raise HTTPException(
                status_code=404, detail=f"Poem with ID '{poem_id}' not found"
            )

        # Get BBR
        bbr = await bbr_service.get_bbr(poem_id)
        if bbr:
            return WebAPIResponse(
                success=True,
                message="Background Briefing Report found",
                data={"bbr": bbr, "has_bbr": True},
            )
        else:
            return WebAPIResponse(
                success=True,
                message="No Background Briefing Report found",
                data={"has_bbr": False, "poem_id": poem_id},
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get BBR: {str(e)}")


@router.delete("/{poem_id}/bbr", response_model=WebAPIResponse)
async def delete_bbr(
    poem_id: str,
    bbr_service: IBBRServiceV2 = Depends(get_bbr_service),
    repository_service: RepositoryService = Depends(get_repository_service),
):
    """
    Delete the Background Briefing Report for a poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to delete BBR for

    **Returns:**
    - Success/failure status
    """
    try:
        # Verify poem exists
        poem = repository_service.poems.get_by_id(poem_id)
        if not poem:
            raise HTTPException(
                status_code=404, detail=f"Poem with ID '{poem_id}' not found"
            )

        # Check if BBR exists
        if not bbr_service.has_bbr(poem_id):
            return WebAPIResponse(
                success=True,
                message="No Background Briefing Report to delete",
                data={"deleted": False},
            )

        # Delete BBR
        deleted = await bbr_service.delete_bbr(poem_id)
        if deleted:
            return WebAPIResponse(
                success=True,
                message="Background Briefing Report deleted successfully",
                data={"deleted": True},
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete Background Briefing Report",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete BBR: {str(e)}")
