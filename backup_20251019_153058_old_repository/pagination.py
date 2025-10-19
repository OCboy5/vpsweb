"""
Pagination utilities for VPSWeb Repository System.

This module provides pagination support for API endpoints, including
query parameters, response formatting, and database query helpers.

Features:
- Standardized pagination query parameters
- Pagination response schemas
- Database query pagination helpers
- Metadata generation for paginated responses
"""

from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar
from math import ceil
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from pydantic import BaseModel, Field, validator

T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    Standard pagination parameters for API endpoints.

    Supports both page-based and offset-based pagination with
    configurable limits and default values.
    """
    page: int = Field(1, ge=1, description="Page number (1-based)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page (max 100)")
    offset: Optional[int] = Field(None, ge=0, description="Offset for alternative pagination")

    @validator('per_page')
    def validate_per_page(cls, v):
        """Validate per_page is within reasonable bounds."""
        if v > 100:
            raise ValueError('per_page cannot exceed 100 items')
        if v < 1:
            raise ValueError('per_page must be at least 1')
        return v

    @classmethod
    def from_query_params(cls, **kwargs) -> 'PaginationParams':
        """
        Create PaginationParams from query parameters.

        Args:
            **kwargs: Query parameters from request

        Returns:
            PaginationParams instance
        """
        # Convert string parameters to integers
        page = int(kwargs.get('page', 1))
        per_page = int(kwargs.get('per_page', 20))
        offset = kwargs.get('offset')

        if offset is not None:
            offset = int(offset)

        return cls(page=page, per_page=per_page, offset=offset)

    def get_offset(self) -> int:
        """Calculate offset for database queries."""
        if self.offset is not None:
            return self.offset
        return (self.page - 1) * self.per_page

    def get_limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page

    def has_next_page(self, total_items: int) -> bool:
        """Check if there is a next page."""
        total_pages = self.get_total_pages(total_items)
        return self.page < total_pages

    def has_prev_page(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1 or (self.offset is not None and self.offset > 0)

    def get_total_pages(self, total_items: int) -> int:
        """Calculate total number of pages."""
        return ceil(total_items / self.per_page) if total_items > 0 else 1


class PaginationMeta(BaseModel):
    """
    Pagination metadata for API responses.

    Provides comprehensive pagination information including
    navigation links and statistics.
    """
    current_page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether next page exists")
    has_prev: bool = Field(..., description="Whether previous page exists")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")

    @classmethod
    def create(
        cls,
        pagination_params: PaginationParams,
        total_items: int
    ) -> 'PaginationMeta':
        """
        Create pagination metadata.

        Args:
            pagination_params: Pagination parameters
            total_items: Total number of items

        Returns:
            PaginationMeta instance
        """
        total_pages = pagination_params.get_total_pages(total_items)

        return cls(
            current_page=pagination_params.page,
            per_page=pagination_params.per_page,
            total_items=total_items,
            total_pages=total_pages,
            has_next=pagination_params.has_next_page(total_items),
            has_prev=pagination_params.has_prev_page(),
            next_page=pagination_params.page + 1 if pagination_params.has_next_page(total_items) else None,
            prev_page=pagination_params.page - 1 if pagination_params.has_prev_page() else None
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response format.

    Generic response that wraps a list of items with pagination metadata.
    """
    items: List[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: List[T],
        pagination_params: PaginationParams,
        total_items: int
    ) -> 'PaginatedResponse[T]':
        """
        Create a paginated response.

        Args:
            items: List of items for current page
            pagination_params: Pagination parameters used
            total_items: Total number of items across all pages

        Returns:
            PaginatedResponse instance
        """
        pagination_meta = PaginationMeta.create(pagination_params, total_items)

        return cls(
            items=items,
            pagination=pagination_meta
        )


