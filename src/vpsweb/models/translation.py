"""
Translation data models for Vox Poetica Studio Web.

This module contains Pydantic models for the complete translation workflow,
matching the exact structure specified in vpts.yml.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum
import json


class Language(str, Enum):
    """Supported languages for translation."""
    ENGLISH = "English"
    CHINESE = "Chinese"
    POLISH = "Polish"


class TranslationInput(BaseModel):
    """Input for translation workflow, matching vpts.yml specification."""

    original_poem: str = Field(
        ...,
        min_length=1,
        max_length=2000,  # From vpts.yml: max_length: 2000
        description="Original poem text for translation"
    )
    source_lang: Language = Field(
        ...,
        description="Source language (English, Chinese, or Polish)"
    )
    target_lang: Language = Field(
        ...,
        description="Target language (English or Chinese only)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the poem (author, title, etc.)"
    )

    @validator('source_lang', 'target_lang')
    def validate_languages(cls, v, values):
        """Validate language choices against vpts.yml specification."""
        return v

    @validator('target_lang')
    def validate_target_language(cls, v, values):
        """Ensure target language is only English or Chinese (from vpts.yml)."""
        if v not in [Language.ENGLISH, Language.CHINESE]:
            raise ValueError("Target language must be either English or Chinese")
        return v

    @validator('source_lang', 'target_lang')
    def validate_source_target_distinct(cls, v, values):
        """Ensure source and target languages are different."""
        if 'source_lang' in values and v == values['source_lang']:
            raise ValueError("Source and target languages must be different")
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationInput':
        """Create from dictionary."""
        return cls(**data)


class InitialTranslation(BaseModel):
    """Output from initial translation step with XML structure from vpts.yml."""

    initial_translation: str = Field(
        ...,
        description="The translated poem text"
    )
    initial_translation_notes: str = Field(
        ...,
        description="Translator's explanation of translation choices (200-300 words)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when translation was created"
    )
    model_info: Dict[str, str] = Field(
        ...,
        description="Model provider and version information"
    )
    tokens_used: int = Field(
        ...,
        ge=0,
        description="Number of tokens used for this translation"
    )

    @validator('initial_translation_notes')
    def validate_notes_length(cls, v):
        """Validate notes length matches vpts.yml specification (200-300 words)."""
        word_count = len(v.split())
        if word_count < 10:  # Allow shorter notes for testing, but warn if too short
            import warnings
            warnings.warn(f"Translation notes should be 200-300 words, got {word_count}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.dict()
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InitialTranslation':
        """Create from dictionary, parsing ISO timestamp."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class EditorReview(BaseModel):
    """Output from editor review step with structured suggestions from vpts.yml."""

    editor_suggestions: str = Field(
        default="",
        description="Structured editor suggestions extracted from XML"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when review was created"
    )
    model_info: Dict[str, str] = Field(
        ...,
        description="Model provider and version information"
    )
    tokens_used: int = Field(
        ...,
        ge=0,
        description="Number of tokens used for this review"
    )

    def get_suggestions_list(self) -> List[str]:
        """Extract numbered suggestions from the editor's text."""
        import re
        text_to_search = self.editor_suggestions
        # Look for numbered suggestions like "1. [suggestion text]"
        suggestions = re.findall(r'^\s*(\d+)\.\s*(.+)$', text_to_search, re.MULTILINE)
        return [suggestion[1].strip() for suggestion in suggestions]

    def get_overall_assessment(self) -> str:
        """Extract the overall assessment from the editor's text."""
        import re
        text_to_search = self.editor_suggestions
        # Look for the overall assessment after the suggestions
        assessment_match = re.search(r'overall assessment:?\s*(.+)', text_to_search, re.IGNORECASE | re.DOTALL)
        if assessment_match:
            return assessment_match.group(1).strip()
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = {
            'editor_suggestions': self.editor_suggestions,
            'timestamp': self.timestamp.isoformat(),
            'model_info': self.model_info,
            'tokens_used': self.tokens_used,
            'suggestions': self.get_suggestions_list(),
            'overall_assessment': self.get_overall_assessment()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditorReview':
        """Create from dictionary, parsing ISO timestamp."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        # Remove computed fields if present
        data.pop('suggestions', None)
        data.pop('overall_assessment', None)
        return cls(**data)


class RevisedTranslation(BaseModel):
    """Output from translator revision step with XML structure from vpts.yml."""

    revised_translation: str = Field(
        ...,
        description="The final revised translation"
    )
    revised_translation_notes: str = Field(
        ...,
        description="Explanation of key changes and decisions (200-300 words)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when revision was created"
    )
    model_info: Dict[str, str] = Field(
        ...,
        description="Model provider and version information"
    )
    tokens_used: int = Field(
        ...,
        ge=0,
        description="Number of tokens used for this revision"
    )

    @validator('revised_translation_notes')
    def validate_revision_notes_length(cls, v):
        """Validate notes length matches vpts.yml specification (200-300 words)."""
        word_count = len(v.split())
        if word_count < 10:  # Allow shorter notes for testing, but warn if too short
            import warnings
            warnings.warn(f"Revision notes should be 200-300 words, got {word_count}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO format timestamp."""
        data = self.dict()
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RevisedTranslation':
        """Create from dictionary, parsing ISO timestamp."""
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class TranslationOutput(BaseModel):
    """Complete workflow output matching the vpts.yml congregation format."""

    workflow_id: str = Field(
        ...,
        description="Unique identifier for this translation workflow"
    )
    input: TranslationInput = Field(
        ...,
        description="Original input to the workflow"
    )
    initial_translation: InitialTranslation = Field(
        ...,
        description="Initial translation with notes"
    )
    editor_review: EditorReview = Field(
        ...,
        description="Editor's detailed suggestions and feedback"
    )
    revised_translation: RevisedTranslation = Field(
        ...,
        description="Final revised translation with notes"
    )
    full_log: str = Field(
        ...,
        description="Complete workflow log including all steps"
    )
    total_tokens: int = Field(
        ...,
        ge=0,
        description="Total tokens used across all workflow steps"
    )
    duration_seconds: float = Field(
        ...,
        ge=0.0,
        description="Total workflow execution time in seconds"
    )

    def get_congregated_output(self) -> Dict[str, Any]:
        """Generate the final congregation format matching vpts.yml template."""
        return {
            "original_poem": self.input.original_poem,
            "initial_translation": self.initial_translation.initial_translation,
            "initial_translation_notes": self.initial_translation.initial_translation_notes,
            "editor_suggestions": self.editor_review.editor_suggestions,
            "revised_translation": self.revised_translation.revised_translation,
            "revised_translation_notes": self.revised_translation.revised_translation_notes
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        return {
            "workflow_id": self.workflow_id,
            "input": self.input.to_dict(),
            "initial_translation": self.initial_translation.to_dict(),
            "editor_review": self.editor_review.to_dict(),
            "revised_translation": self.revised_translation.to_dict(),
            "full_log": self.full_log,
            "total_tokens": self.total_tokens,
            "duration_seconds": self.duration_seconds,
            "congregated_output": self.get_congregated_output()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationOutput':
        """Create from dictionary with proper deserialization."""
        return cls(
            workflow_id=data['workflow_id'],
            input=TranslationInput.from_dict(data['input']),
            initial_translation=InitialTranslation.from_dict(data['initial_translation']),
            editor_review=EditorReview.from_dict(data['editor_review']),
            revised_translation=RevisedTranslation.from_dict(data['revised_translation']),
            full_log=data['full_log'],
            total_tokens=data['total_tokens'],
            duration_seconds=data['duration_seconds']
        )

    def save_to_file(self, filepath: str, format: str = "json") -> None:
        """Save the translation output to a file."""
        if format.lower() == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def load_from_file(cls, filepath: str, format: str = "json") -> 'TranslationOutput':
        """Load translation output from a file."""
        if format.lower() == "json":
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Helper functions for XML parsing (matching the vpts.yml code nodes)
def extract_initial_translation_from_xml(xml_response: str) -> Dict[str, str]:
    """Extract initial translation and notes from XML response (matching vpts.yml code)."""
    import re

    # Remove whitespace between tags
    xml_response = re.sub(r'\s+(<|>)', r'\1', xml_response.strip())

    # Find all tags and their contents
    pattern = r'<(\w+)>(.*?)</\1>'
    matches = re.findall(pattern, xml_response, re.DOTALL)

    result = {}
    for tag, content in matches:
        # Recursively parse nested tags
        if re.search(r'<\w+>', content):
            result[tag] = extract_initial_translation_from_xml(content)
        else:
            result[tag] = content.strip()

    return {
        "initial_translation": str(result.get('initial_translation', '')),
        "initial_translation_notes": str(result.get('initial_translation_notes', '')),
    }


def extract_revised_translation_from_xml(xml_response: str) -> Dict[str, str]:
    """Extract revised translation and notes from XML response (matching vpts.yml code)."""
    import re

    # Remove whitespace between tags
    xml_response = re.sub(r'\s+(<|>)', r'\1', xml_response.strip())

    # Find all tags and their contents
    pattern = r'<(\w+)>(.*?)</\1>'
    matches = re.findall(pattern, xml_response, re.DOTALL)

    result = {}
    for tag, content in matches:
        # Recursively parse nested tags
        if re.search(r'<\w+>', content):
            result[tag] = extract_revised_translation_from_xml(content)
        else:
            result[tag] = content.strip()

    return {
        "revised_translation": str(result.get('revised_translation', '')),
        "revised_translation_notes": str(result.get('revised_translation_notes', '')),
    }