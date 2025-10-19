"""
WeChat article data models for Vox Poetica Studio Web.

This module contains Pydantic models for WeChat article generation and publishing,
including article content, metadata, and API response structures.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from enum import Enum
import re


class WeChatArticleStatus(str, Enum):
    """Status of WeChat article in workflow."""

    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"
    GENERATED = "generated"


class TranslationNotes(BaseModel):
    """Translation notes extracted from workflow for WeChat article."""

    digest: str = Field(
        ...,
        min_length=80,
        max_length=120,
        description="80-120 character summary of translation highlights",
    )
    notes: List[str] = Field(
        ...,
        min_length=1,  # At least one note is required
        description="Translation insights bullet points (number and length determined by LLM based on content)",
    )

    @field_validator("notes")
    @classmethod
    def validate_notes_content(cls, v):
        """Validate notes have reasonable content."""
        if not v:
            raise ValueError("At least one translation note is required")

        # Only check for extremely short/long notes - let LLM decide appropriate length
        for i, note in enumerate(v):
            if len(note.strip()) < 5:
                raise ValueError(f"Note {i+1} is too short (minimum 5 characters)")
            if len(note) > 500:
                raise ValueError(f"Note {i+1} is too long (maximum 500 characters)")
        return v

    def to_html(self) -> str:
        """Convert to HTML bullet list format."""
        return "".join([f"• {note}<br>" for note in self.notes])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"digest": self.digest, "notes": self.notes}


class WeChatArticleMetadata(BaseModel):
    """Metadata for WeChat article generation."""

    # Core poem information
    poem_title: str = Field(..., description="Original poem title")
    poet_name: str = Field(..., description="Original poet name")
    series_index: Optional[str] = Field(
        None, description="Series index (e.g., '其一', '其二')"
    )

    # Translation information
    source_lang: str = Field(..., description="Source language of poem")
    target_lang: str = Field(..., description="Target language of translation")

    # Workflow information
    workflow_id: str = Field(..., description="Original translation workflow ID")
    workflow_mode: Optional[str] = Field(
        None, description="Workflow mode used (reasoning, non_reasoning, hybrid)"
    )

    # File paths
    source_json_path: str = Field(
        ..., description="Path to original translation JSON file"
    )

    # Article information
    slug: str = Field(
        ...,
        description="URL-friendly slug: poetname-poemtitle-YYYYMMDD (supports Chinese characters)",
    )
    author: str = Field(default="知韵VoxPoetica", description="Article author name")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now, description="Article creation timestamp"
    )

    @field_validator("slug")
    @classmethod
    def validate_slug_format(cls, v):
        """Validate slug follows expected format."""
        # Expected format: poetname-poemtitle-YYYYMMDD (allow Chinese characters)
        pattern = r"^[\u4e00-\u9fff\w_-]+-\d{8}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Slug '{v}' does not match expected format 'poetname-poemtitle-YYYYMMDD'"
            )
        return v


class WeChatArticle(BaseModel):
    """WeChat article with content and metadata for publishing."""

    # Core article fields
    title: str = Field(
        ...,
        max_length=60,
        description="Article title (max 64 characters for WeChat API, using 60 for safety)",
    )
    content: str = Field(..., description="WeChat-compatible HTML content")
    digest: str = Field(
        ...,
        max_length=115,
        description="Article summary (max 120 characters for WeChat API, using 115 for safety)",
    )
    author: str = Field(default="知韵VoxPoetica", description="Article author name")

    # Publishing settings (cover image support)
    thumb_media_id: Optional[str] = Field(
        default=None, description="Thumb media_id for cover image"
    )
    show_cover_pic: bool = Field(
        default=False,
        description="Whether to show cover picture; requires thumb_media_id when True",
    )
    cover_image_path: Optional[str] = Field(
        default=None, description="Local path to cover image for uploading to WeChat"
    )
    need_open_comment: bool = Field(
        default=False, description="Whether to enable comments"
    )
    only_fans_can_comment: bool = Field(
        default=False, description="Whether only fans can comment"
    )
    content_source_url: str = Field(
        default="", description="Source URL for original article"
    )

    # Translation-specific metadata
    poem_title: str = Field(..., description="Original poem title")
    poet_name: str = Field(..., description="Original poet name")
    source_lang: str = Field(..., description="Source language of poem")
    target_lang: str = Field(..., description="Target language of translation")
    translation_workflow_id: str = Field(
        ..., description="Original translation workflow ID"
    )
    translation_json_path: str = Field(
        ..., description="Path to original translation JSON file"
    )

    # Translation notes
    translation_notes: Optional[TranslationNotes] = Field(
        None, description="Translation notes generated by LLM"
    )

    @field_validator("title")
    @classmethod
    def validate_title_format(cls, v):
        """Validate title follows expected format."""
        if not v.strip():
            raise ValueError("Title cannot be empty")
        # Check character length for WeChat API compatibility (with safety buffer)
        if len(v) > 60:
            raise ValueError(
                "Title exceeds 60 character limit (64 allowed by WeChat API)"
            )
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_wechat_html(cls, v):
        """Validate content uses WeChat-compatible HTML."""
        # Updated validation for enhanced template - allow necessary tags for proper display
        # Remove style tag from forbidden list since our template uses it for proper styling
        # Keep only truly dangerous tags that WeChat doesn't allow
        forbidden_tags = ["<script", "<iframe", "<object", "<embed"]
        for tag in forbidden_tags:
            if tag.lower() in v.lower():
                raise ValueError(f"Content contains forbidden HTML tag: {tag}")
        return v

    @field_validator("digest")
    @classmethod
    def validate_digest_length(cls, v):
        """Validate digest length for WeChat API compatibility."""
        if len(v) > 115:
            raise ValueError(
                "Digest must be at most 115 characters (120 allowed by WeChat API)"
            )
        return v

    def to_wechat_api_dict(self) -> Dict[str, Any]:
        """Convert to WeChat API request format (draft/add)."""
        payload = {
            "title": self.title,
            "author": self.author,
            "digest": self.digest,
            "content": self.content,
            "content_source_url": self.content_source_url,
            "need_open_comment": 1 if self.need_open_comment else 0,
            "only_fans_can_comment": 1 if self.only_fans_can_comment else 0,
        }
        if self.thumb_media_id:
            payload["thumb_media_id"] = self.thumb_media_id
        return payload

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = {
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "digest": self.digest,
            "show_cover_pic": self.show_cover_pic,
            "need_open_comment": self.need_open_comment,
            "only_fans_can_comment": self.only_fans_can_comment,
            "content_source_url": self.content_source_url,
            "poem_title": self.poem_title,
            "poet_name": self.poet_name,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "translation_workflow_id": self.translation_workflow_id,
            "translation_json_path": self.translation_json_path,
        }

        if self.translation_notes:
            data["translation_notes"] = self.translation_notes.to_dict()

        return data


class WeChatConfig(BaseModel):
    """WeChat API configuration."""

    appid: str = Field(..., description="WeChat Official Account AppID")
    secret: str = Field(..., description="WeChat Official Account App Secret")
    base_url: str = Field(
        default="https://api.weixin.qq.com", description="WeChat API base URL"
    )
    token_cache_path: str = Field(
        default="outputs/.cache/wechat_token.json",
        description="Path to cache WeChat access token",
    )
    timeouts: Dict[str, float] = Field(
        default={"connect": 5.0, "read": 20.0},
        description="Request timeouts in seconds",
    )
    retry_config: Dict[str, Any] = Field(
        default={"attempts": 3, "backoff": "exponential"},
        description="Retry configuration for API calls",
    )

    @field_validator("appid", "secret")
    @classmethod
    def validate_credentials(cls, v):
        """Validate WeChat credentials."""
        if not v.strip():
            raise ValueError("WeChat credentials cannot be empty")
        return v.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (with sensitive fields masked)."""
        return {
            "appid": self.appid,
            "secret": "***" if self.secret else None,
            "base_url": self.base_url,
            "token_cache_path": self.token_cache_path,
            "timeouts": self.timeouts,
            "retry_config": self.retry_config,
        }


