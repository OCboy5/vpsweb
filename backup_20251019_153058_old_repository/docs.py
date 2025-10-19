"""
API Documentation Configuration for VPSWeb Repository System

This module provides comprehensive API documentation setup using FastAPI's
built-in OpenAPI/Swagger integration with custom configurations.

Features:
- OpenAPI schema configuration
- Custom Swagger UI setup
- API metadata and examples
- Documentation endpoints
- ReDoc configuration
"""

from typing import Dict, Any, Optional, List
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import json


class APIDocumentationConfig:
    """
    Configuration for API documentation.
    """

    def __init__(
        self,
        title: str = "VPSWeb Repository API",
        description: str = None,
        version: str = "1.0.0",
        summary: str = None,
        terms_of_service: str = None,
        contact: Dict[str, str] = None,
        license_info: Dict[str, str] = None,
        servers: List[Dict[str, str]] = None
    ):
        """
        Initialize API documentation configuration.

        Args:
            title: API title
            description: API description (supports Markdown)
            version: API version
            summary: API summary
            terms_of_service: URL to terms of service
            contact: Contact information
            license_info: License information
            servers: Server URLs for API deployment
        """
        self.title = title
        self.description = description or self._get_default_description()
        self.version = version
        self.summary = summary or "Professional AI-powered poetry translation repository API"
        self.terms_of_service = terms_of_service
        self.contact = contact or self._get_default_contact()
        self.license_info = license_info or self._get_default_license()
        self.servers = servers or self._get_default_servers()

    def _get_default_description(self) -> str:
        """Get default API description."""
        return """
# VPSWeb Repository API

The VPSWeb Repository API provides a comprehensive backend system for managing
poetry translations with AI-powered assistance. This API supports the full
lifecycle of poem creation, translation, and management.

## Key Features

- **Poem Management**: Create, read, update, and delete poems with rich metadata
- **Translation Workflow**: AI-assisted translation with human review process
- **Multi-language Support**: Support for English, Chinese, and other languages
- **Repository System**: Version control and history tracking
- **Search & Discovery**: Advanced search capabilities across poems and translations
- **Quality Assurance**: Built-in validation and quality checks

## Authentication

This API uses JWT-based authentication. Include your API token in the
Authorization header:

```
Authorization: Bearer <your-api-token>
```

## Rate Limiting

API requests are limited to 60 requests per minute per IP address.

## Error Handling

All errors return standardized JSON responses with detailed error information.
See the error handling section for more details.

        """.strip()

    def _get_default_contact(self) -> Dict[str, str]:
        """Get default contact information."""
        return {
            "name": "VPSWeb API Team",
            "url": "https://github.com/vpsweb/vpsweb",
            "email": "api@vpsweb.com"
        }

    def _get_default_license(self) -> Dict[str, str]:
        """Get default license information."""
        return {
            "name": "MIT License",
            "identifier": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }

    def _get_default_servers(self) -> List[Dict[str, str]]:
        """Get default server URLs."""
        return [
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.vpsweb.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.vpsweb.com",
                "description": "Staging server"
            }
        ]


class DocumentationExamples:
    """
    Collection of API examples for documentation.
    """

    @staticmethod
    def poem_examples() -> Dict[str, Dict[str, Any]]:
        """Get examples for poem creation/update."""
        return {
            "english_poem": {
                "summary": "English Poem Example",
                "description": "A classic English poem with proper structure",
                "value": {
                    "title": "The Road Not Taken",
                    "poet_name": "Robert Frost",
                    "original_text": "Two roads diverged in a yellow wood,\nAnd sorry I could not travel both\nAnd be one traveler, long I stood\nAnd looked down one as far as I could\nTo where it bent in the undergrowth;",
                    "source_language": "en",
                    "tags": ["nature", "choices", "reflection", "classic"],
                    "publication_year": 1916,
                    "translation_notes": "This poem explores themes of choice and individuality through the metaphor of a fork in the road."
                }
            },
            "chinese_poem": {
                "summary": "Chinese Poem Example",
                "description": "A classical Chinese poem with rich imagery",
                "value": {
                    "title": "靜夜思",
                    "poet_name": "李白",
                    "original_text": "床前明月光，\n疑是地上霜。\n舉頭望明月，\n低頭思故鄉。",
                    "source_language": "zh",
                    "tags": ["homesickness", "moon", "classical", "tang"],
                    "dynasty": "Tang",
                    "translation_notes": "A famous Tang dynasty poem expressing homesickness while viewing moonlight."
                }
            }
        }

    @staticmethod
    def translation_examples() -> Dict[str, Dict[str, Any]]:
        """Get examples for translation creation/update."""
        return {
            "english_to_chinese": {
                "summary": "English to Chinese Translation",
                "description": "Translation of an English poem into Chinese",
                "value": {
                    "translated_text": "兩條路在黃林中分歧，\n我遺憾無法同時遊歷\n作為一位旅人，我久久佇立\n極目眺望其中一條路\n直到它消失在灌木叢中；",
                    "target_language": "zh",
                    "translation_method": "hybrid",
                    "translator_notes": "Translation maintains the contemplative tone and imagery of the original poem. The structure follows Chinese poetic conventions while preserving the core message.",
                    "quality_score": 0.85,
                    "review_status": "approved"
                }
            },
            "chinese_to_english": {
                "summary": "Chinese to English Translation",
                "description": "Translation of a Chinese poem into English",
                "value": {
                    "translated_text": "Before my bed, the moonlight is bright,\nI wonder if it's frost upon the ground.\nI lift my head to gaze at the bright moon,\nThen lower my head and think of home.",
                    "target_language": "en",
                    "translation_method": "reasoning",
                    "translator_notes": "This translation captures the simple yet profound emotion of homesickness in the original poem. The four-line structure is maintained.",
                    "quality_score": 0.92,
                    "review_status": "approved"
                }
            }
        }

    @staticmethod
    def error_examples() -> Dict[str, Dict[str, Any]]:
        """Get examples for error responses."""
        return {
            "validation_error": {
                "summary": "Validation Error Example",
                "description": "Example of a validation error response",
                "value": {
                    "error": True,
                    "error_code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "field": "poem_title",
                        "validation_errors": [
                            {
                                "field": "poem_title",
                                "message": "Poem title is required",
                                "code": "required"
                            }
                        ]
                    },
                    "request_id": "req_123456789",
                    "timestamp": "2025-01-18T10:30:00Z"
                }
            },
            "not_found_error": {
                "summary": "Not Found Error Example",
                "description": "Example of a resource not found error",
                "value": {
                    "error": True,
                    "error_code": "NOT_FOUND",
                    "message": "The poem you're looking for doesn't exist.",
                    "details": {
                        "resource_type": "poem",
                        "resource_id": "poem_123456789"
                    },
                    "request_id": "req_123456790",
                    "timestamp": "2025-01-18T10:30:00Z"
                }
            }
        }


def configure_openapi_schema(
    app: FastAPI,
    config: APIDocumentationConfig,
    custom_tags: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Configure OpenAPI schema for the FastAPI application.

    Args:
        app: FastAPI application instance
        config: API documentation configuration
        custom_tags: Custom OpenAPI tags
    """
    def custom_openapi():
        """Custom OpenAPI schema generator."""
        if app.openapi_schema:
            return app.openapi_schema

        # Get the default OpenAPI schema
        openapi_schema = get_openapi(
            title=config.title,
            version=config.version,
            description=config.description,
            summary=config.summary,
            routes=app.routes,
            servers=config.servers,
            terms_of_service=config.terms_of_service,
            contact=config.contact,
            license_info=config.license_info
        )

        # Add custom tags
        if custom_tags:
            openapi_schema["tags"] = custom_tags

        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your Bearer token"
            }
        }

        # Add global security requirement (commented out for optional auth)
        # openapi_schema["security"] = [{"BearerAuth": []}]

        # Add custom info
        openapi_schema["info"]["x-api-version"] = config.version
        openapi_schema["info"]["x-documentation-url"] = "/docs"
        openapi_schema["info"]["x-support-url"] = "https://github.com/vpsweb/vpsweb/issues"

        # Cache the schema
        app.openapi_schema = openapi_schema
        return openapi_schema

    app.openapi = custom_openapi


def configure_swagger_ui(
    app: FastAPI,
    docs_url: str = "/docs",
    swagger_ui_parameters: Optional[Dict[str, Any]] = None
) -> None:
    """
    Configure Swagger UI with custom parameters.

    Args:
        app: FastAPI application instance
        docs_url: URL for Swagger UI
        swagger_ui_parameters: Custom Swagger UI parameters
    """
    default_parameters = {
        "deepLinking": True,
        "displayOperationId": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "syntaxHighlight": True,
        "syntaxHighlight.theme": "monokai",
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "requestSnippetsEnabled": True,
        "docExpansion": "list",
        "filter": True,
        "showRequestHeaders": True,
        "supportedSubmitMethods": ["get", "post", "put", "delete", "patch"],
    }

    # Merge with custom parameters
    if swagger_ui_parameters:
        default_parameters.update(swagger_ui_parameters)

    # Configure the app with Swagger UI parameters
    app.swagger_ui_parameters = default_parameters

    # Custom docs endpoint
    @app.get(docs_url, include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_ui_parameters=default_parameters
        )


def configure_redoc(
    app: FastAPI,
    redoc_url: str = "/redoc",
    redoc_parameters: Optional[Dict[str, Any]] = None
) -> None:
    """
    Configure ReDoc with custom parameters.

    Args:
        app: FastAPI application instance
        redoc_url: URL for ReDoc
        redoc_parameters: Custom ReDoc parameters
    """
    default_parameters = {
        "hideHostname": True,
        "expandResponses": "200,201",
        "requiredPropsFirst": True,
        "sortPropsAlphabetically": False,
        "downloadSpecification": True,
        "showObjectSchemaExamples": True,
        "noAutoAuth": False,
        "pathInMiddlePanel": False,
        "hideDownloadButton": False,
        "hideLoading": False,
        "nativeScrollbars": False,
        "expandSingleSchemaField": False,
        "theme": {"colors": {"primary": {"main": "#329255"}}}
    }

    # Merge with custom parameters
    if redoc_parameters:
        default_parameters.update(redoc_parameters)

    # Custom ReDoc endpoint
    @app.get(redoc_url, include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc"
        )


def setup_api_documentation(
    app: FastAPI,
    config: Optional[APIDocumentationConfig] = None,
    swagger_ui_config: Optional[Dict[str, Any]] = None,
    redoc_config: Optional[Dict[str, Any]] = None,
    enable_docs: bool = True,
    enable_redoc: bool = True,
    docs_url: str = "/docs",
    redoc_url: str = "/redoc",
    openapi_url: str = "/openapi.json"
) -> None:
    """
    Set up comprehensive API documentation for FastAPI application.

    Args:
        app: FastAPI application instance
        config: Documentation configuration
        swagger_ui_config: Swagger UI configuration
        redoc_config: ReDoc configuration
        enable_docs: Whether to enable Swagger UI
        enable_redoc: Whether to enable ReDoc
        docs_url: URL for Swagger UI
        redoc_url: URL for ReDoc
        openapi_url: URL for OpenAPI schema
    """
    if config is None:
        config = APIDocumentationConfig()

    # Configure OpenAPI URLs
    app.openapi_url = openapi_url if enable_docs or enable_redoc else None

    # Configure documentation URLs
    if enable_docs:
        app.docs_url = docs_url
        configure_swagger_ui(app, docs_url, swagger_ui_config)
    else:
        app.docs_url = None

    if enable_redoc:
        app.redoc_url = redoc_url
        configure_redoc(app, redoc_url, redoc_config)
    else:
        app.redoc_url = None

    # Configure OpenAPI schema
    custom_tags = [
        {
            "name": "Poems",
            "description": "Operations for managing poems and their metadata"
        },
        {
            "name": "Translations",
            "description": "Operations for managing poem translations"
        },
        {
            "name": "AI Logs",
            "description": "Operations for managing AI translation logs"
        },
        {
            "name": "Human Notes",
            "description": "Operations for managing human translator notes"
        },
        {
            "name": "Search",
            "description": "Operations for searching and discovering content"
        },
        {
            "name": "Health",
            "description": "Health check and system status operations"
        }
    ]

    configure_openapi_schema(app, config, custom_tags)

    # Add documentation info endpoint
    @app.get("/api-info", include_in_schema=False, tags=["Health"])
    async def api_info():
        """Get API documentation information."""
        return {
            "title": config.title,
            "version": config.version,
            "description": config.summary,
            "documentation": {
                "swagger_ui": docs_url if enable_docs else None,
                "redoc": redoc_url if enable_redoc else None,
                "openapi_schema": openapi_url if (enable_docs or enable_redoc) else None
            },
            "contact": config.contact,
            "license": config.license_info,
            "servers": config.servers
        }


# Pydantic models for API documentation examples
class PoemCreateExample(BaseModel):
    """Example model for poem creation documentation."""
    title: str = Field(..., example="The Road Not Taken", description="Poem title")
    poet_name: str = Field(..., example="Robert Frost", description="Poet name")
    original_text: str = Field(..., example="Two roads diverged in a yellow wood...", description="Original poem text")
    source_language: str = Field(..., example="en", description="Source language code")
    tags: List[str] = Field(default=[], example=["nature", "choices"], description="Poem tags")
    publication_year: Optional[int] = Field(None, example=1916, description="Publication year")
    translation_notes: Optional[str] = Field(None, example="Notes about translation...", description="Translation notes")


class TranslationCreateExample(BaseModel):
    """Example model for translation creation documentation."""
    translated_text: str = Field(..., example="兩條路在黃林中分歧...", description="Translated text")
    target_language: str = Field(..., example="zh", description="Target language code")
    translation_method: str = Field(..., example="hybrid", description="Translation method")
    translator_notes: Optional[str] = Field(None, example="Translation notes...", description="Translator notes")
    quality_score: Optional[float] = Field(None, example=0.85, description="Translation quality score")
    review_status: Optional[str] = Field(None, example="approved", description="Review status")


# Export utility functions
def get_default_config() -> APIDocumentationConfig:
    """Get default API documentation configuration."""
    return APIDocumentationConfig()


def get_examples() -> DocumentationExamples:
    """Get documentation examples."""
    return DocumentationExamples()