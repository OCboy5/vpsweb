"""
VPSWeb Repository System - Database Models

This module defines the SQLAlchemy ORM models for the VPSWeb repository system.
Based on PSD v0.3 with 4 core tables: poems, translations, ai_logs, human_notes.

Features:
- Comprehensive constraints and indexes for performance
- AsyncAttrs support for async operations
- Proper foreign key relationships
- Data validation at model level
- ULID-based primary keys for distributed systems compatibility
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all repository models with AsyncAttrs support."""

    # Common metadata for all models
    __abstract__ = True

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated"
    )


class Poem(Base):
    """
    Core poem entity representing original poetry works.

    Stores original poems with metadata about the poet, title,
    source language, and content. Supports multiple translations
    through relationships.
    """
    __tablename__ = "poems"

    # Primary key using ULID for distributed compatibility
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        comment="ULID-based primary key"
    )

    # Core poem metadata
    poet_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of the original poet"
    )

    poem_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Title of the original poem"
    )

    source_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="BCP-47 language code (e.g., 'en', 'zh-Hans')"
    )

    # Original poem content
    original_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Complete original poem text"
    )

    # Optional metadata
    author_birth_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Birth year of the poet"
    )

    publication_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Year the poem was published"
    )

    genre: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Genre or style of the poem"
    )

    tags: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Comma-separated tags for categorization"
    )

    # System fields
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this poem is active"
    )

    # Relationships
    translations: Mapped[List[Translation]] = relationship(
        "Translation",
        back_populates="poem",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    ai_logs: Mapped[List[AiLog]] = relationship(
        "AiLog",
        back_populates="poem",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    human_notes: Mapped[List[HumanNote]] = relationship(
        "HumanNote",
        back_populates="poem",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Table constraints
    __table_args__ = (
        # Ensure poet_name and poem_title are not empty
        CheckConstraint(
            "LENGTH(TRIM(poet_name)) > 0",
            name="ck_poems_poet_name_not_empty"
        ),
        CheckConstraint(
            "LENGTH(TRIM(poem_title)) > 0",
            name="ck_poems_poem_title_not_empty"
        ),
        CheckConstraint(
            "LENGTH(TRIM(original_text)) > 0",
            name="ck_poems_original_text_not_empty"
        ),
        # Validate basic language code format (simplified for SQLite)
        CheckConstraint(
            "LENGTH(source_language) >= 2 AND LENGTH(source_language) <= 10",
            name="ck_poems_valid_language_code"
        ),
        # Reasonable length constraints
        CheckConstraint(
            "LENGTH(poet_name) <= 255",
            name="ck_poems_poet_name_max_length"
        ),
        CheckConstraint(
            "LENGTH(poem_title) <= 255",
            name="ck_poems_poem_title_max_length"
        ),
        # Unique constraint for poet + title + language
        UniqueConstraint(
            "poet_name", "poem_title", "source_language",
            name="uq_poems_poet_title_lang"
        ),
        # Performance indexes
        Index("idx_poems_poet_name", "poet_name"),
        Index("idx_poems_poem_title", "poem_title"),
        Index("idx_poems_source_language", "source_language"),
        Index("idx_poems_genre", "genre"),
        Index("idx_poems_created_at", "created_at"),
        Index("idx_poems_active", "is_active"),
        # Composite indexes for common queries
        Index("idx_poems_lang_active", "source_language", "is_active"),
        Index("idx_poems_poet_created", "poet_name", "created_at"),
        {
            "comment": "Core poem entity with original poetry content and metadata"
        }
    )

    def __repr__(self) -> str:
        return f"<Poem(id='{self.id}', poet='{self.poet_name}', title='{self.poem_title}')>"


class Translation(Base):
    """
    Translation entity containing translated versions of poems.

    Stores both AI-generated and human-created translations with
    comprehensive metadata about the translation process.
    """
    __tablename__ = "translations"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        comment="ULID-based primary key"
    )

    # Foreign key to poem
    poem_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("poems.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to original poem"
    )

    # Translation metadata
    target_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="BCP-47 target language code"
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Version number for this translation"
    )

    # Translation content
    translated_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Complete translated text"
    )

    translator_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from the translator about the translation"
    )

    # Translation type and source
    translator_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of translator: 'ai', 'human', or 'hybrid'"
    )

    translator_info: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Additional info about translator (model name, human name, etc.)"
    )

    # Quality and metadata
    quality_score: Mapped[Optional[float]] = mapped_column(
        # Using String instead of float to avoid SQLite precision issues
        String(10),
        nullable=True,
        comment="Quality score (0.0-1.0) if available"
    )

    license: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="CC-BY-4.0",
        comment="License for this translation"
    )

    # System fields
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this translation is published"
    )

    # Relationships
    poem: Mapped[Poem] = relationship("Poem", back_populates="translations")

    # Table constraints
    __table_args__ = (
        # Validate basic target language code format (simplified for SQLite)
        CheckConstraint(
            "LENGTH(target_language) >= 2 AND LENGTH(target_language) <= 10",
            name="ck_translations_valid_target_language"
        ),
        # Validate translator type
        CheckConstraint(
            "translator_type IN ('ai', 'human', 'hybrid')",
            name="ck_translations_valid_translator_type"
        ),
        # Validate version is positive
        CheckConstraint(
            "version > 0",
            name="ck_translations_version_positive"
        ),
        # Ensure translated text is not empty
        CheckConstraint(
            "LENGTH(TRIM(translated_text)) > 0",
            name="ck_translations_text_not_empty"
        ),
        # Validate quality score format (simplified for SQLite)
        CheckConstraint(
            "quality_score IS NULL OR LENGTH(quality_score) <= 10",
            name="ck_translations_valid_quality_score"
        ),
        # Unique constraint for poem + language + version
        UniqueConstraint(
            "poem_id", "target_language", "version",
            name="uq_translations_poem_lang_version"
        ),
        # Performance indexes
        Index("idx_translations_poem_id", "poem_id"),
        Index("idx_translations_target_language", "target_language"),
        Index("idx_translations_translator_type", "translator_type"),
        Index("idx_translations_version", "version"),
        Index("idx_translations_published", "is_published"),
        Index("idx_translations_created_at", "created_at"),
        # Composite indexes for common queries
        Index("idx_translations_poem_lang", "poem_id", "target_language"),
        Index("idx_translations_poem_published", "poem_id", "is_published"),
        Index("idx_translations_lang_published", "target_language", "is_published"),
        {
            "comment": "Translation entity with translated content and metadata"
        }
    )

    def __repr__(self) -> str:
        return f"<Translation(id='{self.id}', poem_id='{self.poem_id}', lang='{self.target_language}', v='{self.version}')>"


