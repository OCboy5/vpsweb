"""
Search and Query Functionality for VPSWeb Repository System.

This module provides comprehensive search capabilities including
full-text search, filtering, sorting, and advanced query building
for poems, translations, and other repository entities.

Features:
- Full-text search across multiple fields
- Advanced filtering with multiple criteria
- Dynamic query building
- Search result ranking and scoring
- Search query parsing and validation
- Performance-optimized search queries
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from datetime import datetime, date
from enum import Enum
import re

from sqlalchemy import (
    select, and_, or_, func, text, desc, asc,
    String, Integer, DateTime, Date, Boolean
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select
from pydantic import BaseModel, Field, validator

from .models import Poem, Translation, AiLog, HumanNote
from .exceptions import ValidationException

T = TypeVar('T')


class SearchOperator(str, Enum):
    """Search operators for query building."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"


class SearchCondition(BaseModel):
    """
    Represents a single search condition.

    Defines a field, operator, value, and logical relationship
    for building complex search queries.
    """
    field: str = Field(..., description="Field name to search on")
    operator: SearchOperator = Field(..., description="Search operator")
    value: Optional[Union[str, int, float, bool, List[Any]]] = Field(
        None, description="Value to search for"
    )
    logical_op: LogicalOperator = Field(LogicalOperator.AND, description="Logical operator")

    @validator('value')
    def validate_value(cls, v, values):
        """Validate value based on operator."""
        operator = values.get('operator')

        if operator in [SearchOperator.IS_NULL, SearchOperator.IS_NOT_NULL]:
            return None  # These operators don't need values

        if operator in [SearchOperator.IN, SearchOperator.NOT_IN]:
            if not isinstance(v, list):
                raise ValueError(f"Operator {operator} requires a list value")

        return v


class SearchQuery(BaseModel):
    """
    Represents a complete search query.

    Contains multiple conditions, sorting, and pagination
    parameters for comprehensive search functionality.
    """
    conditions: List[SearchCondition] = Field(default_factory=list)
    search_text: Optional[str] = Field(None, description="Full-text search query")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", regex="^(asc|desc)$")
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError('sort_order must be either "asc" or "desc"')
        return v.lower()


class SearchResult(BaseModel, Generic[T]):
    """
    Represents search results with metadata.

    Contains the search results along with pagination
    information and search metadata.
    """
    items: List[T] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    query_time_ms: Optional[float] = Field(None, description="Query execution time in milliseconds")
    search_time_ms: Optional[float] = Field(None, description="Total search time in milliseconds")


class SearchField:
    """
    Defines a searchable field with its properties.

    Encapsulates field metadata for search functionality
    including field type, weight, and search capabilities.
    """

    def __init__(
        self,
        name: str,
        field_type: Type,
        weight: float = 1.0,
        searchable: bool = True,
        filterable: bool = True,
        sortable: bool = True
    ):
        """
        Initialize search field.

        Args:
            name: Field name
            field_type: Python type of the field
            weight: Search weight for ranking
            searchable: Whether field is included in full-text search
            filterable: Whether field can be used for filtering
            sortable: Whether field can be used for sorting
        """
        self.name = name
        self.field_type = field_type
        self.weight = weight
        self.searchable = searchable
        self.filterable = filterable
        self.sortable = sortable