class WeChatApiResponse(BaseModel):
    """WeChat API response wrapper."""

    errcode: Optional[int] = Field(None, description="Error code from WeChat API")
    errmsg: Optional[str] = Field(None, description="Error message from WeChat API")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data payload")

    @property
    def is_success(self) -> bool:
        """Check if API call was successful."""
        return self.errcode is None or self.errcode == 0

    @property
    def error_message(self) -> str:
        """Get formatted error message."""
        if self.is_success:
            return "No error"
        return f"WeChat API Error {self.errcode}: {self.errmsg or 'Unknown error'}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "errcode": self.errcode,
            "errmsg": self.errmsg,
            "data": self.data,
            "is_success": self.is_success,
            "error_message": self.error_message,
        }


class WeChatDraftResponse(BaseModel):
    """WeChat draft creation response."""

    media_id: Optional[str] = Field(None, description="Media ID of created draft")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> "WeChatDraftResponse":
        """Create from WeChat API response."""
        return cls(media_id=response_data.get("media_id"), created_at=datetime.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "media_id": self.media_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ArticleGenerationResult(BaseModel):
    """Result of article generation process."""

    # Article content
    article: WeChatArticle = Field(..., description="Generated WeChat article")

    # File paths
    html_path: str = Field(..., description="Path to generated HTML file")
    metadata_path: str = Field(..., description="Path to generated metadata file")

    # Generation metadata
    slug: str = Field(..., description="Article slug")
    output_directory: str = Field(..., description="Output directory path")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Generation timestamp"
    )

    # Status
    status: WeChatArticleStatus = Field(
        default=WeChatArticleStatus.GENERATED, description="Article generation status"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if generation failed"
    )

    # LLM metrics (for translation notes synthesis)
    llm_metrics: Optional[Dict[str, Any]] = Field(
        None, description="LLM call metrics (tokens, duration, cost)"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "article": self.article.to_dict(),
            "html_path": self.html_path,
            "metadata_path": self.metadata_path,
            "slug": self.slug,
            "output_directory": self.output_directory,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message,
        }
        return data


