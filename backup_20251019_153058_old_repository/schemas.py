"""
Pydantic schemas for VPSWeb repository system API.

This module defines the data validation and serialization schemas for all API endpoints.
Provides request/response models for poems, translations, AI logs, and human notes.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum


class TranslatorType(str, Enum):
    """Enum for translator types."""
    AI = "ai"
    HUMAN = "human"
    HYBRID = "hybrid"


class WorkflowMode(str, Enum):
    """Enum for workflow modes."""
    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"


class AiLogStatus(str, Enum):
    """Enum for AI log status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ==============================
# Poem Schemas
# ==============================

class PoemBase(BaseModel):
    """Base schema for poem data."""
    poet_name: str = Field(..., min_length=1, max_length=255, description="Name of the poet")
    poem_title: str = Field(..., min_length=1, max_length=255, description="Title of the poem")
    source_language: str = Field(..., min_length=2, max_length=10, description="Source language code (BCP-47)")
    original_text: str = Field(..., min_length=1, description="Original poem text")
    author_birth_year: Optional[int] = Field(None, ge=0, le=2100, description="Poet's birth year")
    publication_year: Optional[int] = Field(None, ge=0, le=2100, description="Publication year")
    genre: Optional[str] = Field(None, max_length=100, description="Genre of the poem")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")
    is_active: bool = Field(True, description="Whether the poem is active")

    @validator('source_language')
    def validate_language_code(cls, v):
        """Basic validation for language code format."""
        if len(v) < 2 or len(v) > 10:
            raise ValueError('Language code must be between 2 and 10 characters')
        return v.lower()

    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format."""
        if v and v.strip():
            tags = [tag.strip() for tag in v.split(',')]
            if any(len(tag) > 50 for tag in tags):
                raise ValueError('Individual tags must be 50 characters or less')
            if len(tags) > 20:
                raise ValueError('Maximum 20 tags allowed')
        return v


class PoemCreate(PoemBase):
    """Schema for creating a new poem."""
    pass


class PoemUpdate(BaseModel):
    """Schema for updating an existing poem."""
    poet_name: Optional[str] = Field(None, min_length=1, max_length=255)
    poem_title: Optional[str] = Field(None, min_length=1, max_length=255)
    source_language: Optional[str] = Field(None, min_length=2, max_length=10)
    original_text: Optional[str] = Field(None, min_length=1)
    author_birth_year: Optional[int] = Field(None, ge=0, le=2100)
    publication_year: Optional[int] = Field(None, ge=0, le=2100)
    genre: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @validator('source_language')
    def validate_language_code(cls, v):
        """Basic validation for language code format."""
        if v is not None:
            if len(v) < 2 or len(v) > 10:
                raise ValueError('Language code must be between 2 and 10 characters')
            return v.lower()
        return v


class PoemResponse(PoemBase):
    """Schema for poem response data."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the poem")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    translation_count: Optional[int] = Field(None, description="Number of translations")


# ==============================
# Translation Schemas
# ==============================

class TranslationBase(BaseModel):
    """Base schema for translation data."""
    target_language: str = Field(..., min_length=2, max_length=10, description="Target language code (BCP-47)")
    version: int = Field(..., ge=1, description="Translation version number")
    translated_text: str = Field(..., min_length=1, description="Translated text")
    translator_notes: Optional[str] = Field(None, description="Translator's notes")
    translator_type: TranslatorType = Field(..., description="Type of translator")
    translator_info: Optional[str] = Field(None, max_length=500, description="Additional translator information")
    quality_score: Optional[str] = Field(None, max_length=10, description="Quality score")
    license: str = Field(..., max_length=100, description="License for the translation")
    is_published: bool = Field(True, description="Whether the translation is published")

    @validator('target_language')
    def validate_language_code(cls, v):
        """Basic validation for language code format."""
        if len(v) < 2 or len(v) > 10:
            raise ValueError('Language code must be between 2 and 10 characters')
        return v.lower()

    @validator('quality_score')
    def validate_quality_score(cls, v):
        """Validate quality score format."""
        if v is not None:
            # Allow simple numeric scores or descriptive values
            valid_scores = ['high', 'medium', 'low', 'excellent', 'good', 'fair', 'poor']
            if v not in valid_scores:
                # Check if it's a simple numeric value
                try:
                    float(v)
                    if not (0 <= float(v) <= 10):
                        raise ValueError('Quality score must be between 0 and 10')
                except ValueError:
                    raise ValueError('Quality score must be a number (0-10) or descriptive value')
        return v


class TranslationCreate(TranslationBase):
    """Schema for creating a new translation."""
    poem_id: str = Field(..., description="ID of the parent poem")


class TranslationUpdate(BaseModel):
    """Schema for updating an existing translation."""
    target_language: Optional[str] = Field(None, min_length=2, max_length=10)
    version: Optional[int] = Field(None, ge=1)
    translated_text: Optional[str] = Field(None, min_length=1)
    translator_notes: Optional[str] = None
    translator_type: Optional[TranslatorType] = None
    translator_info: Optional[str] = Field(None, max_length=500)
    quality_score: Optional[str] = Field(None, max_length=10)
    license: Optional[str] = Field(None, max_length=100)
    is_published: Optional[bool] = None

    @validator('target_language')
    def validate_language_code(cls, v):
        """Basic validation for language code format."""
        if v is not None:
            if len(v) < 2 or len(v) > 10:
                raise ValueError('Language code must be between 2 and 10 characters')
            return v.lower()
        return v


