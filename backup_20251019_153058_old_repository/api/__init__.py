"""
API endpoints for VPSWeb Repository System.

This module provides FastAPI router definitions for all repository API endpoints.
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Import and include sub-routers
# These will be added as we implement the endpoints
# from .poems import router as poems_router
# from .translations import router as translations_router
# from .ai_logs import router as ai_logs_router
# from .human_notes import router as human_notes_router

# Include routers (uncomment as they are created)
# api_router.include_router(poems_router, prefix="/poems", tags=["Poems"])
# api_router.include_router(translations_router, prefix="/translations", tags=["Translations"])
# api_router.include_router(ai_logs_router, prefix="/ai-logs", tags=["AI Logs"])
# api_router.include_router(human_notes_router, prefix="/human-notes", tags=["Human Notes"])

__all__ = ["api_router"]