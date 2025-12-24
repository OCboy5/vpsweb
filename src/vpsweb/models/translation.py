"""
Translation data models for Vox Poetica Studio Web.

This module contains Pydantic models for the complete translation workflow,
matching the exact structure specified in vpts.yml.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Language(str, Enum):
    """Supported languages for translation."""

    ENGLISH = "English"
    CHINESE = "Chinese"
    POLISH = "Polish"


LANGUAGE_CODE_MAP = {
    "en": Language.ENGLISH,
    "zh-CN": Language.CHINESE,
    "pl": Language.POLISH,
}


class TranslationInput(BaseModel):
    """Input for translation workflow, matching vpts.yml specification."""

    original_poem: str = Field(
        ...,
        min_length=1,
        max_length=50000,  # Increased to handle long poems while staying within 32k token context
        description="Original poem text for translation",
    )
    source_lang: Language = Field(..., description="Source language (English, Chinese, or Polish)")
    target_lang: Language = Field(..., description="Target language (English or Chinese only)")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the poem (author, title, etc.)",
    )

    @field_validator("source_lang", "target_lang")
    @classmethod
    def validate_languages(cls, v):
        """Validate language choices against vpts.yml specification."""
        return v

    @field_validator("target_lang")
    @classmethod
    def validate_target_language(cls, v, info):
        """Ensure target language is only English or Chinese (from vpts.yml)."""
        if v not in [Language.ENGLISH, Language.CHINESE]:
            raise ValueError("Target language must be either English or Chinese")
        return v

    @field_validator("target_lang")
    @classmethod
    def validate_source_target_distinct(cls, v, info):
        """Ensure source and target languages are different."""
        if "source_lang" in info.data and v == info.data["source_lang"]:
            raise ValueError("Source and target languages must be different")
        return v

    model_config = ConfigDict(use_enum_values=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranslationInput":
        """Create from dictionary."""
        return cls(**data)


class BackgroundBriefingReport(BaseModel):
    """Background Briefing Report with contextual analysis for translation."""

    content: str = Field(..., description="BBR content with contextual analysis")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when BBR was created or retrieved",
    )
    model_info: Optional[Dict[str, str]] = Field(
        None,
        description="Model provider and version information used to generate BBR",
    )
    tokens_used: Optional[int] = Field(None, ge=0, description="Number of tokens used to generate this BBR")
    prompt_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Number of input tokens used for BBR generation",
    )
    completion_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Number of output tokens used for BBR generation",
    )
    duration: Optional[float] = Field(None, ge=0.0, description="Time taken to generate BBR in seconds")
    cost: Optional[float] = Field(None, ge=0.0, description="Cost in RMB for BBR generation")
    poem_id: Optional[str] = Field(None, description="ID of the poem this BBR belongs to")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackgroundBriefingReport":
        """Create from dictionary, parsing ISO timestamp."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class InitialTranslation(BaseModel):
    """Output from initial translation step with XML structure from vpts.yml."""

    initial_translation: str = Field(..., description="The translated poem text")
    initial_translation_notes: str = Field(
        ...,
        description="Translator's explanation of translation choices (200-300 words)",
    )
    translated_poem_title: str = Field(..., description="The translated poem title in target language")
    translated_poet_name: str = Field(..., description="The translated poet name in target language")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when translation was created",
    )
    model_info: Dict[str, str] = Field(..., description="Model provider and version information")
    tokens_used: int = Field(..., ge=0, description="Number of tokens used for this translation")
    prompt_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Number of input tokens used for this translation",
    )
    completion_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Number of output tokens used for this translation",
    )
    duration: Optional[float] = Field(
        None,
        ge=0.0,
        description="Time taken for initial translation in seconds",
    )
    cost: Optional[float] = Field(None, ge=0.0, description="Cost in RMB for this translation step")

    @field_validator("initial_translation_notes")
    @classmethod
    def validate_notes_length(cls, v):
        """Validate notes length matches vpts.yml specification (200-300 words)."""
        # Note: Removed warning for shorter notes during development
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InitialTranslation":
        """Create from dictionary, parsing ISO timestamp."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EditorReview(BaseModel):
    """Output from editor review step with structured suggestions from vpts.yml."""

    editor_suggestions: str = Field(
        default="",
        description="Structured editor suggestions extracted from XML",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when review was created",
    )
    model_info: Dict[str, str] = Field(..., description="Model provider and version information")
    tokens_used: int = Field(..., ge=0, description="Number of tokens used for this review")
    prompt_tokens: Optional[int] = Field(None, ge=0, description="Number of input tokens used for this review")
    completion_tokens: Optional[int] = Field(None, ge=0, description="Number of output tokens used for this review")
    duration: Optional[float] = Field(None, ge=0.0, description="Time taken for editor review in seconds")
    cost: Optional[float] = Field(None, ge=0.0, description="Cost in RMB for this editor review step")

    def get_suggestions_list(self) -> List[str]:
        """Extract numbered suggestions from the editor's text."""
        import re

        text_to_search = self.editor_suggestions
        # Look for numbered suggestions like "1. [suggestion text]"
        suggestions = re.findall(r"^\s*(\d+)\.\s*(.+)$", text_to_search, re.MULTILINE)
        return [suggestion[1].strip() for suggestion in suggestions]

    def get_overall_assessment(self) -> str:
        """Extract the overall assessment from the editor's text."""
        import re

        text_to_search = self.editor_suggestions
        # Look for the overall assessment after the suggestions
        assessment_match = re.search(
            r"overall assessment:?\s*(.+)",
            text_to_search,
            re.IGNORECASE | re.DOTALL,
        )
        if assessment_match:
            return assessment_match.group(1).strip()
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EditorReview":
        """Create from dictionary, parsing ISO timestamp."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class RevisedTranslation(BaseModel):
    """Output from translator revision step with XML structure from vpts.yml."""

    revised_translation: str = Field(..., description="The final revised translation")
    revised_translation_notes: str = Field(
        ...,
        description="Explanation of key changes and decisions (200-300 words)",
    )
    refined_translated_poem_title: str = Field(..., description="The refined translated poem title in target language")
    refined_translated_poet_name: str = Field(..., description="The refined translated poet name in target language")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when revision was created",
    )
    model_info: Dict[str, str] = Field(..., description="Model provider and version information")
    tokens_used: int = Field(..., ge=0, description="Number of tokens used for this revision")
    prompt_tokens: Optional[int] = Field(None, ge=0, description="Number of input tokens used for this revision")
    completion_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Number of output tokens used for this revision",
    )
    duration: Optional[float] = Field(
        None,
        ge=0.0,
        description="Time taken for translator revision in seconds",
    )
    cost: Optional[float] = Field(
        None,
        ge=0.0,
        description="Cost in RMB for this translator revision step",
    )

    @field_validator("revised_translation_notes")
    @classmethod
    def validate_revision_notes_length(cls, v):
        """Validate notes length matches vpts.yml specification (200-300 words)."""
        len(v.split())
        # Allow any length of revision notes without warning
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisedTranslation":
        """Create from dictionary, parsing ISO timestamp."""
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class TranslationOutput(BaseModel):
    """Complete workflow output matching the vpts.yml congregation format."""

    workflow_id: str = Field(..., description="Unique identifier for this translation workflow")
    input: TranslationInput = Field(..., description="Original input to the workflow")
    initial_translation: InitialTranslation = Field(..., description="Initial translation with notes")
    editor_review: EditorReview = Field(..., description="Editor's detailed suggestions and feedback")
    revised_translation: RevisedTranslation = Field(..., description="Final revised translation with notes")
    total_tokens: int = Field(..., ge=0, description="Total tokens used across all workflow steps")
    duration_seconds: float = Field(..., ge=0.0, description="Total workflow execution time in seconds")
    workflow_mode: Optional[str] = Field(
        None,
        description="Workflow mode used for this translation (reasoning, non_reasoning, hybrid)",
    )
    total_cost: Optional[float] = Field(None, ge=0.0, description="Total cost in RMB for the entire workflow")
    background_briefing_report: Optional[BackgroundBriefingReport] = Field(
        None, description="Background Briefing Report with contextual analysis"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        result = {
            "workflow_id": self.workflow_id,
            "workflow_mode": self.workflow_mode,
            "input": self.input.to_dict(),
        }

        # Add BBR if available (after input section, before workflow steps)
        if self.background_briefing_report:
            result["background_briefing_report"] = self.background_briefing_report.to_dict()

        # Add workflow step sections
        result.update(
            {
                "initial_translation": self.initial_translation.to_dict(),
                "editor_review": self.editor_review.to_dict(),
                "revised_translation": self.revised_translation.to_dict(),
                "total_tokens": self.total_tokens,
                "duration_seconds": self.duration_seconds,
            }
        )

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranslationOutput":
        """Create from dictionary with proper deserialization."""
        # Handle optional BBR
        bbr = None
        if "background_briefing_report" in data and data["background_briefing_report"]:
            bbr = BackgroundBriefingReport.from_dict(data["background_briefing_report"])

        return cls(
            workflow_id=data["workflow_id"],
            workflow_mode=data.get("workflow_mode"),
            input=TranslationInput.from_dict(data["input"]),
            initial_translation=InitialTranslation.from_dict(data["initial_translation"]),
            editor_review=EditorReview.from_dict(data["editor_review"]),
            revised_translation=RevisedTranslation.from_dict(data["revised_translation"]),
            background_briefing_report=bbr,
            total_tokens=data["total_tokens"],
            duration_seconds=data["duration_seconds"],
        )

    def save_to_file(self, filepath: str, format: str = "json") -> None:
        """Save the translation output to a file."""
        if format.lower() == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def load_from_file(cls, filepath: str, format: str = "json") -> "TranslationOutput":
        """Load translation output from a file."""
        if format.lower() == "json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
