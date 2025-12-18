"""
VPSWeb Repository ORM Models v0.3.1

SQLAlchemy ORM models for the 4-table database schema.
Defines Poem, Translation, AILog, and HumanNote models with relationships.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

# Define UTC+8 timezone
UTC_PLUS_8 = timezone(timedelta(hours=8))

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class Poem(Base):
    """Poem model representing original poetry content"""

    __tablename__ = "poems"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Core fields
    poet_name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    poem_title: Mapped[str] = mapped_column(
        String(300), nullable=False, index=True
    )
    source_language: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC_PLUS_8),
    )

    # Relationships
    translations: Mapped[List["Translation"]] = relationship(
        "Translation",
        back_populates="poem",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_poems_created_at", "created_at"),
        Index("idx_poems_poet_name", "poet_name"),
        Index("idx_poems_title", "poem_title"),
        Index("idx_poems_language", "source_language"),
        Index("idx_poems_selected", "selected"),
    )

    def __repr__(self) -> str:
        return f"Poem(id={self.id}, title='{self.poem_title}', poet='{self.poet_name}')"

    @property
    def translation_count(self) -> int:
        """Get the number of translations for this poem"""
        return self.translations.count()

    @property
    def ai_translation_count(self) -> int:
        """Get the number of AI translations"""
        return self.translations.filter_by(translator_type="ai").count()

    @property
    def human_translation_count(self) -> int:
        """Get the number of human translations"""
        return self.translations.filter_by(translator_type="human").count()


class Translation(Base):
    """Translation model representing translated poetry content"""

    __tablename__ = "translations"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign key to Poem
    poem_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("poems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Translation metadata
    translator_type: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # 'ai' or 'human'
    translator_info: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    target_language: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Translated title and poet name metadata
    translated_poem_title: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, index=False
    )
    translated_poet_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=False
    )

    # Optional fields
    quality_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        CheckConstraint("quality_rating >= 0 AND quality_rating <= 10"),
        nullable=True,
        default=0,
        server_default="0",
    )
    raw_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # File organization fields for poet-based storage
    poet_subdirectory: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    relative_json_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    file_category: Mapped[Optional[str]] = mapped_column(
        Enum("recent", "poet_archive", name="file_category_enum"),
        nullable=True,
        index=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
    )

    # Relationships
    poem: Mapped["Poem"] = relationship("Poem", back_populates="translations")
    ai_logs: Mapped[List["AILog"]] = relationship(
        "AILog", back_populates="translation", cascade="all, delete-orphan"
    )
    human_notes: Mapped[List["HumanNote"]] = relationship(
        "HumanNote", back_populates="translation", cascade="all, delete-orphan"
    )
    workflow_steps: Mapped[List["TranslationWorkflowStep"]] = relationship(
        "TranslationWorkflowStep",
        back_populates="translation",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_translations_poem_id", "poem_id"),
        Index("idx_translations_type", "translator_type"),
        Index("idx_translations_language", "target_language"),
        Index("idx_translations_created_at", "created_at"),
        Index("idx_translations_quality_rating", "quality_rating"),
        Index(
            "idx_translations_composite",
            "poem_id",
            "target_language",
            "translator_type",
        ),
        Index("idx_translations_composite_created", "poem_id", "created_at"),
        Index("idx_translations_poet_subdir", "poet_subdirectory"),
        Index("idx_translations_file_category", "file_category"),
        Index(
            "idx_translations_composite_file",
            "poet_subdirectory",
            "file_category",
        ),
        CheckConstraint(
            "translator_type IN ('ai', 'human')", name="ck_translator_type"
        ),
    )

    def __repr__(self) -> str:
        return f"Translation(id={self.id}, type={self.translator_type}, language={self.target_language})"

    @property
    def has_ai_logs(self) -> bool:
        """Check if this translation has AI logs"""
        return len(self.ai_logs) > 0

    @property
    def has_human_notes(self) -> bool:
        """Check if this translation has human notes"""
        return len(self.human_notes) > 0

    @property
    def has_workflow_steps(self) -> bool:
        """Check if this translation has workflow steps"""
        return len(self.workflow_steps) > 0

    @property
    def workflow_step_count(self) -> int:
        """Get the number of workflow steps for this translation"""
        return len(self.workflow_steps)

    @property
    def has_translation_notes(self) -> bool:
        """Check if this translation has AI logs (translation notes)"""
        return len(self.ai_logs) > 0

    @property
    def total_tokens_used(self) -> Optional[int]:
        """Get total tokens used across all workflow steps"""
        return sum(step.tokens_used or 0 for step in self.workflow_steps)

    @property
    def total_cost(self) -> Optional[float]:
        """Get total cost across all workflow steps"""
        return sum(step.cost or 0.0 for step in self.workflow_steps)

    @property
    def total_duration(self) -> Optional[float]:
        """Get total duration across all workflow steps"""
        return sum(
            step.duration_seconds or 0.0 for step in self.workflow_steps
        )


class AILog(Base):
    """AILog model tracking AI translation execution details"""

    __tablename__ = "ai_logs"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign key to Translation
    translation_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("translations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # AI execution details
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    workflow_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'reasoning', 'non_reasoning', 'hybrid'

    # Performance and usage data
    token_usage_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    cost_info_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    runtime_seconds: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
    )

    # Relationships
    translation: Mapped["Translation"] = relationship(
        "Translation", back_populates="ai_logs"
    )
    workflow_steps: Mapped[List["TranslationWorkflowStep"]] = relationship(
        "TranslationWorkflowStep",
        back_populates="ai_log",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_ai_logs_translation_id", "translation_id"),
        Index("idx_ai_logs_model_name", "model_name"),
        Index("idx_ai_logs_workflow_mode", "workflow_mode"),
        Index("idx_ai_logs_created_at", "created_at"),
        CheckConstraint(
            "workflow_mode IN ('reasoning', 'non_reasoning', 'hybrid', 'manual')",
            name="ck_workflow_mode",
        ),
    )

    def __repr__(self) -> str:
        return f"AILog(id={self.id}, model={self.model_name}, mode={self.workflow_mode})"

    @property
    def token_usage(self) -> Optional[dict]:
        """Parse token usage JSON if available"""
        if self.token_usage_json:
            import json

            return json.loads(self.token_usage_json)
        return None

    @property
    def cost_info(self) -> Optional[dict]:
        """Parse cost info JSON if available"""
        if self.cost_info_json:
            import json

            return json.loads(self.cost_info_json)
        return None

    @property
    def step_count(self) -> int:
        """Get the number of workflow steps for this AI log"""
        return len(self.workflow_steps)


class HumanNote(Base):
    """HumanNote model for annotations on human translations"""

    __tablename__ = "human_notes"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign key to Translation
    translation_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("translations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Note content
    note_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
    )

    # Relationships
    translation: Mapped["Translation"] = relationship(
        "Translation", back_populates="human_notes"
    )

    # Indexes
    __table_args__ = (
        Index("idx_human_notes_translation_id", "translation_id"),
        Index("idx_human_notes_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"HumanNote(id={self.id}, translation_id={self.translation_id})"


class TranslationWorkflowStep(Base):
    """TranslationWorkflowStep model for detailed T-E-T workflow content"""

    __tablename__ = "translation_workflow_steps"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign key to Translation (for aggregation queries)
    translation_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("translations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to AILog (for provenance)
    ai_log_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("ai_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Workflow identification
    workflow_id: Mapped[str] = mapped_column(
        String(26), nullable=False, index=True
    )

    # Step classification
    step_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # 'initial_translation', 'editor_review', 'revised_translation'
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Core content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # NEW: Dedicated columns for key metrics (SQL-queryable)
    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    prompt_tokens: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    completion_tokens: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True
    )
    cost: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True
    )

    # Keep JSON for additional/future metrics (flexibility)
    additional_metrics: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Translated metadata (for initial_translation and revised_translation steps)
    translated_title: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    translated_poet_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
    )

    # Relationships
    translation: Mapped["Translation"] = relationship(
        "Translation", back_populates="workflow_steps"
    )
    ai_log: Mapped["AILog"] = relationship(
        "AILog", back_populates="workflow_steps"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_workflow_steps_translation_id", "translation_id"),
        Index("idx_workflow_steps_ai_log_id", "ai_log_id"),
        Index("idx_workflow_steps_workflow_id", "workflow_id"),
        Index("idx_workflow_steps_type_order", "translation_id", "step_order"),
        # Performance indexes for analytics
        Index("idx_workflow_steps_cost", "cost"),
        Index("idx_workflow_steps_duration", "duration_seconds"),
        Index("idx_workflow_steps_tokens", "tokens_used"),
        Index(
            "idx_workflow_steps_step_metrics",
            "step_type",
            "cost",
            "duration_seconds",
        ),
        CheckConstraint(
            "step_type IN ('initial_translation', 'editor_review', 'revised_translation')",
            name="ck_translation_workflow_steps_step_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"TranslationWorkflowStep(id={self.id}, step_type={self.step_type}, "
            f"translation_id={self.translation_id})"
        )

    @property
    def additional_metrics_data(self) -> Optional[dict]:
        """Parse additional metrics JSON if available"""
        if self.additional_metrics:
            import json

            return json.loads(self.additional_metrics)
        return None

    @property
    def model_info_data(self) -> Optional[dict]:
        """Parse model info JSON if available"""
        if self.model_info:
            import json

            return json.loads(self.model_info)
        return None


class BackgroundBriefingReport(Base):
    """BackgroundBriefingReport model for storing AI-generated poem analysis"""

    __tablename__ = "background_briefing_reports"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign key to Poem (one-to-one relationship)
    poem_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("poems.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Core content
    content: Mapped[str] = mapped_column(Text, nullable=False)  # JSON content
    model_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Performance metrics
    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    cost: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True
    )
    time_spent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True
    )  # Time in seconds for BBR generation

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC_PLUS_8),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC_PLUS_8),
    )

    # Relationships
    poem: Mapped["Poem"] = relationship(
        "Poem",
        back_populates="background_briefing_report",
        single_parent=True,
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_bbr_poem_id", "poem_id"),
        Index("idx_bbr_created_at", "created_at"),
        Index("idx_bbr_cost", "cost"),
        Index("idx_bbr_time_spent", "time_spent"),
    )

    def __repr__(self) -> str:
        return (
            f"BackgroundBriefingReport(id={self.id}, poem_id={self.poem_id})"
        )

    @property
    def content_data(self) -> Optional[dict]:
        """Parse BBR content JSON if available"""
        if self.content:
            import json

            return json.loads(self.content)
        return None

    @property
    def model_info_data(self) -> Optional[dict]:
        """Parse model info JSON if available"""
        if self.model_info:
            import json

            return json.loads(self.model_info)
        return None


# Add relationship to Poem model
Poem.background_briefing_report = relationship(
    "BackgroundBriefingReport",
    back_populates="poem",
    uselist=False,
    cascade="all, delete-orphan",
    single_parent=True,
)

# WorkflowTask model removed - task tracking now handled by FastAPI app.state
# for real-time in-memory storage with enhanced step progress reporting