class FilterParams(BaseModel):
    """
    Base class for filter parameters.

    Provides common filtering functionality that can be extended
    for specific entity types.
    """
    search: Optional[str] = Field(None, description="Search query for text fields")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$", description="Sort order")

    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order is either asc or desc."""
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be either "asc" or "desc"')
        return v.lower()

    def has_filters(self) -> bool:
        """Check if any filters are applied."""
        return any([
            self.search,
            self.sort_by
        ])


class SortField:
    """
    Helper class for defining sortable fields.

    Provides field mapping and validation for sorting parameters.
    """

    def __init__(self, field_name: str, display_name: str, column_name: Optional[str] = None):
        """
        Initialize sort field.

        Args:
            field_name: Field name for API parameters
            display_name: Human-readable display name
            column_name: Database column name (defaults to field_name)
        """
        self.field_name = field_name
        self.display_name = display_name
        self.column_name = column_name or field_name

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            'field_name': self.field_name,
            'display_name': self.display_name,
            'column_name': self.column_name
        }


class SortFieldRegistry:
    """
    Registry for sortable fields for different entity types.

    Centralized configuration of what fields can be sorted
    and how they map to database columns.
    """

    # Common sort fields for poems
    POEM_SORT_FIELDS = [
        SortField('title', 'Title', 'poem_title'),
        SortField('poet_name', 'Poet Name', 'poet_name'),
        SortField('source_language', 'Source Language'),
        SortField('created_at', 'Created At'),
        SortField('updated_at', 'Updated At'),
        SortField('is_active', 'Active Status'),
    ]

    # Common sort fields for translations
    TRANSLATION_SORT_FIELDS = [
        SortField('target_language', 'Target Language'),
        SortField('version', 'Version'),
        SortField('translator_type', 'Translator Type'),
        SortField('quality_score', 'Quality Score'),
        SortField('created_at', 'Created At'),
        SortField('updated_at', 'Updated At'),
        SortField('is_published', 'Published Status'),
    ]

    # Common sort fields for AI logs
    AI_LOG_SORT_FIELDS = [
        SortField('provider', 'AI Provider'),
        SortField('model_name', 'Model Name'),
        SortField('workflow_mode', 'Workflow Mode'),
        SortField('status', 'Status'),
        SortField('duration_seconds', 'Duration'),
        SortField('total_tokens', 'Total Tokens'),
        SortField('cost', 'Cost'),
        SortField('created_at', 'Created At'),
    ]

    # Common sort fields for human notes
    HUMAN_NOTE_SORT_FIELDS = [
        SortField('note_type', 'Note Type'),
        SortField('author_name', 'Author Name'),
        SortField('is_public', 'Public Status'),
        SortField('created_at', 'Created At'),
        SortField('updated_at', 'Updated At'),
    ]

    @classmethod
    def get_sort_fields(cls, entity_type: str) -> List[SortField]:
        """
        Get sort fields for an entity type.

        Args:
            entity_type: Type of entity ('poem', 'translation', 'ai_log', 'human_note')

        Returns:
            List of SortField instances
        """
        field_map = {
            'poem': cls.POEM_SORT_FIELDS,
            'translation': cls.TRANSLATION_SORT_FIELDS,
            'ai_log': cls.AI_LOG_SORT_FIELDS,
            'human_note': cls.HUMAN_NOTE_SORT_FIELDS,
        }

        return field_map.get(entity_type, [])

    @classmethod
    def validate_sort_field(cls, entity_type: str, sort_field: str) -> Optional[str]:
        """
        Validate and normalize sort field.

        Args:
            entity_type: Type of entity
            sort_field: Sort field name to validate

        Returns:
            Normalized column name or None if invalid
        """
        sort_fields = cls.get_sort_fields(entity_type)

        for field in sort_fields:
            if field.field_name == sort_field:
                return field.column_name

        return None


def build_pagination_links(
    base_url: str,
    pagination_params: PaginationParams,
    total_items: int,
    additional_params: Optional[Dict[str, str]] = None
) -> Dict[str, Optional[str]]:
    """
    Build pagination navigation links.

    Args:
        base_url: Base URL for pagination links
        pagination_params: Current pagination parameters
        total_items: Total number of items
        additional_params: Additional query parameters to include

    Returns:
        Dictionary with pagination links
    """
    if additional_params is None:
        additional_params = {}

    # Parse base URL
    parsed = urlparse(base_url)
    query_params = parse_qs(parsed.query)

    # Add additional parameters
    for key, value in additional_params.items():
        query_params[key] = [value]

    total_pages = pagination_params.get_total_pages(total_items)
    links = {}

    def build_url(page: int) -> str:
        """Build URL for specific page."""
        params = query_params.copy()
        params['page'] = [str(page)]
        params['per_page'] = [str(pagination_params.per_page)]

        query_string = urlencode(params, doseq=True)

        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query_string,
            parsed.fragment
        ))

    # Self link
    links['self'] = build_url(pagination_params.page)

    # First page
    if pagination_params.page > 1:
        links['first'] = build_url(1)
    else:
        links['first'] = None

    # Last page
    if total_pages > 1:
        links['last'] = build_url(total_pages)
    else:
        links['last'] = None

    # Previous page
    if pagination_params.has_prev_page():
        if pagination_params.offset is not None:
            # Offset-based pagination
            prev_offset = max(0, pagination_params.offset - pagination_params.per_page)
            params = query_params.copy()
            params['offset'] = [str(prev_offset)]
            params['per_page'] = [str(pagination_params.per_page)]

            query_string = urlencode(params, doseq=True)
            links['prev'] = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                parsed.fragment
            ))
        else:
            # Page-based pagination
            links['prev'] = build_url(pagination_params.page - 1)
    else:
        links['prev'] = None

    # Next page
    if pagination_params.has_next_page(total_items):
        if pagination_params.offset is not None:
            # Offset-based pagination
            next_offset = pagination_params.offset + pagination_params.per_page
            params = query_params.copy()
            params['offset'] = [str(next_offset)]
            params['per_page'] = [str(pagination_params.per_page)]

            query_string = urlencode(params, doseq=True)
            links['next'] = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                parsed.fragment
            ))
        else:
            # Page-based pagination
            links['next'] = build_url(pagination_params.page + 1)
    else:
        links['next'] = None

    return links


# Database query helpers
def apply_pagination_to_query(query, pagination_params: PaginationParams):
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query
        pagination_params: Pagination parameters

    Returns:
        Query with pagination applied
    """
    return query.offset(pagination_params.get_offset()).limit(pagination_params.get_limit())


def apply_sorting_to_query(query, sort_field: str, sort_order: str, model_class):
    """
    Apply sorting to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query
        sort_field: Field name to sort by
        sort_order: Sort order ('asc' or 'desc')
        model_class: SQLAlchemy model class

    Returns:
        Query with sorting applied
    """
    if hasattr(model_class, sort_field):
        field = getattr(model_class, sort_field)

        if sort_order.lower() == 'desc':
            return query.order_by(field.desc())
        else:
            return query.order_by(field.asc())

    # If field doesn't exist, return original query
    return query