"""
VPSWeb Repository Pydantic Schemas v0.3.1

Pydantic models for data validation and serialization.
Defines schemas for poems, translations, AI logs, and human notes.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic_core import ValidationError
import re


class TranslatorType(str, Enum):
    """Enum for translator types"""

    AI = "ai"
    HUMAN = "human"


class WorkflowMode(str, Enum):
    """Enum for workflow modes"""

    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


# Poem schemas
class PoemBase(BaseSchema):
    """Base poem schema with enhanced validation"""

    poet_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the poet",
        examples=["陶渊明", "William Shakespeare", "李白"],
    )
    poem_title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Title of the poem",
        examples=["歸園田居", "Sonnet 18", "靜夜思"],
    )
    source_language: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Source language code (BCP-47)",
        examples=["zh", "en", "fr", "es"],
    )
    original_text: str = Field(
        ...,
        min_length=10,
        description="Original poem text (minimum 10 characters)",
        examples=[
            "採菊東籬下，悠然見南山。",
            "Shall I compare thee to a summer's day?",
        ],
    )
    metadata_json: Optional[str] = Field(
        None,
        max_length=5000,
        description="Optional metadata as JSON string (max 5000 characters)",
    )

    @field_validator("poet_name")
    @classmethod
    def validate_poet_name(cls, v: str) -> str:
        """Validate poet name format"""
        if not v or not v.strip():
            raise ValueError("Poet name cannot be empty")

        v = v.strip()

        # Check for reasonable length and characters
        if len(v) < 1:
            raise ValueError("Poet name must be at least 1 character long")

        # Allow letters, spaces, hyphens, and common punctuation
        if not re.match(r"^[\w\s\-\.\,\'\'\u4e00-\u9fff]+$", v):
            raise ValueError("Poet name contains invalid characters")

        return v

    @field_validator("poem_title")
    @classmethod
    def validate_poem_title(cls, v: str) -> str:
        """Validate poem title format"""
        if not v or not v.strip():
            raise ValueError("Poem title cannot be empty")

        v = v.strip()

        if len(v) < 1:
            raise ValueError("Poem title must be at least 1 character long")

        # Allow letters, numbers, spaces, and common punctuation
        if not re.match(r"^[\w\s\-\.\,\!\?\:\;\'\"()\u4e00-\u9fff]+$", v):
            raise ValueError("Poem title contains invalid characters")

        return v

    @field_validator("source_language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        """Enhanced language code validation"""
        if not v or len(v.strip()) < 2:
            raise ValueError("Language code must be at least 2 characters")

        v = v.strip().lower()

        # Validate BCP-47 format (simplified)
        if not re.match(r"^[a-z]{2}(-[A-Z]{2})?(-[a-z]{3})?$", v):
            # Allow common language codes even if not strictly BCP-47
            if not re.match(r"^[a-z]{2,3}(-[A-Z]{2})?$", v):
                raise ValueError(
                    'Language code must be in valid format (e.g., "en", "zh-CN")'
                )

        return v

    @field_validator("original_text")
    @classmethod
    def validate_original_text(cls, v: str) -> str:
        """Validate original poem text"""
        if not v or not v.strip():
            raise ValueError("Original text cannot be empty")

        v = v.strip()

        if len(v) < 10:
            raise ValueError("Original text must be at least 10 characters long")

        # Check for reasonable content (not just whitespace or punctuation)
        if len(re.sub(r'[\s\-\.\,\!\?\:\;\'\"()（）。，！？：；""' "]+", "", v)) < 5:
            raise ValueError("Original text must contain meaningful content")

        return v

    @field_validator("metadata_json")
    @classmethod
    def validate_metadata_json(cls, v: Optional[str]) -> Optional[str]:
        """Validate metadata JSON format"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Basic JSON format validation
        if not (v.startswith("{") and v.endswith("}")):
            raise ValueError("Metadata must be valid JSON format")

        return v


class PoemCreate(PoemBase):
    """Schema for creating a new poem"""

    pass


