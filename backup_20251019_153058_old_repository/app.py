"""
VPSWeb Repository Application Factory - Streamlined Prototype

This module provides a simplified application factory function for creating
and configuring the FastAPI application with basic security and validation.
"""

from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .security import setup_security_middleware
from ..utils.logger import get_structured_logger


def create_repository_app(
    title: str = "VPSWeb Repository API",
    description: str = "VPSWeb Repository System API",
    version: str = "1.0.0",
    debug: bool = False,
    security_config: Optional[Dict[str, Any]] = None,
    cors_config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    Create and configure a FastAPI application for the VPSWeb repository system.

    Args:
        title: Application title
        description: Application description
        version: Application version
        debug: Whether to enable debug mode
        security_config: Security middleware configuration
        cors_config: CORS configuration

    Returns:
        Configured FastAPI application
    """
    logger = get_structured_logger()

    # Create FastAPI application
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        debug=debug,
        docs_url="/docs" if debug else None,
        redoc_url="/redoc" if debug else None,
    )

    # Set up global exception handlers
    setup_exception_handlers(app)

    # Set up security middleware
    security_config = security_config or {}
    setup_security_middleware(
        app,
        enable_cors=True,
        enable_compression=True,
        enable_rate_limiting=not debug,  # Disable rate limiting in debug
        enable_request_logging=True,
        custom_config={
            **security_config,
            **(cors_config or {})
        }
    )

    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info(
            "VPSWeb Repository API starting up",
            title=title,
            version=version,
            debug=debug
        )

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(
            "VPSWeb Repository API shutting down",
            title=title,
            version=version
        )

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": title,
            "version": version,
            "timestamp": "2025-01-18T00:00:00Z"  # Placeholder
        }

    # Add API info endpoint
    @app.get("/info")
    async def api_info():
        """API information endpoint."""
        return {
            "title": title,
            "description": description,
            "version": version,
            "debug": debug,
            "endpoints": {
                "health": "/health",
                "info": "/info",
                "docs": "/docs" if debug else "disabled"
            }
        }

    logger.info(
        "VPSWeb Repository API created",
        title=title,
        version=version,
        debug_mode=debug
    )

    return app


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up simplified global exception handlers for the application.

    Args:
        app: FastAPI application instance
    """
    logger = get_structured_logger()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle FastAPI validation exceptions."""
        logger.warning(
            "Request validation failed",
            path=request.url.path,
            errors=exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation failed",
                "message": "Invalid input data",
                "details": exc.errors()
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        logger.warning(
            "HTTP exception",
            path=request.url.path,
            status_code=exc.status_code,
            detail=exc.detail
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP error",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }
        )


# Default application configuration
DEFAULT_SECURITY_CONFIG = {
    "hsts_include_subdomains": True,
    "rate_limit_per_minute": 60,
    "rate_limit_burst": 10,
    "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
    "cors_credentials": True,
    "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "cors_headers": ["*"],
    "compression_min_size": 1000,
    "log_request_body": False,
    "log_max_body_size": 1000,
}


def create_app(
    title: str = "VPSWeb Repository API",
    debug: bool = False,
    custom_security_config: Optional[Dict[str, Any]] = None
) -> FastAPI:
    """
    Create a repository app with default configuration.

    Args:
        title: Application title
        debug: Whether to enable debug mode
        custom_security_config: Custom security configuration

    Returns:
        Configured FastAPI application
    """
    security_config = {**DEFAULT_SECURITY_CONFIG}
    if custom_security_config:
        security_config.update(custom_security_config)

    return create_repository_app(
        title=title,
        debug=debug,
        security_config=security_config
    )