class AiLog(Base):
    """
    AI processing log for tracking AI translation operations.

    Stores metadata about AI translation processes including
    model information, token usage, and processing details.
    """
    __tablename__ = "ai_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        comment="ULID-based primary key"
    )

    # Foreign key to poem
    poem_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("poems.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to original poem"
    )

    # Foreign key to translation (optional, may be created during processing)
    translation_id: Mapped[Optional[str]] = mapped_column(
        String(26),
        ForeignKey("translations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to resulting translation"
    )

    # AI processing metadata
    workflow_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Workflow mode: 'reasoning', 'non_reasoning', 'hybrid'"
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="AI provider (e.g., 'tongyi', 'deepseek')"
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Specific model used (e.g., 'qwen-max-latest')"
    )

    temperature: Mapped[float] = mapped_column(
        # Using String for precision
        String(10),
        nullable=False,
        comment="Temperature parameter used"
    )

    # Token usage and metrics
    prompt_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of tokens in prompt"
    )

    completion_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of tokens in completion"
    )

    total_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total tokens used"
    )

    cost: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Cost in currency (stored as string for precision)"
    )

    duration_seconds: Mapped[Optional[float]] = mapped_column(
        # Using String for precision
        String(20),
        nullable=True,
        comment="Processing duration in seconds"
    )

    # Processing status and details
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="Status: 'pending', 'processing', 'completed', 'failed'"
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if processing failed"
    )

    raw_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Raw AI response (truncated for storage)"
    )

    # Relationships
    poem: Mapped[Poem] = relationship("Poem", back_populates="ai_logs")
    translation: Mapped[Optional[Translation]] = relationship("Translation")

    # Table constraints
    __table_args__ = (
        # Validate workflow mode
        CheckConstraint(
            "workflow_mode IN ('reasoning', 'non_reasoning', 'hybrid')",
            name="ck_ai_logs_valid_workflow_mode"
        ),
        # Validate status
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_ai_logs_valid_status"
        ),
        # Validate numeric fields
        CheckConstraint(
            "prompt_tokens IS NULL OR prompt_tokens >= 0",
            name="ck_ai_logs_prompt_tokens_non_negative"
        ),
        CheckConstraint(
            "completion_tokens IS NULL OR completion_tokens >= 0",
            name="ck_ai_logs_completion_tokens_non_negative"
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="ck_ai_logs_total_tokens_non_negative"
        ),
        # Validate temperature format (simplified for SQLite)
        CheckConstraint(
            "LENGTH(temperature) <= 10",
            name="ck_ai_logs_valid_temperature"
        ),
        # Performance indexes
        Index("idx_ai_logs_poem_id", "poem_id"),
        Index("idx_ai_logs_translation_id", "translation_id"),
        Index("idx_ai_logs_workflow_mode", "workflow_mode"),
        Index("idx_ai_logs_provider", "provider"),
        Index("idx_ai_logs_status", "status"),
        Index("idx_ai_logs_created_at", "created_at"),
        # Composite indexes for common queries
        Index("idx_ai_logs_poem_status", "poem_id", "status"),
        Index("idx_ai_logs_provider_model", "provider", "model_name"),
        Index("idx_ai_logs_status_created", "status", "created_at"),
        {
            "comment": "AI processing log for tracking translation operations"
        }
    )

    def __repr__(self) -> str:
        return f"<AiLog(id='{self.id}', poem_id='{self.poem_id}', provider='{self.provider}', status='{self.status}')>"


