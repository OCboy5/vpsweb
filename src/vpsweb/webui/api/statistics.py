"""
VPSWeb Web UI - Statistics and Comparison API Endpoints v0.3.1

API endpoints for repository statistics, data analysis, and translation comparisons.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.vpsweb.repository.crud import RepositoryService
from src.vpsweb.repository.database import get_db
from src.vpsweb.repository.schemas import ComparisonView, RepositoryStats

router = APIRouter()


def get_repository_service(db: Session = Depends(get_db)) -> RepositoryService:
    """Dependency to get repository service instance"""
    return RepositoryService(db)


@router.get("/overview", response_model=RepositoryStats)
async def get_repository_overview(
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get comprehensive repository statistics and overview.

    **Returns:**
    - Complete repository statistics including poem and translation counts
    """
    try:
        stats = service.get_repository_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate repository statistics: {str(e)}",
        )


@router.get("/translations/comparison/{poem_id}", response_model=ComparisonView)
async def get_translation_comparison(
    poem_id: str,
    target_language: Optional[str] = Query(
        None, description="Filter by target language"
    ),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get comparison view for all translations of a specific poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem to compare translations for

    **Query Parameters:**
    - **target_language**: Optional filter for specific target language

    **Returns:**
    - Comparison view with all translations and their relationships
    """
    # Check if poem exists
    poem = service.poems.get_by_id(poem_id)
    if not poem:
        raise HTTPException(
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    try:
        comparison = service.get_translation_comparison(poem_id, target_language)
        return comparison
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate translation comparison: {str(e)}",
        )


@router.get("/translations/quality-summary/{poem_id}")
async def get_translation_quality_summary(
    poem_id: str, service: RepositoryService = Depends(get_repository_service)
):
    """
    Get quality summary for all translations of a poem.

    **Path Parameters:**
    - **poem_id**: ULID of the poem

    **Returns:**
    - Quality metrics and summary statistics
    """
    # Check if poem exists
    poem = service.poems.get_by_id(poem_id)
    if not poem:
        raise HTTPException(
            status_code=404, detail=f"Poem with ID '{poem_id}' not found"
        )

    try:
        # Get all translations for this poem
        translations = service.translations.get_by_poem_id(poem_id)

        if not translations:
            return {
                "poem_id": poem_id,
                "total_translations": 0,
                "quality_summary": {
                    "average_rating": None,
                    "highest_rated": None,
                    "lowest_rated": None,
                    "distribution": {},
                },
            }

        # Calculate quality metrics
        ratings = [
            t.quality_rating for t in translations if t.quality_rating is not None
        ]

        if ratings:
            average_rating = sum(ratings) / len(ratings)
            highest_rated = max(ratings)
            lowest_rated = min(ratings)

            # Distribution of ratings
            distribution = {}
            for rating in [1, 2, 3, 4, 5]:
                distribution[str(rating)] = ratings.count(rating)
        else:
            average_rating = None
            highest_rated = None
            lowest_rated = None
            distribution = {}

        # Separate AI and human translations
        ai_translations = [t for t in translations if t.translator_type == "AI"]
        human_translations = [t for t in translations if t.translator_type == "Human"]

        return {
            "poem_id": poem_id,
            "total_translations": len(translations),
            "ai_translations": len(ai_translations),
            "human_translations": len(human_translations),
            "target_languages": list(set(t.target_language for t in translations)),
            "quality_summary": {
                "average_rating": average_rating,
                "highest_rated": highest_rated,
                "lowest_rated": lowest_rated,
                "distribution": distribution,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quality summary: {str(e)}",
        )


@router.get("/poems/language-distribution")
async def get_language_distribution(
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get distribution of poems and translations by language.

    **Returns:**
    - Language statistics for poems and translations
    """
    try:
        # Get all poems
        poems = service.poems.get_multi(skip=0, limit=10000)  # Large limit to get all

        # Count poems by source language
        source_language_counts = {}
        for poem in poems:
            lang = poem.source_language
            source_language_counts[lang] = source_language_counts.get(lang, 0) + 1

        # Get all translations to count target languages
        all_translations = []
        for poem in poems:
            translations = service.translations.get_by_poem_id(poem.id)
            all_translations.extend(translations)

        target_language_counts = {}
        for translation in all_translations:
            lang = translation.target_language
            target_language_counts[lang] = target_language_counts.get(lang, 0) + 1

        return {
            "source_languages": {
                "total_poems": len(poems),
                "distribution": source_language_counts,
            },
            "target_languages": {
                "total_translations": len(all_translations),
                "distribution": target_language_counts,
            },
            "language_pairs": [
                {
                    "source": poem.source_language,
                    "target": translation.target_language,
                    "count": 1,
                }
                for poem in poems
                for translation in service.translations.get_by_poem_id(poem.id)
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate language distribution: {str(e)}",
        )


@router.get("/translators/productivity")
async def get_translator_productivity(
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get productivity statistics for translators (both AI and human).

    **Returns:**
    - Translator productivity metrics
    """
    try:
        # Get all poems and their translations
        poems = service.poems.get_multi(skip=0, limit=10000)

        translator_stats = {}

        for poem in poems:
            translations = service.translations.get_by_poem_id(poem.id)
            for translation in translations:
                translator = translation.translator_info
                if translator not in translator_stats:
                    translator_stats[translator] = {
                        "translator_type": translation.translator_type,
                        "total_translations": 0,
                        "target_languages": set(),
                        "average_quality": 0,
                        "quality_ratings": [],
                    }

                translator_stats[translator]["total_translations"] += 1
                translator_stats[translator]["target_languages"].add(
                    translation.target_language
                )

                if translation.quality_rating is not None:
                    translator_stats[translator]["quality_ratings"].append(
                        translation.quality_rating
                    )

        # Calculate average quality for each translator
        for translator, stats in translator_stats.items():
            ratings = stats["quality_ratings"]
            if ratings:
                stats["average_quality"] = sum(ratings) / len(ratings)
            else:
                stats["average_quality"] = None

            # Convert set to list for JSON serialization
            stats["target_languages"] = list(stats["target_languages"])
            # Remove temporary ratings list
            del stats["quality_ratings"]

        # Sort by total translations
        sorted_stats = dict(
            sorted(
                translator_stats.items(),
                key=lambda x: x[1]["total_translations"],
                reverse=True,
            )
        )

        return {
            "total_translators": len(sorted_stats),
            "translator_stats": sorted_stats,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate translator productivity: {str(e)}",
        )


@router.get("/timeline/activity")
async def get_activity_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get repository activity timeline.

    **Query Parameters:**
    - **days**: Number of days to look back (1-365)

    **Returns:**
    - Timeline of repository activity
    """
    try:
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get poems created in the time range
        poems = service.poems.get_multi(skip=0, limit=10000)
        poems_in_range = [
            poem for poem in poems if start_date <= poem.created_at <= end_date
        ]

        # Get translations created in the time range
        translations_in_range = []
        for poem in poems_in_range:
            translations = service.translations.get_by_poem_id(poem.id)
            for translation in translations:
                if start_date <= translation.created_at <= end_date:
                    translations_in_range.append(translation)

        # Group by date
        activity_by_date = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            activity_by_date[date_str] = {
                "poems_created": 0,
                "translations_created": 0,
                "total_activity": 0,
            }
            current_date += timedelta(days=1)

        # Count activity by date
        for poem in poems_in_range:
            date_str = poem.created_at.strftime("%Y-%m-%d")
            if date_str in activity_by_date:
                activity_by_date[date_str]["poems_created"] += 1
                activity_by_date[date_str]["total_activity"] += 1

        for translation in translations_in_range:
            date_str = translation.created_at.strftime("%Y-%m-%d")
            if date_str in activity_by_date:
                activity_by_date[date_str]["translations_created"] += 1
                activity_by_date[date_str]["total_activity"] += 1

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "summary": {
                "total_poems_created": len(poems_in_range),
                "total_translations_created": len(translations_in_range),
                "total_activity": len(poems_in_range) + len(translations_in_range),
                "average_daily_activity": (
                    len(poems_in_range) + len(translations_in_range)
                )
                / days,
            },
            "daily_activity": activity_by_date,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate activity timeline: {str(e)}",
        )


@router.get("/search/metrics")
async def get_search_metrics(
    service: RepositoryService = Depends(get_repository_service),
):
    """
    Get metrics useful for search and filtering.

    **Returns:**
    - Search-related metrics and available filter options
    """
    try:
        # Get all poems and translations
        poems = service.poems.get_multi(skip=0, limit=10000)

        # Extract unique values for filters
        poets = set()
        source_languages = set()
        target_languages = set()
        translator_types = set()

        for poem in poems:
            poets.add(poem.poet_name)
            source_languages.add(poem.source_language)

            translations = service.translations.get_by_poem_id(poem.id)
            for translation in translations:
                target_languages.add(translation.target_language)
                translator_types.add(translation.translator_type)

        return {
            "available_filters": {
                "poets": sorted(list(poets)),
                "source_languages": sorted(list(source_languages)),
                "target_languages": sorted(list(target_languages)),
                "translator_types": sorted(list(translator_types)),
            },
            "collection_stats": {
                "total_poems": len(poems),
                "total_unique_poets": len(poets),
                "total_unique_source_languages": len(source_languages),
                "total_unique_target_languages": len(target_languages),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate search metrics: {str(e)}",
        )
