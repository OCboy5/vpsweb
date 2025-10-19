"""
VPSWeb Repository Server - Streamlined Prototype

Simple FastAPI server for VPSWeb repository system with Jinja2 templating.
This is a streamlined version focused on prototype simplicity.
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .app import create_app
from .database.models import initialize_database
from .api import api_router
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


def create_server() -> FastAPI:
    """
    Create simplified FastAPI server for VPSWeb repository with Jinja2 templating.

    Returns:
        Configured FastAPI application
    """
    # Create app with simplified configuration
    app = create_app(
        title="VPSWeb Repository API",
        debug=True
    )

    # Set up Jinja2 templates
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    # Include API routes
    app.include_router(api_router)

    # Add basic endpoints
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Root endpoint with Jinja2 template."""
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": "VPSWeb Repository System",
            "version": "v0.3.0 Prototype"
        })

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "VPSWeb Repository API",
            "version": "v0.3.0",
            "timestamp": "2025-01-18T00:00:00Z"
        }

    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup."""
        logger.info("Starting VPSWeb Repository server")
        try:
            # Initialize database with default schema
            await initialize_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Continue anyway - the database might already exist

    return app


# Create application instance
app = create_server()


if __name__ == "__main__":
    import uvicorn

    # Run server
    uvicorn.run(
        "src.vpsweb.repository.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )