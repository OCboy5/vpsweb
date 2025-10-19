"""
OpenAPI and Swagger UI Configuration for VPSWeb Repository System.

This module provides comprehensive OpenAPI configuration, Swagger UI
customization, and documentation generation for the API.

Features:
- Custom OpenAPI schema configuration
- Swagger UI customization with themes and settings
- ReDoc configuration
- Multiple documentation formats
- API examples and documentation enhancements
- Custom documentation endpoints
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel


class OpenAPIConfig:
    """
    Configuration for OpenAPI specification generation.

    Provides settings for customizing the OpenAPI schema,
    including metadata, security, and server configurations.
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
        servers: List[Dict[str, str]] = None,
        openapi_version: str = "3.1.0",
        tags: List[Dict[str, str]] = None
    ):
        """
        Initialize OpenAPI configuration.

        Args:
            title: API title
            description: API description (supports Markdown)
            version: API version
            summary: Short API summary
            terms_of_service: URL to terms of service
            contact: Contact information
            license_info: License information
            servers: Server configurations
            openapi_version: OpenAPI specification version
            tags: API tags for grouping endpoints
        """
        self.title = title
        self.description = description or self._get_default_description()
        self.version = version
        self.summary = summary or "Professional AI-powered poetry translation platform API"
        self.terms_of_service = terms_of_service
        self.contact = contact or self._get_default_contact()
        self.license_info = license_info or self._get_default_license()
        self.servers = servers or self._get_default_servers()
        self.openapi_version = openapi_version
        self.tags = tags or self._get_default_tags()

    def _get_default_description(self) -> str:
        """Get default API description."""
        return """
# VPSWeb Repository API

VPSWeb Repository System provides a comprehensive API for managing poetry translations,
AI processing logs, and human annotations. This API supports the complete workflow
from poem creation to translation management and quality assessment.

## Features

- **Poem Management**: Create, read, update, and delete poems with metadata
- **Translation Management**: Handle translation versions and quality scores
- **AI Processing**: Track AI translation workflows and performance metrics
- **Human Annotations**: Manage editorial notes and cultural context
- **Search & Discovery**: Advanced search across poems and translations
- **Version Control**: API versioning with backward compatibility

## Authentication

Currently running in localhost-only mode for v0.3. Authentication will be
added in future releases.

## Rate Limiting

Basic rate limiting is implemented to ensure fair usage. Check response
headers for rate limit information.

## Error Handling

The API uses standard HTTP status codes and provides detailed error
responses in JSON format.

## Getting Started

1. Check the `/health` endpoint for API status
2. Explore `/api/versions` for available API versions
3. Visit `/docs` for interactive API documentation
4. Use `/api/poems` to start exploring poems

## Support

For support and questions, refer to the contact information in this
specification or check the API documentation endpoints.
        """.strip()

    def _get_default_contact(self) -> Dict[str, str]:
        """Get default contact information."""
        return {
            "name": "VPSWeb Development Team",
            "url": "https://github.com/vpsweb/vpsweb",
            "email": "support@vpsweb.dev"
        }

    def _get_default_license(self) -> Dict[str, str]:
        """Get default license information."""
        return {
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }

    def _get_default_servers(self) -> List[Dict[str, str]]:
        """Get default server configurations."""
        return [
            {
                "url": "http://localhost:8000",
                "description": "Development server (localhost only)"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "API v1 endpoint"
            }
        ]

    def _get_default_tags(self) -> List[Dict[str, str]]:
        """Get default API tags."""
        return [
            {
                "name": "Poems",
                "description": "Poem management operations"
            },
            {
                "name": "Translations",
                "description": "Translation management and versioning"
            },
            {
                "name": "AI Logs",
                "description": "AI processing workflow logs"
            },
            {
                "name": "Human Notes",
                "description": "Human annotations and editorial notes"
            },
            {
                "name": "Search",
                "description": "Search and query operations"
            },
            {
                "name": "System",
                "description": "System information and health checks"
            },
            {
                "name": "Versioning",
                "description": "API versioning information"
            },
            {
                "name": "Documentation",
                "description": "API documentation and guides"
            }
        ]


class SwaggerUIConfig:
    """
    Configuration for Swagger UI customization.

    Provides settings for customizing the Swagger UI appearance,
    functionality, and behavior.
    """

    def __init__(
        self,
        deep_linking: bool = True,
        display_operation_id: bool = False,
        display_request_duration: bool = True,
        doc_expansion: str = "none",
        default_models_expand_depth: int = 1,
        default_model_expand_depth: int = 1,
        show_extensions: bool = True,
        show_common_extensions: bool = True,
        try_it_out_enabled: bool = True,
        request_snippets_enabled: bool = True,
        oauth2_redirect_url: Optional[str] = None,
        persist_authorization: bool = False,
        syntax_highlight_theme: str = "arta",
        filter: bool = True,
        supported_submit_methods: List[str] = None
    ):
        """
        Initialize Swagger UI configuration.

        Args:
            deep_linking: Enable deep linking to operations and tags
            display_operation_id: Display operation IDs
            display_request_duration: Show request duration
            doc_expansion: Default expansion mode for tags/operations
            default_models_expand_depth: Default expand depth for models
            default_model_expand_depth: Default expand depth for model
            show_extensions: Show vendor extensions
            show_common_extensions: Show common extensions
            try_it_out_enabled: Enable "Try it out" functionality
            request_snippets_enabled: Enable request code snippets
            oauth2_redirect_url: OAuth2 redirect URL
            persist_authorization: Persist authorization
            syntax_highlight_theme: Syntax highlighting theme
            filter: Enable filtering
            supported_submit_methods: Supported HTTP methods
        """
        self.deep_linking = deep_linking
        self.display_operation_id = display_operation_id
        self.display_request_duration = display_request_duration
        self.doc_expansion = doc_expansion
        self.default_models_expand_depth = default_models_expand_depth
        self.default_model_expand_depth = default_model_expand_depth
        self.show_extensions = show_extensions
        self.show_common_extensions = show_common_extensions
        self.try_it_out_enabled = try_it_out_enabled
        self.request_snippets_enabled = request_snippets_enabled
        self.oauth2_redirect_url = oauth2_redirect_url
        self.persist_authorization = persist_authorization
        self.syntax_highlight_theme = syntax_highlight_theme
        self.filter = filter
        self.supported_submit_methods = supported_submit_methods or [
            "get", "post", "put", "delete", "patch"
        ]

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get Swagger UI parameters as dictionary.

        Returns:
            Swagger UI parameters dictionary
        """
        return {
            "deepLinking": self.deep_linking,
            "displayOperationId": self.display_operation_id,
            "displayRequestDuration": self.display_request_duration,
            "docExpansion": self.doc_expansion,
            "defaultModelsExpandDepth": self.default_models_expand_depth,
            "defaultModelExpandDepth": self.default_model_expand_depth,
            "showExtensions": self.show_extensions,
            "showCommonExtensions": self.show_common_extensions,
            "tryItOutEnabled": self.try_it_out_enabled,
            "requestSnippetsEnabled": self.request_snippets_enabled,
            "persistAuthorization": self.persist_authorization,
            "syntaxHighlight.theme": self.syntax_highlight_theme,
            "filter": self.filter,
            "supportedSubmitMethods": self.supported_submit_methods
        }


class ReDocConfig:
    """
    Configuration for ReDoc customization.

    Provides settings for customizing the ReDoc appearance
    and functionality.
    """

    def __init__(
        self,
        theme: Dict[str, Any] = None,
        hide_download_button: bool = False,
        hide_hostname: bool = False,
        no_auto_auth: bool = False,
        scroll_y_offset: int = 0,
        required_props_first: bool = True,
        sort_props_alphabetically: bool = True,
        sort_enum_values_alphabetically: bool = True,
        expand_single_schema_field: bool = True
    ):
        """
        Initialize ReDoc configuration.

        Args:
            theme: ReDoc theme configuration
            hide_download_button: Hide download button
            hide_hostname: Hide hostname in documentation
            no_auto_auth: Disable automatic authentication
            scroll_y_offset: Vertical scroll offset
            required_props_first: Show required properties first
            sort_props_alphabetically: Sort properties alphabetically
            sort_enum_values_alphabetically: Sort enum values alphabetically
            expand_single_schema_field: Expand single field schemas
        """
        self.theme = theme or self._get_default_theme()
        self.hide_download_button = hide_download_button
        self.hide_hostname = hide_hostname
        self.no_auto_auth = no_auto_auth
        self.scroll_y_offset = scroll_y_offset
        self.required_props_first = required_props_first
        self.sort_props_alphabetically = sort_props_alphabetically
        self.sort_enum_values_alphabetically = sort_enum_values_alphabetically
        self.expand_single_schema_field = expand_single_schema_field

    def _get_default_theme(self) -> Dict[str, Any]:
        """Get default ReDoc theme."""
        return {
            "colors": {
                "primary": "#2577a3",
                "secondary": "#8b4513",
                "light": "#ffffff",
                "dark": "#2b2b2b"
            },
            "typography": {
                "fontFamily": "Inter, sans-serif",
                "fontSize": "14px",
                "lineHeight": "1.5"
            },
            "sidebar": {
                "backgroundColor": "#f8f9fa",
                "textColor": "#2b2b2b"
            }
        }

    def get_config(self) -> Dict[str, Any]:
        """
        Get ReDoc configuration as dictionary.

        Returns:
            ReDoc configuration dictionary
        """
        return {
            "theme": self.theme,
            "hideDownloadButton": self.hide_download_button,
            "hideHostname": self.hide_hostname,
            "noAutoAuth": self.no_auto_auth,
            "scrollYOffset": self.scroll_y_offset,
            "requiredPropsFirst": self.required_props_first,
            "sortPropsAlphabetically": self.sort_props_alphabetically,
            "sortEnumValuesAlphabetically": self.sort_enum_values_alphabetically,
            "expandSingleSchemaField": self.expand_single_schema_field
        }


class DocumentationConfigurator:
    """
    Configures documentation for FastAPI applications.

    Provides methods to set up OpenAPI, Swagger UI, and ReDoc
    with comprehensive customization options.
    """

    def __init__(
        self,
        openapi_config: OpenAPIConfig = None,
        swagger_config: SwaggerUIConfig = None,
        redoc_config: ReDocConfig = None
    ):
        """
        Initialize documentation configurator.

        Args:
            openapi_config: OpenAPI configuration
            swagger_config: Swagger UI configuration
            redoc_config: ReDoc configuration
        """
        self.openapi_config = openapi_config or OpenAPIConfig()
        self.swagger_config = swagger_config or SwaggerUIConfig()
        self.redoc_config = redoc_config or ReDocConfig()

    def configure_fastapi_app(self, app: FastAPI) -> FastAPI:
        """
        Configure FastAPI app with documentation settings.

        Args:
            app: FastAPI application to configure

        Returns:
            Configured FastAPI application
        """
        # Update app metadata
        app.title = self.openapi_config.title
        app.description = self.openapi_config.description
        app.version = self.openapi_config.version
        app.summary = self.openapi_config.summary
        app.terms_of_service = self.openapi_config.terms_of_service
        app.contact = self.openapi_config.contact
        app.license_info = self.openapi_config.license_info
        app.servers = self.openapi_config.servers
        app.openapi_version = self.openapi_config.openapi_version
        app.swagger_ui_parameters = self.swagger_config.get_parameters()

        # Set custom OpenAPI function
        app.openapi = lambda: self._get_custom_openapi(app)

        # Add custom documentation endpoints
        self._add_custom_docs_endpoints(app)

        return app

    def _get_custom_openapi(self, app: FastAPI) -> Dict[str, Any]:
        """
        Generate custom OpenAPI specification.

        Args:
            app: FastAPI application

        Returns:
            Custom OpenAPI specification
        """
        if app.openapi_url:
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                summary=app.summary,
                routes=app.routes,
                openapi_version=app.openapi_version,
                servers=app.servers,
                tags=app.openapi_tags,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info
            )

            # Add custom extensions
            self._add_custom_extensions(openapi_schema)

            # Add security schemes (for future use)
            self._add_security_schemes(openapi_schema)

            # Add examples
            self._add_examples(openapi_schema)

            return openapi_schema

        return {}

    def _add_custom_extensions(self, openapi_schema: Dict[str, Any]) -> None:
        """Add custom extensions to OpenAPI schema."""
        # Add custom extension for API information
        if "x-api-info" not in openapi_schema:
            openapi_schema["x-api-info"] = {
                "version": self.openapi_config.version,
                "status": "active",
                "repository": "https://github.com/vpsweb/vpsweb",
                "documentation": {
                    "api_reference": "/api/docs",
                    "changelog": "/api/changelog",
                    "migration_guides": "/api/migration",
                    "examples": "/api/examples"
                }
            }

        # Add custom extension for rate limiting
        if "x-rate-limit" not in openapi_schema:
            openapi_schema["x-rate-limit"] = {
                "requests_per_minute": 100,
                "burst": 20,
                "headers": {
                    "X-RateLimit-Limit": "Total requests allowed per time window",
                    "X-RateLimit-Remaining": "Remaining requests in current window",
                    "X-RateLimit-Reset": "Time when rate limit resets"
                }
            }

    def _add_security_schemes(self, openapi_schema: Dict[str, Any]) -> None:
        """Add security schemes for future authentication."""
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        if "securitySchemes" not in openapi_schema["components"]:
            openapi_schema["components"]["securitySchemes"] = {
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key authentication (future implementation)"
                },
                "oauth2": {
                    "type": "oauth2",
                    "flows": {
                        "authorizationCode": {
                            "authorizationUrl": "https://auth.vpsweb.dev/oauth/authorize",
                            "tokenUrl": "https://auth.vpsweb.dev/oauth/token",
                            "scopes": {
                                "read": "Read access to poems and translations",
                                "write": "Write access to poems and translations",
                                "admin": "Administrative access"
                            }
                        }
                    }
                }
            }

    def _add_examples(self, openapi_schema: Dict[str, Any]) -> None:
        """Add examples to OpenAPI schema."""
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}

        if "examples" not in openapi_schema["components"]:
            openapi_schema["components"]["examples"] = {
                "poem_example": {
                    "summary": "Example poem",
                    "description": "Example of a poem with metadata",
                    "value": {
                        "poet_name": "陶渊明",
                        "poem_title": "歸園田居",
                        "original_text": "種豆南山下，草盛豆苗稀。\n晨興理荒穢，帶月荷鋤歸。",
                        "source_language": "zh",
                        "tags": ["classical", "pastoral", "nature"],
                        "is_active": True
                    }
                },
                "translation_example": {
                    "summary": "Example translation",
                    "description": "Example of a poem translation",
                    "value": {
                        "translated_text": "Planting beans at the southern mountain,\nThe bean seedlings are sparse among the grass.\nRise early to tend to the weeds,\nReturn carrying the hoe under the moon.",
                        "target_language": "en",
                        "version": 1,
                        "translator_type": "hybrid",
                        "quality_score": 0.85,
                        "is_published": True
                    }
                }
            }

    def _add_custom_docs_endpoints(self, app: FastAPI) -> None:
        """Add custom documentation endpoints."""

        @app.get("/api/documentation", tags=["Documentation"], include_in_schema=False)
        async def get_documentation_info():
            """
            Get comprehensive documentation information.

            Returns information about all available documentation
            formats, endpoints, and how to access them.
            """
            return {
                "documentation": {
                    "interactive": {
                        "swagger_ui": {
                            "url": "/docs",
                            "description": "Interactive API documentation (Swagger UI)",
                            "features": [
                                "Try it out functionality",
                                "Request/response examples",
                                "Parameter validation",
                                "Code snippets in multiple languages"
                            ]
                        },
                        "redoc": {
                            "url": "/redoc",
                            "description": "Alternative API documentation (ReDoc)",
                            "features": [
                                "Three-panel layout",
                                "Code samples",
                                "API reference",
                                "Mobile-friendly design"
                            ]
                        }
                    },
                    "specification": {
                        "openapi_json": {
                            "url": "/openapi.json",
                            "description": "OpenAPI specification in JSON format",
                            "version": self.openapi_config.openapi_version
                        }
                    },
                    "guides": {
                        "quick_start": {
                            "url": "/api/docs/quick-start",
                            "description": "Quick start guide for API usage"
                        },
                        "examples": {
                            "url": "/api/examples",
                            "description": "API usage examples and code samples"
                        },
                        "changelog": {
                            "url": "/api/changelog",
                            "description": "API changelog and version history"
                        }
                    }
                },
                "tools": {
                    "postman_collection": {
                        "url": "/api/postman",
                        "description": "Postman collection for API testing"
                    },
                    "openapi_generator": {
                        "url": "/api/generator",
                        "description": "Generate client SDKs using OpenAPI Generator"
                    }
                }
            }

        @app.get("/api/examples", tags=["Documentation"])
        async def get_api_examples():
            """
            Get API usage examples.

            Returns practical examples of how to use different
            API endpoints with request/response examples.
            """
            return {
                "examples": {
                    "poems": {
                        "create_poem": {
                            "method": "POST",
                            "url": "/api/v1/poems",
                            "description": "Create a new poem",
                            "request": {
                                "poet_name": "William Shakespeare",
                                "poem_title": "Sonnet 18",
                                "original_text": "Shall I compare thee to a summer's day?\nThou art more lovely and more temperate:",
                                "source_language": "en",
                                "tags": ["sonnet", "love", "classic"]
                            },
                            "response": {
                                "id": "01HXRQ8YJ9P9N7Q4J8K2R4S4T3",
                                "poet_name": "William Shakespeare",
                                "poem_title": "Sonnet 18",
                                "original_text": "Shall I compare thee to a summer's day?\nThou art more lovely and more temperate:",
                                "source_language": "en",
                                "tags": ["sonnet", "love", "classic"],
                                "is_active": True,
                                "created_at": "2025-01-19T10:30:00Z",
                                "updated_at": "2025-01-19T10:30:00Z"
                            }
                        },
                        "search_poems": {
                            "method": "GET",
                            "url": "/api/v1/poems/search",
                            "description": "Search for poems",
                            "parameters": {
                                "query": "love",
                                "source_language": "en",
                                "per_page": 10,
                                "page": 1
                            },
                            "response": {
                                "items": [...],
                                "total": 42,
                                "page": 1,
                                "per_page": 10,
                                "total_pages": 5
                            }
                        }
                    },
                    "translations": {
                        "create_translation": {
                            "method": "POST",
                            "url": "/api/v1/poems/{poem_id}/translations",
                            "description": "Create a translation for a poem",
                            "request": {
                                "translated_text": "我能否将你比作夏日？\n但你更加可爱和温和：",
                                "target_language": "zh",
                                "translator_type": "human"
                            }
                        }
                    }
                },
                "code_samples": {
                    "python": {
                        "library": "httpx",
                        "example": """
import httpx

# Create a poem
response = httpx.post(
    "http://localhost:8000/api/v1/poems",
    json={
        "poet_name": "William Shakespeare",
        "poem_title": "Sonnet 18",
        "original_text": "Shall I compare thee to a summer's day?",
        "source_language": "en"
    }
)
poem = response.json()

# Search poems
response = httpx.get(
    "http://localhost:8000/api/v1/poems/search",
    params={"query": "love", "per_page": 5}
)
results = response.json()
                        """.strip()
                    },
                    "javascript": {
                        "library": "fetch",
                        "example": """
// Create a poem
const response = await fetch('http://localhost:8000/api/v1/poems', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        poet_name: 'William Shakespeare',
        poem_title: 'Sonnet 18',
        original_text: 'Shall I compare thee to a summer\\'s day?',
        source_language: 'en'
    })
});
const poem = await response.json();

// Search poems
const searchResponse = await fetch(
    'http://localhost:8000/api/v1/poems/search?query=love&per_page=5'
);
const results = await searchResponse.json();
                        """.strip()
                    }
                }
            }


def setup_documentation(
    app: FastAPI,
    openapi_config: OpenAPIConfig = None,
    swagger_config: SwaggerUIConfig = None,
    redoc_config: ReDocConfig = None
) -> FastAPI:
    """
    Set up comprehensive documentation for FastAPI application.

    Args:
        app: FastAPI application to configure
        openapi_config: OpenAPI configuration
        swagger_config: Swagger UI configuration
        redoc_config: ReDoc configuration

    Returns:
        Configured FastAPI application
    """
    configurator = DocumentationConfigurator(
        openapi_config=openapi_config,
        swagger_config=swagger_config,
        redoc_config=redoc_config
    )

    return configurator.configure_fastapi_app(app)


# Default configurations
DEFAULT_OPENAPI_CONFIG = OpenAPIConfig()
DEFAULT_SWAGGER_CONFIG = SwaggerUIConfig()
DEFAULT_REDOC_CONFIG = ReDocConfig()