class SearchFieldRegistry:
    """
    Registry of searchable fields for different entity types.

    Centralized configuration of what fields can be searched
    and how they should be handled.
    """

    # Search fields for poems
    POEM_FIELDS = {
        'id': SearchField('id', str, weight=0.5, searchable=False, filterable=True),
        'poet_name': SearchField('poet_name', str, weight=2.0),
        'poem_title': SearchField('poem_title', str, weight=1.5),
        'original_text': SearchField('original_text', str, weight=1.0),
        'source_language': SearchField('source_language', str, weight=0.8, filterable=True),
        'tags': SearchField('tags', str, weight=0.7, filterable=True),
        'is_active': SearchField('is_active', bool, weight=0.3, filterable=True),
        'created_at': SearchField('created_at', datetime, weight=0.2, sortable=True),
        'updated_at': SearchField('updated_at', datetime, weight=0.2, sortable=True),
    }

    # Search fields for translations
    TRANSLATION_FIELDS = {
        'id': SearchField('id', str, weight=0.5, searchable=False, filterable=True),
        'poem_id': SearchField('poem_id', str, weight=0.3, searchable=False, filterable=True),
        'translated_text': SearchField('translated_text', str, weight=1.5),
        'target_language': SearchField('target_language', str, weight=0.8, filterable=True),
        'version': SearchField('version', int, weight=0.4, filterable=True, sortable=True),
        'translator_type': SearchField('translator_type', str, weight=0.6, filterable=True),
        'quality_score': SearchField('quality_score', float, weight=0.5, filterable=True, sortable=True),
        'is_published': SearchField('is_published', bool, weight=0.3, filterable=True),
        'created_at': SearchField('created_at', datetime, weight=0.2, sortable=True),
        'updated_at': SearchField('updated_at', datetime, weight=0.2, sortable=True),
    }

    # Search fields for AI logs
    AI_LOG_FIELDS = {
        'id': SearchField('id', str, weight=0.5, searchable=False, filterable=True),
        'poem_id': SearchField('poem_id', str, weight=0.3, searchable=False, filterable=True),
        'translation_id': SearchField('translation_id', str, weight=0.3, searchable=False, filterable=True),
        'provider': SearchField('provider', str, weight=0.8, filterable=True),
        'model_name': SearchField('model_name', str, weight=0.7, filterable=True),
        'workflow_mode': SearchField('workflow_mode', str, weight=0.6, filterable=True),
        'status': SearchField('status', str, weight=0.5, filterable=True),
        'duration_seconds': SearchField('duration_seconds', float, weight=0.4, filterable=True, sortable=True),
        'total_tokens': SearchField('total_tokens', int, weight=0.4, filterable=True, sortable=True),
        'cost': SearchField('cost', float, weight=0.4, filterable=True, sortable=True),
        'created_at': SearchField('created_at', datetime, weight=0.2, sortable=True),
    }

    # Search fields for human notes
    HUMAN_NOTE_FIELDS = {
        'id': SearchField('id', str, weight=0.5, searchable=False, filterable=True),
        'poem_id': SearchField('poem_id', str, weight=0.3, searchable=False, filterable=True),
        'translation_id': SearchField('translation_id', str, weight=0.3, searchable=False, filterable=True),
        'title': SearchField('title', str, weight=1.2),
        'content': SearchField('content', str, weight=1.0),
        'note_type': SearchField('note_type', str, weight=0.8, filterable=True),
        'author_name': SearchField('author_name', str, weight=0.6, filterable=True),
        'is_public': SearchField('is_public', bool, weight=0.3, filterable=True),
        'created_at': SearchField('created_at', datetime, weight=0.2, sortable=True),
        'updated_at': SearchField('updated_at', datetime, weight=0.2, sortable=True),
    }

    @classmethod
    def get_fields(cls, entity_type: str) -> Dict[str, SearchField]:
        """
        Get search fields for an entity type.

        Args:
            entity_type: Type of entity ('poem', 'translation', 'ai_log', 'human_note')

        Returns:
            Dictionary of SearchField instances
        """
        field_map = {
            'poem': cls.POEM_FIELDS,
            'translation': cls.TRANSLATION_FIELDS,
            'ai_log': cls.AI_LOG_FIELDS,
            'human_note': cls.HUMAN_NOTE_FIELDS,
        }

        return field_map.get(entity_type, {})

    @classmethod
    def get_searchable_fields(cls, entity_type: str) -> List[SearchField]:
        """Get searchable fields for an entity type."""
        fields = cls.get_fields(entity_type)
        return [field for field in fields.values() if field.searchable]

    @classmethod
    def get_filterable_fields(cls, entity_type: str) -> List[SearchField]:
        """Get filterable fields for an entity type."""
        fields = cls.get_fields(entity_type)
        return [field for field in fields.values() if field.filterable]

    @classmethod
    def get_sortable_fields(cls, entity_type: str) -> List[SearchField]:
        """Get sortable fields for an entity type."""
        fields = cls.get_fields(entity_type)
        return [field for field in fields.values() if field.sortable]


