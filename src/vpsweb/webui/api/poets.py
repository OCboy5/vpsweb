"""
VPSWeb Web UI - Poet API Endpoints v0.3.1

API endpoints for poet browsing and discovery operations.
Provides database-driven poet listings, poems by poet, and translation statistics.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.service import RepositoryWebService
from src.vpsweb.repository.models import Poem, Translation
from ..schemas import WebAPIResponse, PaginationInfo

router = APIRouter()


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryWebService:
    """Dependency to get repository service instance"""
    return RepositoryWebService(db)


@router.get("/", response_model=WebAPIResponse)
async def list_poets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum number of records to return"
    ),
    search: Optional[str] = Query(None, description="Search poets by name"),
    sort_by: Optional[str] = Query(
        "name",
        description="Sort by: name, poem_count, translation_count, recent_activity",
    ),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    min_poems: Optional[int] = Query(None, ge=0, description="Minimum number of poems"),
    min_translations: Optional[int] = Query(
        None, ge=0, description="Minimum number of translations"
    ),
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get list of all poets with their statistics and activity metrics.

    **Parameters:**
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **search**: Search poets by name (partial match)
    - **sort_by**: Sort field (name, poem_count, translation_count, recent_activity)
    - **sort_order**: Sort order (asc, desc)
    - **min_poems**: Filter by minimum number of poems
    - **min_translations**: Filter by minimum number of translations

    **Returns:**
    - List of poets with statistics and activity data
    """
    try:
        # Base query with poem and translation counts
        query = (
            service.db.query(
                Poem.poet_name,
                func.count(Poem.id).label("poem_count"),
                func.count(Translation.id).label("translation_count"),
                func.avg(Translation.quality_rating).label("avg_quality_rating"),
                func.max(Translation.created_at).label("last_translation_date"),
                func.max(Poem.created_at).label("last_poem_date"),
                func.group_concat(Poem.source_language, ", ").label("source_languages"),
                func.group_concat(Translation.target_language, ", ").label(
                    "target_languages"
                ),
            )
            .outerjoin(Translation, Poem.id == Translation.poem_id)
            .group_by(Poem.poet_name)
        )

        # Apply filters
        if search:
            query = query.filter(Poem.poet_name.ilike(f"%{search}%"))

        if min_poems is not None:
            query = query.having(func.count(Poem.id) >= min_poems)

        if min_translations is not None:
            query = query.having(func.count(Translation.id) >= min_translations)

        # Apply sorting
        if sort_by == "name":
            order_column = Poem.poet_name
        elif sort_by == "poem_count":
            order_column = func.count(Poem.id)
        elif sort_by == "translation_count":
            order_column = func.count(Translation.id)
        elif sort_by == "recent_activity":
            # SQLite doesn't support greatest() function
            # Use a CASE statement to choose the latest date
            from sqlalchemy import case
            order_column = case(
                (func.max(Translation.created_at) >= func.max(Poem.created_at), func.max(Translation.created_at)),
                else_=func.max(Poem.created_at)
            )
        else:
            order_column = Poem.poet_name

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination
        poets_data = query.offset(skip).limit(limit).all()

        # Format response
        poets = []
        for row in poets_data:
            poet_info = {
                "poet_name": row.poet_name,
                "poem_count": row.poem_count,
                "translation_count": row.translation_count or 0,
                "avg_quality_rating": (
                    float(row.avg_quality_rating) if row.avg_quality_rating else None
                ),
                "last_translation_date": (
                    row.last_translation_date.isoformat()
                    if row.last_translation_date
                    else None
                ),
                "last_poem_date": (
                    row.last_poem_date.isoformat() if row.last_poem_date else None
                ),
                "source_languages": [
                    lang for lang in row.source_languages if lang is not None
                ],
                "target_languages": [
                    lang for lang in row.target_languages if lang is not None
                ],
                "has_recent_activity": (
                    (row.last_translation_date or row.last_poem_date) is not None
                ),
            }
            poets.append(poet_info)

        pagination = PaginationInfo(
            current_page=(skip // limit) + 1,
            total_pages=(total_count + limit - 1) // limit,
            total_items=total_count,
            page_size=limit,
            has_next=(skip + limit) < total_count,
            has_previous=skip > 0,
        )

        return WebAPIResponse(
            success=True, data={"poets": poets, "pagination": pagination.dict()}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch poets: {str(e)}")


@router.get("/{poet_name}/poems", response_model=WebAPIResponse)
async def get_poems_by_poet(
    poet_name: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of records to return"
    ),
    language: Optional[str] = Query(None, description="Filter by source language"),
    has_translations: Optional[bool] = Query(
        None, description="Filter by translation status"
    ),
    sort_by: Optional[str] = Query(
        "title", description="Sort by: title, created_at, translation_count"
    ),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get all poems by a specific poet with translation information.

    **Parameters:**
    - **poet_name**: Name of the poet
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **language**: Filter by source language
    - **has_translations**: Filter by whether poem has translations
    - **sort_by**: Sort field (title, created_at, translation_count)
    - **sort_order**: Sort order (asc, desc)

    **Returns:**
    - List of poems by the specified poet with translation details
    """
    try:
        # Base query for poems by poet
        query = (
            service.db.query(
                Poem,
                func.count(Translation.id).label("translation_count"),
                func.max(Translation.created_at).label("last_translation_date"),
                func.group_concat(Translation.target_language, ", ").label(
                    "target_languages"
                ),
            )
            .outerjoin(Translation, Poem.id == Translation.poem_id)
            .filter(Poem.poet_name == poet_name)
            .group_by(Poem.id)
        )

        # Apply filters
        if language:
            query = query.filter(Poem.source_language == language)

        if has_translations is not None:
            if has_translations:
                query = query.having(func.count(Translation.id) > 0)
            else:
                query = query.having(func.count(Translation.id) == 0)

        # Apply sorting
        if sort_by == "title":
            order_column = Poem.poem_title
        elif sort_by == "created_at":
            order_column = Poem.created_at
        elif sort_by == "translation_count":
            order_column = func.count(Translation.id)
        else:
            order_column = Poem.poem_title

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination
        poems_data = query.offset(skip).limit(limit).all()

        # Format response
        poems = []
        for (
            poem,
            translation_count,
            last_translation_date,
            target_languages,
        ) in poems_data:
            poem_info = {
                "id": poem.id,
                "poet_name": poem.poet_name,
                "poem_title": poem.poem_title,
                "source_language": poem.source_language,
                "original_text": (
                    poem.original_text[:200] + "..."
                    if len(poem.original_text) > 200
                    else poem.original_text
                ),
                "created_at": poem.created_at.isoformat(),
                "updated_at": poem.updated_at.isoformat(),
                "translation_count": translation_count or 0,
                "last_translation_date": (
                    last_translation_date.isoformat() if last_translation_date else None
                ),
                "target_languages": (
                    [
                        lang.strip()
                        for lang in (target_languages or "").split(",")
                        if lang and lang.strip()
                    ]
                    if target_languages
                    else []
                ),
                "has_translations": (translation_count or 0) > 0,
            }
            poems.append(poem_info)

        pagination = PaginationInfo(
            current_page=(skip // limit) + 1,
            total_pages=(total_count + limit - 1) // limit,
            total_items=total_count,
            page_size=limit,
            has_next=(skip + limit) < total_count,
            has_previous=skip > 0,
        )

        return WebAPIResponse(
            success=True,
            data={
                "poet_name": poet_name,
                "poems": poems,
                "pagination": pagination.dict(),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch poems for poet '{poet_name}': {str(e)}",
        )


@router.get("/{poet_name}/translations", response_model=WebAPIResponse)
async def get_translations_by_poet(
    poet_name: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of records to return"
    ),
    target_language: Optional[str] = Query(
        None, description="Filter by target language"
    ),
    translator_type: Optional[str] = Query(
        None, description="Filter by translator type"
    ),
    min_quality: Optional[int] = Query(
        None, ge=1, le=5, description="Minimum quality rating"
    ),
    sort_by: Optional[str] = Query(
        "created_at", description="Sort by: created_at, quality_rating, title"
    ),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get all translations by a specific poet with detailed information.

    **Parameters:**
    - **poet_name**: Name of the poet
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **target_language**: Filter by target language
    - **translator_type**: Filter by translator type (ai, human)
    - **min_quality**: Filter by minimum quality rating (1-5)
    - **sort_by**: Sort field (created_at, quality_rating, title)
    - **sort_order**: Sort order (asc, desc)

    **Returns:**
    - List of translations by the specified poet with detailed information
    """
    try:
        # Base query for translations by poet
        query = (
            service.db.query(Translation, Poem.poem_title, Poem.source_language)
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Poem.poet_name == poet_name)
        )

        # Apply filters
        if target_language:
            query = query.filter(Translation.target_language == target_language)

        if translator_type:
            query = query.filter(Translation.translator_type == translator_type)

        if min_quality is not None:
            query = query.filter(Translation.quality_rating >= min_quality)

        # Apply sorting
        if sort_by == "created_at":
            order_column = Translation.created_at
        elif sort_by == "quality_rating":
            order_column = Translation.quality_rating
        elif sort_by == "title":
            order_column = Poem.poem_title
        else:
            order_column = Translation.created_at

        if sort_order.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination
        translations_data = query.offset(skip).limit(limit).all()

        # Format response
        translations = []
        for translation, poem_title, source_language in translations_data:
            translation_info = {
                "id": translation.id,
                "poem_id": translation.poem_id,
                "poem_title": poem_title,
                "source_language": source_language,
                "target_language": translation.target_language,
                "translator_type": translation.translator_type,
                "translator_info": translation.translator_info,
                "translated_text": (
                    translation.translated_text[:200] + "..."
                    if len(translation.translated_text) > 200
                    else translation.translated_text
                ),
                "quality_rating": translation.quality_rating,
                "created_at": translation.created_at.isoformat(),
                "has_ai_logs": len(translation.ai_logs) > 0,
                "has_human_notes": len(translation.human_notes) > 0,
                "raw_path": translation.raw_path,
            }
            translations.append(translation_info)

        pagination = PaginationInfo(
            current_page=(skip // limit) + 1,
            total_pages=(total_count + limit - 1) // limit,
            total_items=total_count,
            page_size=limit,
            has_next=(skip + limit) < total_count,
            has_previous=skip > 0,
        )

        return WebAPIResponse(
            success=True,
            data={
                "poet_name": poet_name,
                "translations": translations,
                "pagination": pagination.dict(),
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch translations for poet '{poet_name}': {str(e)}",
        )


@router.get("/{poet_name}/stats", response_model=WebAPIResponse)
async def get_poet_statistics(
    poet_name: str,
    service: RepositoryWebService = Depends(get_repository_service),
):
    """
    Get comprehensive statistics for a specific poet.

    **Parameters:**
    - **poet_name**: Name of the poet

    **Returns:**
    - Detailed statistics for the specified poet
    """
    try:
        # Check if poet exists
        poet_exists = service.db.query(Poem).filter(Poem.poet_name == poet_name).first()

        if not poet_exists:
            raise HTTPException(status_code=404, detail=f"Poet '{poet_name}' not found")

        # Get comprehensive statistics
        stats = (
            service.db.query(
                func.count(Poem.id).label("total_poems"),
                func.count(func.distinct(Poem.source_language)).label(
                    "source_languages_count"
                ),
                func.min(Poem.created_at).label("first_poem_date"),
                func.max(Poem.created_at).label("last_poem_date"),
            )
            .filter(Poem.poet_name == poet_name)
            .first()
        )

        translation_stats = (
            service.db.query(
                func.count(Translation.id).label("total_translations"),
                func.count(func.distinct(Translation.target_language)).label(
                    "target_languages_count"
                ),
                func.avg(Translation.quality_rating).label("avg_quality_rating"),
                func.count(func.distinct(Translation.translator_type)).label(
                    "translator_types_count"
                ),
                func.min(Translation.created_at).label("first_translation_date"),
                func.max(Translation.created_at).label("last_translation_date"),
            )
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Poem.poet_name == poet_name)
            .first()
        )

        # Language pair distribution
        language_pairs = (
            service.db.query(
                Poem.source_language,
                Translation.target_language,
                func.count(Translation.id).label("translation_count"),
            )
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Poem.poet_name == poet_name)
            .group_by(Poem.source_language, Translation.target_language)
            .order_by(desc(func.count(Translation.id)))
            .all()
        )

        # Translator type distribution
        translator_distribution = (
            service.db.query(
                Translation.translator_type,
                func.count(Translation.id).label("count"),
                func.avg(Translation.quality_rating).label("avg_quality"),
            )
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Poem.poet_name == poet_name)
            .group_by(Translation.translator_type)
            .all()
        )

        # Format response
        poet_stats = {
            "poet_name": poet_name,
            "poem_statistics": {
                "total_poems": stats.total_poems,
                "source_languages_count": stats.source_languages_count,
                "first_poem_date": (
                    stats.first_poem_date.isoformat() if stats.first_poem_date else None
                ),
                "last_poem_date": (
                    stats.last_poem_date.isoformat() if stats.last_poem_date else None
                ),
            },
            "translation_statistics": {
                "total_translations": translation_stats.total_translations or 0,
                "target_languages_count": translation_stats.target_languages_count or 0,
                "avg_quality_rating": (
                    float(translation_stats.avg_quality_rating)
                    if translation_stats.avg_quality_rating
                    else None
                ),
                "translator_types_count": translation_stats.translator_types_count or 0,
                "first_translation_date": (
                    translation_stats.first_translation_date.isoformat()
                    if translation_stats.first_translation_date
                    else None
                ),
                "last_translation_date": (
                    translation_stats.last_translation_date.isoformat()
                    if translation_stats.last_translation_date
                    else None
                ),
            },
            "language_pairs": [
                {
                    "source_language": pair.source_language,
                    "target_language": pair.target_language,
                    "translation_count": pair.translation_count,
                }
                for pair in language_pairs
            ],
            "translator_distribution": [
                {
                    "translator_type": dist.translator_type,
                    "count": dist.count,
                    "avg_quality": (
                        float(dist.avg_quality) if dist.avg_quality else None
                    ),
                }
                for dist in translator_distribution
            ],
        }

        return WebAPIResponse(success=True, data=poet_stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch statistics for poet '{poet_name}': {str(e)}",
        )
