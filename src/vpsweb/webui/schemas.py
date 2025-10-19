"""
VPSWeb Web UI Pydantic Schemas v0.3.1

Web interface specific schemas for form data and API responses.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum

from src.vpsweb.repository.schemas import (
    PoemResponse,
    TranslationResponse,
    WorkflowMode,
    ComparisonView,
    RepositoryStats
)


class TranslatorType(str, Enum):
    """Translator type enumeration"""
    AI = "AI"
    HUMAN = "Human"


class WebUIBase(BaseModel):
    """Base schema for web UI with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


# Form schemas (for HTML form submissions)
class PoemFormCreate(WebUIBase):
    """Schema for poem creation form"""
    poet_name: str = Field(..., min_length=1, max_length=200, description="Name of the poet")
    poem_title: str = Field(..., min_length=1, max_length=300, description="Title of the poem")
    source_language: str = Field(..., min_length=2, max_length=10, description="Source language code")
    original_text: str = Field(..., min_length=1, description="Original poem text")
    metadata: Optional[str] = Field(None, max_length=1000, description="Optional metadata")

    @field_validator('original_text')
    @classmethod
    def clean_text(cls, v):
        """Clean up text input"""
        if v:
            return v.strip()
        return v


class TranslationFormCreate(WebUIBase):
    """Schema for translation creation form"""
    poem_id: str = Field(..., description="ID of the poem")
    target_language: str = Field(..., min_length=2, max_length=10, description="Target language")
    translator_name: Optional[str] = Field(None, max_length=200, description="Human translator name")
    translated_text: str = Field(..., min_length=1, description="Translated text")
    quality_rating: Optional[int] = Field(None, ge=1, le=5, description="Quality rating")

    @field_validator('translated_text')
    @classmethod
    def clean_text(cls, v):
        """Clean up text input"""
        if v:
            return v.strip()
        return v


class TranslationFormRequest(WebUIBase):
    """Schema for translation workflow request from form"""
    poem_id: str = Field(..., description="ID of the poem to translate")
    target_lang: str = Field(..., min_length=2, max_length=10, description="Target language")
    workflow_mode: WorkflowMode = Field(WorkflowMode.HYBRID, description="Translation workflow mode")


# Page display schemas
class DashboardPage(WebUIBase):
    """Schema for dashboard page data"""
    poems: List[PoemResponse] = Field(default_factory=list, description="Recent poems")
    total_poems: int = Field(0, description="Total number of poems")
    total_translations: int = Field(0, description="Total number of translations")
    stats: RepositoryStats = Field(..., description="Repository statistics")


class PoemDetailPage(WebUIBase):
    """Schema for poem detail page data"""
    poem: PoemResponse = Field(..., description="Poem information")
    translations: List[TranslationResponse] = Field(default_factory=list, description="All translations")
    comparison_data: Optional[ComparisonView] = Field(None, description="Comparison view data")


class ComparisonPage(WebUIBase):
    """Schema for comparison page data"""
    poem: PoemResponse = Field(..., description="Poem information")
    comparison_data: ComparisonView = Field(..., description="Comparison view data")


# Search and filter schemas
class SearchQuery(WebUIBase):
    """Schema for search queries"""
    q: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    language: Optional[str] = Field(None, min_length=2, max_length=10, description="Language filter")
    poet: Optional[str] = Field(None, min_length=1, max_length=100, description="Poet filter")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")


# API response schemas for web UI
class WebAPIResponse(WebUIBase):
    """Generic web API response"""
    success: bool = Field(True, description="Request success status")
    message: str = Field("Operation completed successfully", description="Response message")
    data: Optional[dict] = Field(None, description="Response data")
    redirect_url: Optional[str] = Field(None, description="Optional redirect URL")


class TranslationFormResponse(WebAPIResponse):
    """Schema for translation form submission response"""
    translation_id: Optional[str] = Field(None, description="Created translation ID")
    model_name: Optional[str] = Field(None, description="AI model name")


# UI Component schemas
class TranslationCard(WebUIBase):
    """Schema for translation card display"""
    id: str = Field(..., description="Translation ID")
    translator_type: str = Field(..., description="Translator type")
    translator_info: str = Field(..., description="Translator information")
    target_language: str = Field(..., description="Target language")
    created_at: datetime = Field(..., description="Creation timestamp")
    quality_rating: Optional[int] = Field(None, description="Quality rating")
    has_notes: bool = Field(False, description="Has human notes")
    runtime_info: Optional[dict] = Field(None, description="Runtime information for AI translations")


class PoemCard(WebUIBase):
    """Schema for poem card display"""
    id: str = Field(..., description="Poem ID")
    poet_name: str = Field(..., description="Poet name")
    poem_title: str = Field(..., description="Poem title")
    source_language: str = Field(..., description="Source language")
    created_at: datetime = Field(..., description="Creation timestamp")
    translation_count: int = Field(0, description="Number of translations")
    ai_translation_count: int = Field(0, description="Number of AI translations")
    human_translation_count: int = Field(0, description="Number of human translations")
    can_translate: bool = Field(True, description="Whether translation is possible")


# Navigation schemas
class NavigationItem(WebUIBase):
    """Schema for navigation item"""
    name: str = Field(..., description="Display name")
    url: str = Field(..., description="URL")
    active: bool = Field(False, description="Whether this is the current page")
    icon: Optional[str] = Field(None, description="Icon name")


class NavigationBar(WebUIBase):
    """Schema for navigation bar"""
    items: List[NavigationItem] = Field(default_factory=list, description="Navigation items")
    user_info: Optional[dict] = Field(None, description="User information (for future auth)")


# Pagination schemas
class PaginationInfo(WebUIBase):
    """Schema for pagination information"""
    current_page: int = Field(..., ge=1, description="Current page")
    total_pages: int = Field(..., ge=0, description="Total pages")
    total_items: int = Field(..., ge=0, description="Total items")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(False, description="Has next page")
    has_previous: bool = Field(False, description="Has previous page")
    next_page_url: Optional[str] = Field(None, description="Next page URL")
    previous_page_url: Optional[str] = Field(None, description="Previous page URL")


# Flash message schemas
class FlashMessage(WebUIBase):
    """Schema for flash messages"""
    message: str = Field(..., description="Message text")
    type: str = Field(..., pattern="^(success|error|warning|info)$", description="Message type")
    auto_dismiss: bool = Field(True, description="Whether to auto-dismiss")


class FlashMessages(WebUIBase):
    """Schema for flash messages list"""
    messages: List[FlashMessage] = Field(default_factory=list, description="List of flash messages")