class QueryBuilder:
    """
    Builds database queries from search conditions.

    Translates SearchCondition objects into SQLAlchemy
    queries with proper operator handling and type safety.
    """

    @staticmethod
    def build_condition(
        condition: SearchCondition,
        model_class: Type
    ) -> Any:
        """
        Build a single condition for SQLAlchemy query.

        Args:
            condition: Search condition to build
            model_class: SQLAlchemy model class

        Returns:
            SQLAlchemy condition expression
        """
        if not hasattr(model_class, condition.field):
            raise ValidationException(f"Invalid field: {condition.field}")

        field = getattr(model_class, condition.field)

        # Handle different operators
        if condition.operator == SearchOperator.EQUALS:
            return field == condition.value

        elif condition.operator == SearchOperator.NOT_EQUALS:
            return field != condition.value

        elif condition.operator == SearchOperator.GREATER_THAN:
            return field > condition.value

        elif condition.operator == SearchOperator.GREATER_EQUAL:
            return field >= condition.value

        elif condition.operator == SearchOperator.LESS_THAN:
            return field < condition.value

        elif condition.operator == SearchOperator.LESS_EQUAL:
            return field <= condition.value

        elif condition.operator == SearchOperator.CONTAINS:
            if hasattr(field, 'contains'):
                return field.contains(condition.value)
            else:
                return field.like(f"%{condition.value}%")

        elif condition.operator == SearchOperator.STARTS_WITH:
            return field.like(f"{condition.value}%")

        elif condition.operator == SearchOperator.ENDS_WITH:
            return field.like(f"%{condition.value}")

        elif condition.operator == SearchOperator.IN:
            return field.in_(condition.value)

        elif condition.operator == SearchOperator.NOT_IN:
            return field.notin_(condition.value)

        elif condition.operator == SearchOperator.IS_NULL:
            return field.is_(None)

        elif condition.operator == SearchOperator.IS_NOT_NULL:
            return field.isnot(None)

        elif condition.operator == SearchOperator.BETWEEN:
            if not isinstance(condition.value, (list, tuple)) or len(condition.value) != 2:
                raise ValidationException("BETWEEN operator requires a list of two values")
            return field.between(condition.value[0], condition.value[1])

        else:
            raise ValidationException(f"Unsupported operator: {condition.operator}")

    @staticmethod
    def build_query(
        search_query: SearchQuery,
        model_class: Type
    ) -> Select:
        """
        Build a complete SQLAlchemy query from search parameters.

        Args:
            search_query: Search query parameters
            model_class: SQLAlchemy model class

        Returns:
            SQLAlchemy select query
        """
        query = select(model_class)

        # Build conditions
        conditions = []
        for condition in search_query.conditions:
            db_condition = QueryBuilder.build_condition(condition, model_class)
            conditions.append((condition.logical_op, db_condition))

        # Apply conditions with logical operators
        if conditions:
            combined_condition = None
            for logical_op, db_condition in conditions:
                if combined_condition is None:
                    combined_condition = db_condition
                elif logical_op == LogicalOperator.AND:
                    combined_condition = and_(combined_condition, db_condition)
                else:  # OR
                    combined_condition = or_(combined_condition, db_condition)

            query = query.where(combined_condition)

        # Apply full-text search
        if search_query.search_text:
            searchable_fields = SearchFieldRegistry.get_searchable_fields(
                model_class.__tablename__.replace('_', '')
            )

            if searchable_fields:
                text_conditions = []
                for field in searchable_fields:
                    if hasattr(model_class, field.name):
                        db_field = getattr(model_class, field.name)
                        text_conditions.append(db_field.like(f"%{search_query.search_text}%"))

                if text_conditions:
                    text_query = or_(*text_conditions)
                    if conditions:  # If there are existing conditions
                        query = query.where(and_(combined_condition, text_query))
                    else:
                        query = query.where(text_query)

        # Apply sorting
        if search_query.sort_by:
            sortable_fields = SearchFieldRegistry.get_sortable_fields(
                model_class.__tablename__.replace('_', '')
            )

            # Check if field is sortable
            sortable_field_names = [f.name for f in sortable_fields]
            if search_query.sort_by in sortable_field_names:
                sort_field = getattr(model_class, search_query.sort_by)
                if search_query.sort_order == 'desc':
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(asc(sort_field))

        # Apply pagination
        offset = (search_query.page - 1) * search_query.per_page
        query = query.offset(offset).limit(search_query.per_page)

        return query