class PublishingResult(BaseModel):
    """Result of article publishing process."""

    # Success indicators
    success: bool = Field(..., description="Whether publishing was successful")
    draft_id: Optional[str] = Field(None, description="WeChat draft ID if successful")

    # API response
    api_response: Optional[WeChatApiResponse] = Field(
        None, description="WeChat API response"
    )

    # Request details
    article_path: str = Field(..., description="Path to article HTML file")
    metadata_path: str = Field(..., description="Path to article metadata file")

    # Timestamps
    published_at: Optional[datetime] = Field(None, description="Publishing timestamp")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Result creation timestamp"
    )

    # Error handling
    error_message: Optional[str] = Field(
        None, description="Error message if publishing failed"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "success": self.success,
            "draft_id": self.draft_id,
            "article_path": self.article_path,
            "metadata_path": self.metadata_path,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "error_message": self.error_message,
        }

        if self.api_response:
            data["api_response"] = self.api_response.to_dict()

        if self.published_at:
            data["published_at"] = self.published_at.isoformat()

        return data


class WeChatLLMConfig(BaseModel):
    """Configuration for LLM model types and settings."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="LLM model name")
    prompt_template: str = Field(..., description="Prompt template name")
    temperature: float = Field(default=0.1, description="Temperature for generation")
    max_tokens: int = Field(default=8192, description="Maximum tokens for generation")
    timeout: int = Field(default=180, description="Request timeout in seconds")


class WeChatLLMModelsConfig(BaseModel):
    """Configuration for different LLM model types."""

    reasoning: WeChatLLMConfig = Field(..., description="Reasoning model configuration")
    non_reasoning: WeChatLLMConfig = Field(
        ..., description="Non-reasoning model configuration"
    )


class ArticleGenerationConfig(BaseModel):
    """Configuration for article generation from translation data."""

    include_translation_notes: bool = Field(
        default=True, description="Whether to include translation notes section"
    )
    copyright_text: str = Field(
        default="本译文与导读由【知韵译诗】知韵VoxPoetica原创制作。未经授权，不得转载。若需引用，请注明出处。",
        description="Copyright disclaimer text in Chinese",
    )
    article_template: str = Field(
        default="default", description="Article template to use"
    )
    default_cover_image_path: str = Field(
        default="config/html_templates/cover_image_big.jpg",
        description="Default cover image path (relative to project root)",
    )
    default_local_cover_image_name: str = Field(
        default="cover_image_big.jpg",
        description="Default local cover image filename in wechat_articles/slug directory",
    )
    prompt_template: str = Field(
        default="wechat_article_notes_reasoning",
        description="LLM prompt template for translation notes synthesis (legacy, use llm.model_type instead)",
    )

    # LLM configuration
    model_type: str = Field(
        default="reasoning",
        description="Model type for translation notes: 'reasoning' or 'non_reasoning'",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "include_translation_notes": self.include_translation_notes,
            "copyright_text": self.copyright_text,
            "article_template": self.article_template,
            "default_cover_image_path": self.default_cover_image_path,
            "default_local_cover_image_name": self.default_local_cover_image_name,
            "prompt_template": self.prompt_template,
        }