class PoemUpdate(BaseSchema):
    """Schema for updating an existing poem"""

    poet_name: Optional[str] = Field(None, min_length=1, max_length=200)
    poem_title: Optional[str] = Field(None, min_length=1, max_length=300)
    source_language: Optional[str] = Field(None, min_length=2, max_length=10)
    original_text: Optional[str] = Field(None, min_length=1)
    metadata_json: Optional[str] = None


class PoemResponse(PoemBase):
    """Schema for poem response"""

    id: str = Field(..., description="Poem ID (ULID)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    translation_count: Optional[int] = Field(0, description="Number of translations")


class PoemList(BaseSchema):
    """Schema for poem list response"""

    poems: List[PoemResponse] = Field(default_factory=list, description="List of poems")
    total: int = Field(..., description="Total number of poems")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Number of items per page")


# Translation schemas
class TranslationBase(BaseSchema):
    """Base translation schema with enhanced validation"""

    translator_type: TranslatorType = Field(
        ...,
        description="Type of translator",
        examples=[TranslatorType.AI, TranslatorType.HUMAN],
    )
    translator_info: Optional[str] = Field(
        None,
        max_length=200,
        description="Translator information (model name, person name, etc.)",
        examples=["gpt-4", "Claude-3.5", "王晓明"],
    )
    target_language: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Target language code (BCP-47)",
        examples=["en", "zh", "fr", "es"],
    )
    translated_text: str = Field(
        ...,
        min_length=10,
        description="Translated text (minimum 10 characters)",
        examples=[
            "Picking chrysanthemums by the eastern fence, I calmly see the Southern Mountain."
        ],
    )
    quality_rating: Optional[int] = Field(
        None, ge=1, le=5, description="Quality rating (1=Poor, 5=Excellent)"
    )
    raw_path: Optional[str] = Field(
        None, max_length=500, description="Path to raw output file"
    )

    @field_validator("translator_info")
    @classmethod
    def validate_translator_info(cls, v: Optional[str]) -> Optional[str]:
        """Validate translator information"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) < 1:
            raise ValueError(
                "Translator info must be at least 1 character long if provided"
            )

        # Allow letters, numbers, spaces, hyphens, dots, and common punctuation
        if not re.match(r"^[\w\s\-\.\,\(\)\[\]\u4e00-\u9fff]+$", v):
            raise ValueError("Translator info contains invalid characters")

        return v

    @field_validator("target_language")
    @classmethod
    def validate_target_language(cls, v: str) -> str:
        """Enhanced target language code validation"""
        if not v or len(v.strip()) < 2:
            raise ValueError("Target language code must be at least 2 characters")

        v = v.strip().lower()

        # Same validation as source_language
        if not re.match(r"^[a-z]{2}(-[A-Z]{2})?(-[a-z]{3})?$", v):
            if not re.match(r"^[a-z]{2,3}(-[A-Z]{2})?$", v):
                raise ValueError(
                    'Target language code must be in valid format (e.g., "en", "zh-CN")'
                )

        return v

    @field_validator("translated_text")
    @classmethod
    def validate_translated_text(cls, v: str) -> str:
        """Validate translated text content"""
        if not v or not v.strip():
            raise ValueError("Translated text cannot be empty")

        v = v.strip()

        if len(v) < 10:
            raise ValueError("Translated text must be at least 10 characters long")

        # Check for reasonable content
        if len(re.sub(r'[\s\-\.\,\!\?\:\;\'\"()（）。，！？：；""' "]+", "", v)) < 5:
            raise ValueError("Translated text must contain meaningful content")

        return v

    @field_validator("raw_path")
    @classmethod
    def validate_raw_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate raw file path"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Basic path validation - prevent directory traversal
        if ".." in v:
            raise ValueError("Path cannot contain directory traversal")

        # Check for valid file extensions
        valid_extensions = [".txt", ".json", ".md", ".log"]
        if not any(v.lower().endswith(ext) for ext in valid_extensions):
            raise ValueError(
                f'Path must have valid file extension: {", ".join(valid_extensions)}'
            )

        return v


class TranslationCreate(TranslationBase):
    """Schema for creating a new translation"""

    poem_id: str = Field(
        ..., min_length=1, max_length=50, description="ID of the parent poem"
    )

    @model_validator(mode="after")
    def validate_translation_consistency(self) -> "TranslationCreate":
        """Validate consistency between translator_type and translator_info"""
        # If translator_type is AI, translator_info should be a model name
        if self.translator_type == TranslatorType.AI and self.translator_info:
            # Check if it looks like a model name
            model_patterns = ["gpt", "claude", "gemini", "deepseek", "qwen", "llama"]
            if not any(
                pattern.lower() in self.translator_info.lower()
                for pattern in model_patterns
            ):
                # This is just a warning, not an error, as AI models can vary
                pass

        # If translator_type is HUMAN, translator_info should be a person's name
        if self.translator_type == TranslatorType.HUMAN and self.translator_info:
            # Basic check for human name format
            if len(self.translator_info) < 2 or len(self.translator_info) > 100:
                raise ValueError(
                    "Human translator name must be between 2 and 100 characters"
                )

        return self


class TranslationUpdate(BaseSchema):
    """Schema for updating an existing translation"""

    translator_type: Optional[TranslatorType] = None
    translator_info: Optional[str] = Field(None, max_length=200)
    target_language: Optional[str] = Field(None, min_length=2, max_length=10)
    translated_text: Optional[str] = Field(None, min_length=1)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    raw_path: Optional[str] = None


class TranslationResponse(TranslationBase):
    """Schema for translation response"""

    id: str = Field(..., description="Translation ID (ULID)")
    poem_id: str = Field(..., description="ID of the parent poem")
    created_at: datetime = Field(..., description="Creation timestamp")


class TranslationList(BaseSchema):
    """Schema for translation list response"""

    translations: List[TranslationResponse] = Field(
        default_factory=list, description="List of translations"
    )
    total: int = Field(..., description="Total number of translations")
    poem_id: str = Field(..., description="Parent poem ID")


# AI Log schemas
class AILogBase(BaseSchema):
    """Base AI log schema with enhanced validation"""

    model_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="AI model name",
        examples=["gpt-4", "claude-3-sonnet", "deepseek-reasoner"],
    )
    workflow_mode: WorkflowMode = Field(
        ...,
        description="Translation workflow mode used",
        examples=[
            WorkflowMode.REASONING,
            WorkflowMode.NON_REASONING,
            WorkflowMode.HYBRID,
        ],
    )
    token_usage_json: Optional[str] = Field(
        None, max_length=2000, description="Token usage data as JSON string"
    )
    cost_info_json: Optional[str] = Field(
        None, max_length=1000, description="Cost information as JSON string"
    )
    runtime_seconds: Optional[float] = Field(
        None,
        ge=0,
        le=3600,  # Max 1 hour runtime
        description="Translation runtime in seconds (0-3600)",
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional notes about the translation process",
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate AI model name"""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")

        v = v.strip()

        if len(v) < 1:
            raise ValueError("Model name must be at least 1 character long")

        # Allow letters, numbers, hyphens, and dots in model names
        if not re.match(r"^[a-zA-Z0-9\-\.\u4e00-\u9fff]+$", v):
            raise ValueError("Model name contains invalid characters")

        return v

    @field_validator("runtime_seconds")
    @classmethod
    def validate_runtime_seconds(cls, v: Optional[float]) -> Optional[float]:
        """Validate runtime seconds"""
        if v is None:
            return None

        if v < 0:
            raise ValueError("Runtime cannot be negative")

        if v > 3600:  # 1 hour max
            raise ValueError("Runtime cannot exceed 1 hour (3600 seconds)")

        # Round to 3 decimal places for consistency
        return round(v, 3)

    @field_validator("token_usage_json")
    @classmethod
    def validate_token_usage_json(cls, v: Optional[str]) -> Optional[str]:
        """Validate token usage JSON format"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Basic JSON validation
        if not (v.startswith("{") and v.endswith("}")):
            raise ValueError("Token usage must be valid JSON format")

        # Could add more sophisticated JSON parsing here if needed
        try:
            import json

            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("Token usage JSON is not valid")

        return v

    @field_validator("cost_info_json")
    @classmethod
    def validate_cost_info_json(cls, v: Optional[str]) -> Optional[str]:
        """Validate cost info JSON format"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        # Basic JSON validation
        if not (v.startswith("{") and v.endswith("}")):
            raise ValueError("Cost info must be valid JSON format")

        try:
            import json

            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("Cost info JSON is not valid")

        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes content"""
        if v is None:
            return None

        v = v.strip()
        if not v:
            return None

        if len(v) < 1:
            raise ValueError("Notes must contain content if provided")

        return v


class AILogCreate(AILogBase):
    """Schema for creating a new AI log"""

    translation_id: str = Field(
        ..., min_length=1, max_length=50, description="ID of the parent translation"
    )

    @model_validator(mode="after")
    def validate_ai_log_consistency(self) -> "AILogCreate":
        """Validate AI log data consistency"""
        # If workflow_mode is reasoning, runtime should typically be longer
        if self.workflow_mode == WorkflowMode.REASONING and self.runtime_seconds:
            if self.runtime_seconds < 5:  # Reasoning usually takes at least 5 seconds
                pass  # Just a note, not an error

        # If token_usage is provided, it should be reasonable
        if self.token_usage_json:
            try:
                import json

                usage_data = json.loads(self.token_usage_json)
                # Basic sanity checks
                if isinstance(usage_data, dict):
                    if (
                        "total_tokens" in usage_data
                        and usage_data["total_tokens"] > 100000
                    ):
                        pass  # Very high token usage, but allowed
                    if (
                        "prompt_tokens" in usage_data
                        and usage_data["prompt_tokens"] < 1
                    ):
                        raise ValueError("Prompt tokens must be at least 1")
            except json.JSONDecodeError:
                # This is already validated in field validator, but keep as backup
                raise ValueError("Invalid JSON format in token_usage_json")

        return self


class AILogResponse(AILogBase):
    """Schema for AI log response"""

    id: str = Field(..., description="AI log ID (ULID)")
    translation_id: str = Field(..., description="ID of the parent translation")
    created_at: datetime = Field(..., description="Creation timestamp")


# Human Note schemas
class HumanNoteBase(BaseSchema):
    """Base human note schema with enhanced validation"""

    note_text: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Human note text (minimum 5 characters)",
        examples=[
            "This translation captures the poetic essence well.",
            "Consider alternative wording for the second line.",
        ],
    )

    @field_validator("note_text")
    @classmethod
    def validate_note_text(cls, v: str) -> str:
        """Validate human note content"""
        if not v or not v.strip():
            raise ValueError("Note text cannot be empty")

        v = v.strip()

        if len(v) < 5:
            raise ValueError("Note text must be at least 5 characters long")

        # Check for meaningful content
        if len(re.sub(r'[\s\-\.\,\!\?\:\;\'\"()（）。，！？：；""' "]+", "", v)) < 3:
            raise ValueError("Note text must contain meaningful content")

        return v


class HumanNoteCreate(HumanNoteBase):
    """Schema for creating a new human note"""

    translation_id: str = Field(..., description="ID of the parent translation")


class HumanNoteResponse(HumanNoteBase):
    """Schema for human note response"""

    id: str = Field(..., description="Human note ID (ULID)")
    translation_id: str = Field(..., description="ID of the parent translation")
    created_at: datetime = Field(..., description="Creation timestamp")


# Translation workflow schemas
class TranslationRequest(BaseSchema):
    """Schema for translation workflow request"""

    poem_id: str = Field(..., description="ID of the poem to translate")
    target_language: str = Field(
        ..., min_length=2, max_length=10, description="Target language"
    )
    workflow_mode: WorkflowMode = Field(
        WorkflowMode.HYBRID, description="Translation workflow mode"
    )
    model_override: Optional[str] = Field(
        None, max_length=100, description="Override AI model"
    )


class TranslationResponse(BaseSchema):
    """Schema for translation workflow response"""

    translation_id: str = Field(..., description="ID of the created translation")
    translated_text: str = Field(..., description="The translated text")
    model_name: str = Field(..., description="AI model used")
    runtime_seconds: Optional[float] = Field(None, description="Translation runtime")
    token_usage: Optional[Dict[str, Any]] = Field(
        None, description="Token usage details"
    )


# Comparison schemas
class ComparisonView(BaseSchema):
    """Schema for comparison view data"""

    poem: PoemResponse = Field(..., description="Poem information")
    translations: List[TranslationResponse] = Field(
        ..., description="All translations for the poem"
    )
    ai_logs: List[AILogResponse] = Field(
        default_factory=list, description="AI logs for translations"
    )
    human_notes: List[HumanNoteResponse] = Field(
        default_factory=list, description="Human notes for translations"
    )


# Statistics schemas
class RepositoryStats(BaseSchema):
    """Schema for repository statistics"""

    total_poems: int = Field(..., ge=0, description="Total number of poems")
    total_translations: int = Field(
        ..., ge=0, description="Total number of translations"
    )
    ai_translations: int = Field(..., ge=0, description="Number of AI translations")
    human_translations: int = Field(
        ..., ge=0, description="Number of human translations"
    )
    languages: List[str] = Field(
        default_factory=list, description="Languages in repository"
    )
    latest_translation: Optional[datetime] = Field(
        None, description="Latest translation timestamp"
    )


# Workflow Task schemas
class TaskStatus(str, Enum):
    """Enum for task status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowTaskCreate(BaseSchema):
    """Schema for creating workflow tasks"""

    poem_id: str = Field(..., description="ID of the poem to translate")
    source_lang: str = Field(
        ..., min_length=2, max_length=10, description="Source language code"
    )
    target_lang: str = Field(
        ..., min_length=2, max_length=10, description="Target language code"
    )
    workflow_mode: WorkflowMode = Field(..., description="Translation workflow mode")