class SearchService:
    """
    High-level search service for repository entities.

    Provides search functionality with query building,
    result processing, and performance optimization.
    """

    def __init__(self, db_session):
        """
        Initialize search service.

        Args:
            db_session: Database session
        """
        self.db_session = db_session

    async def search(
        self,
        search_query: SearchQuery,
        entity_type: str
    ) -> SearchResult:
        """
        Perform search on specified entity type.

        Args:
            search_query: Search query parameters
            entity_type: Type of entity to search

        Returns:
            Search results with metadata
        """
        import time
        start_time = time.time()

        # Get model class
        model_map = {
            'poem': Poem,
            'translation': Translation,
            'ai_log': AiLog,
            'human_note': HumanNote,
        }

        model_class = model_map.get(entity_type)
        if not model_class:
            raise ValidationException(f"Invalid entity type: {entity_type}")

        # Build query
        query = QueryBuilder.build_query(search_query, model_class)

        # Get total count
        count_query = select(func.count(model_class.id))
        if search_query.search_text:
            # Add text search conditions to count query
            searchable_fields = SearchFieldRegistry.get_searchable_fields(entity_type)
            text_conditions = []
            for field in searchable_fields:
                if hasattr(model_class, field.name):
                    db_field = getattr(model_class, field.name)
                    text_conditions.append(db_field.like(f"%{search_query.search_text}%"))

            if text_conditions:
                text_query = or_(*text_conditions)
                count_query = count_query.where(text_query)

        query_start = time.time()
        total = await self.db_session.scalar(count_query)
        query_time = (time.time() - query_start) * 1000

        # Execute search query
        result_start = time.time()
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        result_time = (time.time() - result_start) * 1000

        # Calculate pagination
        total_pages = (total + search_query.per_page - 1) // search_query.per_page

        total_time = (time.time() - start_time) * 1000

        return SearchResult(
            items=list(items),
            total=total,
            page=search_query.page,
            per_page=search_query.per_page,
            total_pages=total_pages,
            query_time_ms=query_time,
            search_time_ms=total_time
        )

    async def suggest(
        self,
        query_text: str,
        entity_type: str,
        field: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get search suggestions for a field.

        Args:
            query_text: Query text to search for
            entity_type: Type of entity
            field: Field to search in
            limit: Maximum number of suggestions

        Returns:
            List of suggestions
        """
        model_map = {
            'poem': Poem,
            'translation': Translation,
            'ai_log': AiLog,
            'human_note': HumanNote,
        }

        model_class = model_map.get(entity_type)
        if not model_class:
            raise ValidationException(f"Invalid entity type: {entity_type}")

        if not hasattr(model_class, field):
            raise ValidationException(f"Invalid field: {field}")

        search_field = getattr(model_class, field)

        # Create suggestion query
        query = (
            select(search_field)
            .where(search_field.like(f"{query_text}%"))
            .distinct()
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        suggestions = [row[0] for row in result.fetchall() if row[0]]

        return suggestions


# Search query validation and parsing utilities
def parse_search_string(search_string: str) -> SearchQuery:
    """
    Parse a search string into a SearchQuery object.

    Supports advanced search syntax like:
    - "field:value" for exact matches
    - "field:>value" for greater than
    - "field:value1,value2" for IN operator
    - "free text search" for full-text search

    Args:
        search_string: Search string to parse

    Returns:
        Parsed SearchQuery object
    """
    search_query = SearchQuery()

    # Split by spaces, but preserve quoted strings
    tokens = re.findall(r'(?:"([^"]*)"|([^\s]+))', search_string)
    tokens = [token for pair in tokens for token in pair if token]

    conditions = []
    search_terms = []

    for token in tokens:
        if ':' in token and not token.startswith('"'):
            # Field-based search
            parts = token.split(':', 1)
            field = parts[0]
            value_part = parts[1]

            # Parse operator and value
            operator = SearchOperator.EQUALS
            value = value_part

            if value_part.startswith('>'):
                operator = SearchOperator.GREATER_THAN
                value = value_part[1:]
            elif value_part.startswith('<'):
                operator = SearchOperator.LESS_THAN
                value = value_part[1:]
            elif value_part.startswith('>='):
                operator = SearchOperator.GREATER_EQUAL
                value = value_part[2:]
            elif value_part.startswith('<='):
                operator = SearchOperator.LESS_EQUAL
                value = value_part[2:]
            elif value_part.startswith('!'):
                operator = SearchOperator.NOT_EQUALS
                value = value_part[1:]
            elif ',' in value_part:
                operator = SearchOperator.IN
                value = value_part.split(',')

            try:
                # Try to convert to appropriate type
                if value.replace('.', '').replace('-', '').isdigit():
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                elif value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'

                condition = SearchCondition(
                    field=field,
                    operator=operator,
                    value=value
                )
                conditions.append(condition)

            except ValueError:
                # If conversion fails, treat as search term
                search_terms.append(token)
        else:
            # Free text search
            search_terms.append(token)

    search_query.conditions = conditions
    if search_terms:
        search_query.search_text = ' '.join(search_terms)

    return search_query


def validate_search_query(search_query: SearchQuery, entity_type: str) -> SearchQuery:
    """
    Validate and normalize a search query.

    Args:
        search_query: Search query to validate
        entity_type: Type of entity being searched

    Returns:
        Validated SearchQuery object
    """
    # Get field definitions
    fields = SearchFieldRegistry.get_fields(entity_type)
    field_names = list(fields.keys())

    # Validate conditions
    validated_conditions = []
    for condition in search_query.conditions:
        if condition.field not in field_names:
            raise ValidationException(f"Invalid field: {condition.field}")

        field_def = fields[condition.field]

        # Validate operator compatibility with field type
        if condition.operator in [SearchOperator.IN, SearchOperator.NOT_IN]:
            if not isinstance(condition.value, list):
                raise ValidationException(f"Operator {condition.operator} requires a list value")

        validated_conditions.append(condition)

    search_query.conditions = validated_conditions

    # Validate sort field
    if search_query.sort_by and search_query.sort_by not in field_names:
        raise ValidationException(f"Invalid sort field: {search_query.sort_by}")

    return search_query