class HumanNote(Base):
    """
    Human notes and annotations for poems and translations.

    Stores human-created notes, reviews, and annotations about
    poems and their translations.
    """
    __tablename__ = "human_notes"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(26),
        primary_key=True,
        comment="ULID-based primary key"
    )

    # Foreign key to poem
    poem_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("poems.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to original poem"
    )

    # Foreign key to translation (optional - note can be about poem or specific translation)
    translation_id: Mapped[Optional[str]] = mapped_column(
        String(26),
        ForeignKey("translations.id", ondelete="CASCADE"),
        nullable=True,
        comment="Reference to specific translation if applicable"
    )

    # Note content
    note_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of note: 'review', 'comment', 'suggestion', 'correction'"
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional title for the note"
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Complete note content"
    )

    # Author information
    author_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of the person who wrote the note"
    )

    # System fields
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this note should be displayed publicly"
    )

    # Relationships
    poem: Mapped[Poem] = relationship("Poem", back_populates="human_notes")
    translation: Mapped[Optional[Translation]] = relationship("Translation")

    # Table constraints
    __table_args__ = (
        # Validate note type
        CheckConstraint(
            "note_type IN ('review', 'comment', 'suggestion', 'correction', 'general')",
            name="ck_human_notes_valid_note_type"
        ),
        # Ensure content is not empty
        CheckConstraint(
            "LENGTH(TRIM(content)) > 0",
            name="ck_human_notes_content_not_empty"
        ),
        # Performance indexes
        Index("idx_human_notes_poem_id", "poem_id"),
        Index("idx_human_notes_translation_id", "translation_id"),
        Index("idx_human_notes_note_type", "note_type"),
        Index("idx_human_notes_author_name", "author_name"),
        Index("idx_human_notes_is_public", "is_public"),
        Index("idx_human_notes_created_at", "created_at"),
        # Composite indexes for common queries
        Index("idx_human_notes_poem_type", "poem_id", "note_type"),
        Index("idx_human_notes_public_created", "is_public", "created_at"),
        Index("idx_human_notes_translation_type", "translation_id", "note_type"),
        {
            "comment": "Human notes and annotations for poems and translations"
        }
    )

    def __repr__(self) -> str:
        return f"<HumanNote(id='{self.id}', poem_id='{self.poem_id}', type='{self.note_type}')>"