class WorkflowTaskUpdate(BaseSchema):
    """Schema for updating workflow tasks"""

    status: Optional[TaskStatus] = Field(None, description="Task status")
    progress_percentage: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    result_json: Optional[str] = Field(None, description="Task result data as JSON")
    error_message: Optional[str] = Field(
        None, description="Error message if task failed"
    )
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")


class WorkflowTaskResponse(BaseSchema):
    """Schema for workflow task responses"""

    id: str = Field(..., description="Task ID")
    poem_id: str = Field(..., description="ID of the poem being translated")
    source_lang: str = Field(..., description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    workflow_mode: WorkflowMode = Field(..., description="Translation workflow mode")
    status: TaskStatus = Field(..., description="Current task status")
    progress_percentage: int = Field(..., description="Progress percentage (0-100)")
    result_json: Optional[str] = Field(None, description="Task result data as JSON")
    error_message: Optional[str] = Field(
        None, description="Error message if task failed"
    )
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    created_at: datetime = Field(..., description="Task creation time")
    updated_at: datetime = Field(..., description="Last update time")

    # Computed properties
    is_running: bool = Field(..., description="Whether task is currently running")
    is_completed: bool = Field(..., description="Whether task has completed")
    duration_seconds: Optional[int] = Field(
        None, description="Task duration in seconds"
    )


class WorkflowTaskStatusUpdate(BaseSchema):
    """Schema for updating task status"""

    status: TaskStatus = Field(..., description="New task status")
    progress_percentage: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage (0-100)"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if status is failed"
    )


class WorkflowTaskResult(BaseSchema):
    """Schema for task completion result"""

    translation_id: str = Field(..., description="ID of the created translation")
    workflow_id: str = Field(..., description="VPSWeb workflow execution ID")
    total_tokens: int = Field(..., description="Total tokens used")
    duration_seconds: int = Field(..., description="Translation duration in seconds")
    total_cost: float = Field(..., description="Total cost of translation")


# Response wrappers
class APIResponse(BaseSchema):
    """Generic API response wrapper"""

    success: bool = Field(True, description="Request success status")
    message: str = Field(
        "Operation completed successfully", description="Response message"
    )
    data: Optional[Any] = Field(None, description="Response data")


class ErrorResponse(BaseSchema):
    """Schema for error responses"""

    success: bool = Field(False, description="Request success status")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
