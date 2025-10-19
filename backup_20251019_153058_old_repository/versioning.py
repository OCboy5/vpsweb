"""
API Versioning Foundation for VPSWeb Repository System

This module provides comprehensive API versioning support including
URL versioning, header versioning, and version negotiation.

Features:
- URL-based versioning (/api/v1/, /api/v2/)
- Header-based versioning (Accept-Version, API-Version)
- Version compatibility and deprecation
- Version routing and middleware
- Version metadata and changelog
"""

from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.routing import APIRoute
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import re
from urllib.parse import parse_qs


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "1.0"
    V1_1 = "1.1"
    V2 = "2.0"


class VersionStatus(str, Enum):
    """Version status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    DEVELOPMENT = "development"


class VersioningMethod(str, Enum):
    """Versioning methods."""
    URL_PATH = "url_path"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    CUSTOM = "custom"


@dataclass
class VersionInfo:
    """Information about an API version."""
    version: APIVersion
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    description: str = ""
    changes: List[str] = None
    breaking_changes: List[str] = None
    migration_guide: Optional[str] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = []
        if self.breaking_changes is None:
            self.breaking_changes = []


class APIVersionManager:
    """
    Manages API versions and version negotiation.
    """

    def __init__(self, default_version: APIVersion = APIVersion.V1):
        """
        Initialize version manager.

        Args:
            default_version: Default API version
        """
        self.default_version = default_version
        self.versions: Dict[APIVersion, VersionInfo] = {}
        self.versioned_apps: Dict[APIVersion, FastAPI] = {}
        self.supported_methods = [
            VersioningMethod.URL_PATH,
            VersioningMethod.HEADER,
            VersioningMethod.QUERY_PARAM
        ]
        self._register_default_versions()

    def _register_default_versions(self) -> None:
        """Register default API versions."""
        # Version 1.0 - Initial release
        self.register_version(VersionInfo(
            version=APIVersion.V1,
            status=VersionStatus.ACTIVE,
            release_date=datetime(2025, 1, 18, tzinfo=timezone.utc),
            description="Initial API release with basic CRUD operations",
            changes=[
                "Initial poem and translation CRUD operations",
                "Basic search and filtering",
                "Authentication and authorization",
                "Error handling and validation"
            ]
        ))

        # Version 1.1 - Enhanced features
        self.register_version(VersionInfo(
            version=APIVersion.V1_1,
            status=VersionStatus.ACTIVE,
            release_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
            description="Enhanced API with advanced features",
            changes=[
                "Advanced search capabilities",
                "Bulk operations support",
                "Enhanced error responses",
                "Rate limiting improvements",
                "Webhook support"
            ]
        ))

        # Version 2.0 - Future release
        self.register_version(VersionInfo(
            version=APIVersion.V2,
            status=VersionStatus.DEVELOPMENT,
            release_date=datetime(2025, 6, 1, tzinfo=timezone.utc),
            description="Next generation API with breaking changes",
            breaking_changes=[
                "Updated response format for consistency",
                "Changed authentication method",
                "Modified endpoint structure",
                "Updated parameter naming"
            ],
            changes=[
                "GraphQL support",
                "Real-time notifications",
                "Advanced analytics",
                "Machine learning integration"
            ],
            migration_guide="/docs/migration/v1-to-v2"
        ))

    def register_version(self, version_info: VersionInfo) -> None:
        """
        Register a new API version.

        Args:
            version_info: Version information
        """
        self.versions[version_info.version] = version_info

    def get_version_info(self, version: APIVersion) -> Optional[VersionInfo]:
        """
        Get information about a specific version.

        Args:
            version: API version

        Returns:
            Version information or None if not found
        """
        return self.versions.get(version)

    def is_version_supported(self, version: APIVersion) -> bool:
        """
        Check if a version is supported.

        Args:
            version: API version to check

        Returns:
            True if version is supported
        """
        if version not in self.versions:
            return False

        version_info = self.versions[version]

        # Check if version is sunset
        if version_info.status == VersionStatus.SUNSET:
            return False

        return True

    def negotiate_version(
        self,
        request: Request,
        methods: List[VersioningMethod] = None
    ) -> APIVersion:
        """
        Negotiate API version from request.

        Args:
            request: HTTP request
            methods: Version negotiation methods to try (in order)

        Returns:
            Negotiated API version
        """
        if methods is None:
            methods = self.supported_methods

        for method in methods:
            version = self._extract_version(request, method)
            if version and self.is_version_supported(version):
                return version

        # Fall back to default version
        return self.default_version

    def _extract_version(self, request: Request, method: VersioningMethod) -> Optional[APIVersion]:
        """
        Extract version from request using specified method.

        Args:
            request: HTTP request
            method: Versioning method

        Returns:
            Extracted version or None
        """
        if method == VersioningMethod.URL_PATH:
            return self._extract_from_url(request)
        elif method == VersioningMethod.HEADER:
            return self._extract_from_header(request)
        elif method == VersioningMethod.QUERY_PARAM:
            return self._extract_from_query(request)
        elif method == VersioningMethod.CUSTOM:
            return self._extract_custom(request)

        return None

    def _extract_from_url(self, request: Request) -> Optional[APIVersion]:
        """Extract version from URL path."""
        path = request.url.path

        # Match /api/v1/, /api/v2/, etc.
        match = re.match(r'/api/v(\d+(?:\.\d+)?)/', path)
        if match:
            version_str = match.group(1)
            try:
                return APIVersion(version_str)
            except ValueError:
                pass

        return None

    def _extract_from_header(self, request: Request) -> Optional[APIVersion]:
        """Extract version from HTTP headers."""
        # Try Accept-Version header first
        accept_version = request.headers.get("Accept-Version")
        if accept_version:
            try:
                return APIVersion(accept_version)
            except ValueError:
                pass

        # Try API-Version header
        api_version = request.headers.get("API-Version")
        if api_version:
            try:
                return APIVersion(api_version)
            except ValueError:
                pass

        return None

    def _extract_from_query(self, request: Request) -> Optional[APIVersion]:
        """Extract version from query parameters."""
        query_params = parse_qs(request.url.query)

        # Check for version parameter
        version_params = query_params.get("version", [])
        if version_params:
            version_str = version_params[0]
            try:
                return APIVersion(version_str)
            except ValueError:
                pass

        return None

    def _extract_custom(self, request: Request) -> Optional[APIVersion]:
        """Extract version using custom logic."""
        # Custom logic can be added here
        # For now, fall back to None
        return None

    def get_active_versions(self) -> List[VersionInfo]:
        """
        Get all active versions.

        Returns:
            List of active version information
        """
        return [
            info for info in self.versions.values()
            if info.status == VersionStatus.ACTIVE
        ]

    def get_deprecated_versions(self) -> List[VersionInfo]:
        """
        Get all deprecated versions.

        Returns:
            List of deprecated version information
        """
        return [
            info for info in self.versions.values()
            if info.status == VersionStatus.DEPRECATED
        ]


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API versioning support.
    """

    def __init__(
        self,
        app,
        version_manager: APIVersionManager,
        negotiation_methods: List[VersioningMethod] = None,
        add_version_headers: bool = True
    ):
        """
        Initialize versioning middleware.

        Args:
            app: FastAPI application
            version_manager: Version manager instance
            negotiation_methods: Version negotiation methods
            add_version_headers: Whether to add version headers to responses
        """
        super().__init__(app)
        self.version_manager = version_manager
        self.negotiation_methods = negotiation_methods or version_manager.supported_methods
        self.add_version_headers = add_version_headers

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with version negotiation.

        Args:
            request: HTTP request
            call_next: Next middleware/endpoint

        Returns:
            HTTP response with version headers
        """
        # Negotiate version
        version = self.version_manager.negotiate_version(
            request,
            self.negotiation_methods
        )

        # Add version to request state
        request.state.api_version = version
        request.state.version_info = self.version_manager.get_version_info(version)

        # Process request
        response = await call_next(request)

        # Add version headers to response
        if self.add_version_headers:
            self._add_version_headers(response, version)

        return response

    def _add_version_headers(self, response: Response, version: APIVersion) -> None:
        """
        Add version headers to response.

        Args:
            response: HTTP response
            version: API version
        """
        response.headers["API-Version"] = version.value
        response.headers["API-Version-Status"] = self.version_manager.get_version_info(version).status.value

        # Add deprecation warnings if needed
        version_info = self.version_manager.get_version_info(version)
        if version_info.status == VersionStatus.DEPRECATED:
            response.headers["Deprecation"] = "true"
            if version_info.sunset_date:
                response.headers["Sunset"] = version_info.sunset_date.isoformat()
            if version_info.migration_guide:
                response.headers["Link"] = f'<{version_info.migration_guide}>; rel="deprecation"'


def create_versioned_app(
    version: APIVersion,
    title: str = None,
    description: str = None,
    **kwargs
) -> FastAPI:
    """
    Create a versioned FastAPI application.

    Args:
        version: API version
        title: App title (will include version)
        description: App description
        **kwargs: Additional FastAPI arguments

    Returns:
        Versioned FastAPI application
    """
    if title is None:
        title = f"VPSWeb Repository API v{version.value}"

    if description is None:
        description = f"VPSWeb Repository API version {version.value}"

    app = FastAPI(
        title=title,
        description=description,
        version=version.value,
        **kwargs
    )

    # Add version info endpoint
    @app.get("/version", tags=["Versioning"])
    async def get_version_info():
        """Get current API version information."""
        return {
            "version": version.value,
            "status": "active",
            "api_title": title,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            }
        }

    return app


def setup_versioning(
    app: FastAPI,
    version_manager: APIVersionManager = None,
    middleware_config: Dict[str, Any] = None
) -> APIVersionManager:
    """
    Set up API versioning for FastAPI application.

    Args:
        app: FastAPI application
        version_manager: Version manager (creates default if None)
        middleware_config: Middleware configuration

    Returns:
        Configured version manager
    """
    if version_manager is None:
        version_manager = APIVersionManager()

    # Configure middleware
    config = {
        "negotiation_methods": [
            VersioningMethod.URL_PATH,
            VersioningMethod.HEADER,
            VersioningMethod.QUERY_PARAM
        ],
        "add_version_headers": True
    }

    if middleware_config:
        config.update(middleware_config)

    app.add_middleware(VersioningMiddleware, version_manager=version_manager, **config)

    # Add comprehensive version information endpoints
    @app.get("/api/versions", tags=["Versioning"])
    async def get_supported_versions():
        """
        Get all supported API versions with detailed information.

        Provides information about active, deprecated, and development versions,
        including release dates, status, and migration guides.
        """
        return {
            "default_version": version_manager.default_version.value,
            "active_versions": [
                {
                    "version": info.version.value,
                    "status": info.status.value,
                    "release_date": info.release_date.isoformat(),
                    "description": info.description,
                    "changes": info.changes
                }
                for info in version_manager.get_active_versions()
            ],
            "deprecated_versions": [
                {
                    "version": info.version.value,
                    "status": info.status.value,
                    "deprecation_date": info.deprecation_date.isoformat() if info.deprecation_date else None,
                    "sunset_date": info.sunset_date.isoformat() if info.sunset_date else None,
                    "migration_guide": info.migration_guide,
                    "breaking_changes": info.breaking_changes
                }
                for info in version_manager.get_deprecated_versions()
            ],
            "development_versions": [
                {
                    "version": info.version.value,
                    "status": info.status.value,
                    "release_date": info.release_date.isoformat(),
                    "description": info.description,
                    "breaking_changes": info.breaking_changes,
                    "changes": info.changes
                }
                for info in version_manager.versions.values()
                if info.status == VersionStatus.DEVELOPMENT
            ]
        }

    @app.get("/api/versions/{version}", tags=["Versioning"])
    async def get_version_details(version: str):
        """Get detailed information about a specific version."""
        try:
            api_version = APIVersion(version)
            version_info = version_manager.get_version_info(api_version)

            if not version_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Version {version} not found"
                )

            return {
                "version": version_info.version.value,
                "status": version_info.status.value,
                "release_date": version_info.release_date.isoformat(),
                "deprecation_date": version_info.deprecation_date.isoformat() if version_info.deprecation_date else None,
                "sunset_date": version_info.sunset_date.isoformat() if version_info.sunset_date else None,
                "description": version_info.description,
                "changes": version_info.changes,
                "breaking_changes": version_info.breaking_changes,
                "migration_guide": version_info.migration_guide,
                "is_supported": version_manager.is_version_supported(api_version)
            }
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid version format: {version}"
            )

    @app.get("/api/docs", tags=["Documentation"])
    async def get_documentation_info():
        """
        Get API documentation information and endpoints.

        Returns information about available documentation formats,
        endpoints, and how to access them.
        """
        return {
            "documentation": {
                "swagger_ui": {
                    "url": "/docs",
                    "description": "Interactive API documentation (Swagger UI)",
                    "format": "HTML"
                },
                "redoc": {
                    "url": "/redoc",
                    "description": "Alternative API documentation (ReDoc)",
                    "format": "HTML"
                },
                "openapi_spec": {
                    "url": "/openapi.json",
                    "description": "OpenAPI specification in JSON format",
                    "format": "JSON"
                }
            },
            "version_info": {
                "endpoint": "/api/versions",
                "description": "Get version information and compatibility"
            },
            "health_check": {
                "endpoint": "/health",
                "description": "API health status and basic information"
            },
            "api_info": {
                "endpoint": "/info",
                "description": "API metadata and available endpoints"
            }
        }

    @app.get("/api/changelog", tags=["Documentation"])
    async def get_changelog():
        """
        Get API changelog information.

        Returns changes, new features, and breaking changes
        across different API versions.
        """
        changelog = {
            "versions": []
        }

        for version_info in sorted(
            version_manager.versions.values(),
            key=lambda x: x.release_date,
            reverse=True
        ):
            version_changelog = {
                "version": version_info.version.value,
                "release_date": version_info.release_date.isoformat(),
                "status": version_info.status.value,
                "description": version_info.description,
                "changes": version_info.changes,
                "breaking_changes": version_info.breaking_changes
            }

            # Add deprecation information
            if version_info.deprecation_date:
                version_changelog["deprecation_date"] = version_info.deprecation_date.isoformat()
                version_changelog["deprecation_reason"] = "Superseded by newer version"

            if version_info.sunset_date:
                version_changelog["sunset_date"] = version_info.sunset_date.isoformat()
                version_changelog["sunset_warning"] = "This version will be discontinued"

            if version_info.migration_guide:
                version_changelog["migration_guide"] = version_info.migration_guide

            changelog["versions"].append(version_changelog)

        return changelog

    @app.get("/api/migration/{from_version}/{to_version}", tags=["Documentation"])
    async def get_migration_guide(from_version: str, to_version: str):
        """
        Get migration guide between two API versions.

        Provides detailed migration instructions including
        breaking changes and recommended migration steps.
        """
        try:
            from_api_version = APIVersion(from_version)
            to_api_version = APIVersion(to_version)

            from_info = version_manager.get_version_info(from_api_version)
            to_info = version_manager.get_version_info(to_api_version)

            if not from_info or not to_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or both versions not found"
                )

            # Collect breaking changes for migration path
            breaking_changes = []
            if from_info.breaking_changes:
                breaking_changes.extend(from_info.breaking_changes)
            if to_info.breaking_changes:
                breaking_changes.extend(to_info.breaking_changes)

            return {
                "migration": {
                    "from_version": from_version,
                    "to_version": to_version,
                    "from_status": from_info.status.value,
                    "to_status": to_info.status.value
                },
                "breaking_changes": breaking_changes,
                "recommended_steps": [
                    "Review breaking changes section",
                    "Update API client to handle new response formats",
                    "Test with development environment first",
                    "Plan migration during maintenance window"
                ],
                "compatibility": {
                    "url_versioning": "Update URL paths from /api/v{from}/ to /api/v{to}/",
                    "header_versioning": "Change API-Version header from {from} to {to}",
                    "query_versioning": "Update version parameter from {from} to {to}"
                },
                "migration_guide": to_info.migration_guide,
                "support": {
                    "documentation": "/api/docs",
                    "versions": "/api/versions",
                    "health_check": "/health"
                }
            }

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid version format. Use format like '1.0', '1.1', '2.0'"
            )

    return version_manager


# Decorator for version-specific endpoints
def versioned(*versions: APIVersion):
    """
    Decorator to make endpoint available only for specific versions.

    Args:
        versions: Supported API versions
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Try to get from kwargs
                request = kwargs.get('request')

            if request:
                current_version = getattr(request.state, 'api_version', None)
                if current_version not in versions:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Endpoint not available in API version {current_version}"
                    )

            return await func(*args, **kwargs)

        # Add version information to function
        wrapper.__versioned__ = True
        wrapper.__supported_versions__ = versions
        return wrapper

    return decorator


# Global version manager instance
_version_manager = APIVersionManager()


def get_version_manager() -> APIVersionManager:
    """Get the global version manager instance."""
    return _version_manager