class TranslationResponse(TranslationBase):
    """Schema for translation response data."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the translation")
    poem_id: str = Field(..., description="ID of the parent poem")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    poem_title: Optional[str] = Field(None, description="Title of the parent poem")
    poet_name: Optional[str] = Field(None, description="Name of the poet")


# ==============================
# AI Log Schemas
# ==============================

class AiLogBase(BaseModel):
    """Base schema for AI log data."""
    workflow_mode: WorkflowMode = Field(..., description="Translation workflow mode")
    provider: str = Field(..., max_length=100, description="AI provider name")
    model_name: str = Field(..., max_length=100, description="AI model name")
    temperature: str = Field(..., max_length=10, description="Temperature setting")
    prompt_tokens: Optional[int] = Field(None, ge=0, description="Number of prompt tokens used")
    completion_tokens: Optional[int] = Field(None, ge=0, description="Number of completion tokens used")
    total_tokens: Optional[int] = Field(None, ge=0, description="Total tokens used")
    cost: Optional[str] = Field(None, max_length=20, description="Cost of the API call")
    duration_seconds: Optional[str] = Field(None, max_length=20, description="Duration in seconds")
    status: AiLogStatus = Field(..., description="Status of the AI operation")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    raw_response: Optional[str] = Field(None, description="Raw AI response")

    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature format."""
        try:
            temp_val = float(v)
            if not (0.0 <= temp_val <= 2.0):
                raise ValueError('Temperature must be between 0.0 and 2.0')
        except ValueError:
            raise ValueError('Temperature must be a valid number')
        return v


class AiLogCreate(AiLogBase):
    """Schema for creating a new AI log."""
    poem_id: str = Field(..., description="ID of the associated poem")
    translation_id: Optional[str] = Field(None, description="ID of the associated translation")


class AiLogUpdate(BaseModel):
    """Schema for updating an existing AI log."""
    workflow_mode: Optional[WorkflowMode] = Field(None, description="Translation workflow mode")
    provider: Optional[str] = Field(None, max_length=100, description="AI provider name")
    model_name: Optional[str] = Field(None, max_length=100, description="AI model name")
    temperature: Optional[str] = Field(None, max_length=10, description="Temperature setting")
    prompt_tokens: Optional[str] = Field(None, max_length=20, description="Number of prompt tokens")
    completion_tokens: Optional[str] = Field(None, max_length=20, description="Number of completion tokens")
    total_tokens: Optional[str] = Field(None, max_length=20, description="Total number of tokens")
    cost: Optional[str] = Field(None, max_length=20, description="Cost of the API call")
    duration_seconds: Optional[str] = Field(None, max_length=20, description="Duration in seconds")
    status: Optional[AiLogStatus] = Field(None, description="Status of the AI operation")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    raw_response: Optional[str] = Field(None, description="Raw AI response")

    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature format."""
        if v is not None:
            try:
                temp_val = float(v)
                if not (0.0 <= temp_val <= 2.0):
                    raise ValueError('Temperature must be between 0.0 and 2.0')
            except ValueError:
                raise ValueError('Temperature must be a valid number')
        return v


class AiLogResponse(AiLogBase):
    """Schema for AI log response data."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the AI log")
    poem_id: str = Field(..., description="ID of the associated poem")
    translation_id: Optional[str] = Field(None, description="ID of the associated translation")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ==============================
# Human Note Schemas
# ==============================

class HumanNoteBase(BaseModel):
    """Base schema for human note data."""
    note_type: str = Field(..., max_length=50, description="Type of note (e.g., 'editorial', 'cultural', 'technical')")
    content: str = Field(..., min_length=1, description="Note content")
    author_name: str = Field(..., max_length=255, description="Name of the note author")
    is_public: bool = Field(True, description="Whether the note is public")

    @validator('note_type')
    def validate_note_type(cls, v):
        """Validate note type."""
        valid_types = ['editorial', 'cultural', 'technical', 'historical', 'linguistic', 'general']
        if v.lower() not in valid_types:
            raise ValueError(f'Note type must be one of: {", ".join(valid_types)}')
        return v.lower()


class HumanNoteCreate(HumanNoteBase):
    """Schema for creating a new human note."""
    poem_id: str = Field(..., description="ID of the associated poem")
    translation_id: Optional[str] = Field(None, description="ID of the associated translation")


class HumanNoteUpdate(BaseModel):
    """Schema for updating an existing human note."""
    note_type: Optional[str] = Field(None, max_length=50)
    content: Optional[str] = Field(None, min_length=1)
    author_name: Optional[str] = Field(None, max_length=255)
    is_public: Optional[bool] = None

    @validator('note_type')
    def validate_note_type(cls, v):
        """Validate note type."""
        if v is not None:
            valid_types = ['editorial', 'cultural', 'technical', 'historical', 'linguistic', 'general']
            if v.lower() not in valid_types:
                raise ValueError(f'Note type must be one of: {", ".join(valid_types)}')
            return v.lower()
        return v


class HumanNoteResponse(HumanNoteBase):
    """Schema for human note response data."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique identifier for the human note")
    poem_id: str = Field(..., description="ID of the associated poem")
    translation_id: Optional[str] = Field(None, description="ID of the associated translation")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ==============================
# Collection Schemas
# ==============================

class PoemListResponse(BaseModel):
    """Schema for poem list response."""
    poems: List[PoemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class TranslationListResponse(BaseModel):
    """Schema for translation list response."""
    translations: List[TranslationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AiLogListResponse(BaseModel):
    """Schema for AI log list response."""
    ai_logs: List[AiLogResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class HumanNoteListResponse(BaseModel):
    """Schema for human note list response."""
    human_notes: List[HumanNoteResponse]
    total: int
    page: int
    per_page: int
    total_pages: int