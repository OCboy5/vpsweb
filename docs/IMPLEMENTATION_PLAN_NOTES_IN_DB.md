# Implementation Plan: Translation Workflow Notes in Database

## Overview

This plan implements the storage of detailed translation workflow content (T-E-T process) in the database while keeping JSON files as external backups. The goal is to provide a complete, database-driven foundation for the "Translation Notes" page.

## Current State Analysis

### Current Database Schema (4 Tables)
- `poems` - Original poetry content
- `translations` - Final translation results only
- `ai_logs` - Aggregated workflow execution data (summary only)
- `human_notes` - Human translation annotations

### Current JSON Structure (Complete Content)
```json
{
  "workflow_id": "uuid",
  "input": { "original_poem": "...", "metadata": {...} },
  "initial_translation": { "text": "...", "notes": "...", "metrics": {...} },
  "editor_review": { "suggestions": "...", "metrics": {...} },
  "revised_translation": { "text": "...", "notes": "...", "metrics": {...} },
  "total_tokens": 13813,
  "duration_seconds": 254.83
}
```

### Problem Statement
- Critical T-E-T workflow content exists only in JSON files
- Database stores only aggregated/summary data
- JSON files became primary source instead of backups
- Translation Notes page requires file system access + database queries

## Target Architecture

### New Database Schema (5 Tables)
1. `poems` - Original poetry content (unchanged)
2. `translations` - Final translation results (unchanged)
3. `ai_logs` - Workflow execution records (enhanced)
4. `human_notes` - Human translation notes (unchanged)
5. **NEW**: `translation_workflow_steps` - Detailed T-E-T workflow content

### Relationship Design
```
poem (1) → (N) translations
   ├── translation.ai (1) → (1) ai_log (1) → (3) translation_workflow_steps
   └── translation.human (1) → (1) human_note
```

### ID Strategy
- **Standardize on ULID** for all database records (26 chars, time-sortable)
- Replace UUID4 usage in workflow.py and vpsweb_adapter.py
- Maintain consistent ID generation across all tables

## Implementation Phases

### Phase 1: Database Schema Enhancement (Week 1)

#### 1.1 Create Alembic Migration
**File**: `src/vpsweb/repository/migrations/versions/add_translation_workflow_steps.py`

```python
"""Add translation_workflow_steps table

Revision ID: 001_add_workflow_steps
Revises: base
Create Date: 2025-01-XX

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create translation_workflow_steps table
    op.create_table('translation_workflow_steps',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('translation_id', sa.String(length=26), nullable=False),
        sa.Column('ai_log_id', sa.String(length=26), nullable=False),
        sa.Column('workflow_id', sa.String(length=26), nullable=False),
        sa.Column('step_type', sa.String(length=30), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('model_info', sa.Text(), nullable=True),
        sa.Column('performance_metrics', sa.Text(), nullable=True),
        sa.Column('translated_title', sa.String(length=500), nullable=True),
        sa.Column('translated_poet_name', sa.String(length=200), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ai_log_id'], ['ai_logs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['translation_id'], ['translations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_workflow_steps_translation_id', 'translation_workflow_steps', ['translation_id'])
    op.create_index('idx_workflow_steps_ai_log_id', 'translation_workflow_steps', ['ai_log_id'])
    op.create_index('idx_workflow_steps_workflow_id', 'translation_workflow_steps', ['workflow_id'])
    op.create_index('idx_workflow_steps_type_order', 'translation_workflow_steps', ['translation_id', 'step_order'])

def downgrade():
    op.drop_table('translation_workflow_steps')
```

#### 1.2 Update SQLAlchemy Models
**File**: `src/vpsweb/repository/models.py`

```python
class TranslationWorkflowStep(Base):
    """Detailed workflow step content for T-E-T translation process"""

    __tablename__ = "translation_workflow_steps"

    # Primary key
    id: Mapped[str] = mapped_column(String(26), primary_key=True, index=True)

    # Foreign keys
    translation_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("translations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ai_log_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("ai_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Workflow identification
    workflow_id: Mapped[str] = mapped_column(String(26), nullable=False, index=True)
    step_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content fields
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata fields
    model_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # NEW: Dedicated columns for key metrics (SQL-queryable)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)

    # Keep JSON for additional/future metrics (flexibility)
    additional_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Translated metadata (for initial_translation and revised_translation steps)
    translated_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    translated_poet_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC_PLUS_8)
    )

    # Relationships
    translation: Mapped["Translation"] = relationship("Translation", back_populates="workflow_steps")
    ai_log: Mapped["AILog"] = relationship("AILog", back_populates="workflow_steps")

    # Indexes (enhanced for analytics)
    __table_args__ = (
        Index("idx_workflow_steps_composite", "translation_id", "step_order"),
        Index("idx_workflow_steps_execution", "ai_log_id", "step_order"),
        Index("idx_workflow_steps_workflow", "workflow_id", "step_type"),
        Index("idx_workflow_steps_cost", "cost"),
        Index("idx_workflow_steps_duration", "duration_seconds"),
        Index("idx_workflow_steps_tokens", "tokens_used"),
        Index("idx_workflow_steps_step_metrics", "step_type", "cost", "duration_seconds"),
        CheckConstraint("step_type IN ('initial_translation', 'editor_review', 'revised_translation')",
                       name="ck_step_type"),
    )
```

#### 1.3 Update Translation Model Relationship
**File**: `src/vpsweb/repository/models.py` (add to Translation class)

```python
class Translation(Base):
    # ... existing fields ...

    # NEW: Relationship to workflow steps
    workflow_steps: Mapped[List["TranslationWorkflowStep"]] = relationship(
        "TranslationWorkflowStep", back_populates="translation", cascade="all, delete-orphan"
    )
```

#### 1.4 Update AILog Model Relationship
**File**: `src/vpsweb/repository/models.py` (add to AILog class)

```python
class AILog(Base):
    # ... existing fields ...

    # NEW: Relationship to workflow steps
    workflow_steps: Mapped[List["TranslationWorkflowStep"]] = relationship(
        "TranslationWorkflowStep", back_populates="ai_log", cascade="all, delete-orphan"
    )
```

### Phase 2: ID Generation Standardization (Week 1)

#### 2.1 Update Workflow ID Generation
**File**: `src/vpsweb/core/workflow.py`

```python
# BEFORE:
import uuid
workflow_id = str(uuid.uuid4())

# AFTER:
from vpsweb.utils.ulid_utils import generate_ulid
workflow_id = generate_ulid()
```

#### 2.2 Update VPSWeb Adapter Task ID Generation
**File**: `src/vpsweb/webui/services/vpsweb_adapter.py`

```python
# BEFORE:
import uuid
task_id = str(uuid.uuid4())

# AFTER:
from vpsweb.utils.ulid_utils import generate_ulid
task_id = generate_ulid()
```

#### 2.3 Update Test Fixtures
**Files**: Multiple test files using uuid.uuid4()

```python
# BEFORE:
import uuid
poem_data["id"] = str(uuid.uuid4())[:26]

# AFTER:
from vpsweb.utils.ulid_utils import generate_ulid
poem_data["id"] = generate_ulid()
```

### Phase 3: CRUD Operations Enhancement (Week 2)

#### 3.1 Create TranslationWorkflowStep CRUD
**File**: `src/vpsweb/repository/crud.py`

```python
class TranslationWorkflowStepCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow_steps(self, translation_id: str, ai_log_id: str,
                             workflow_id: str, workflow_data: Dict[str, Any]) -> List[TranslationWorkflowStep]:
        """Create all three workflow steps from TranslationOutput data"""

        steps = []

        # Step 1: Initial Translation
        initial_metrics = workflow_data["initial_translation"]
        initial_step = TranslationWorkflowStep(
            id=generate_ulid(),
            translation_id=translation_id,
            ai_log_id=ai_log_id,
            workflow_id=workflow_id,
            step_type="initial_translation",
            step_order=1,
            content=workflow_data["initial_translation"]["initial_translation"],
            notes=workflow_data["initial_translation"]["initial_translation_notes"],
            model_info=json.dumps(workflow_data["initial_translation"]["model_info"]),
            # NEW: Use dedicated metric columns
            tokens_used=initial_metrics.get("tokens_used", 0),
            prompt_tokens=initial_metrics.get("prompt_tokens", 0),
            completion_tokens=initial_metrics.get("completion_tokens", 0),
            duration_seconds=initial_metrics.get("duration", 0.0),
            cost=initial_metrics.get("cost", 0.0),
            # Keep additional metrics in JSON
            additional_metrics=json.dumps({
                "provider": workflow_data["initial_translation"]["model_info"].get("provider"),
                "model": workflow_data["initial_translation"]["model_info"].get("model"),
                "temperature": workflow_data["initial_translation"]["model_info"].get("temperature")
            }),
            translated_title=workflow_data["initial_translation"]["translated_poem_title"],
            translated_poet_name=workflow_data["initial_translation"]["translated_poet_name"],
            timestamp=datetime.fromisoformat(workflow_data["initial_translation"]["timestamp"]),
            created_at=datetime.now(UTC_PLUS_8)
        )
        steps.append(initial_step)

        # Step 2: Editor Review
        editor_metrics = workflow_data["editor_review"]
        editor_step = TranslationWorkflowStep(
            id=generate_ulid(),
            translation_id=translation_id,
            ai_log_id=ai_log_id,
            workflow_id=workflow_id,
            step_type="editor_review",
            step_order=2,
            content=workflow_data["editor_review"]["editor_suggestions"],
            notes="",
            model_info=json.dumps(workflow_data["editor_review"]["model_info"]),
            # NEW: Use dedicated metric columns
            tokens_used=editor_metrics.get("tokens_used", 0),
            prompt_tokens=editor_metrics.get("prompt_tokens", 0),
            completion_tokens=editor_metrics.get("completion_tokens", 0),
            duration_seconds=editor_metrics.get("duration", 0.0),
            cost=editor_metrics.get("cost", 0.0),
            # Keep additional metrics in JSON
            additional_metrics=json.dumps({
                "provider": workflow_data["editor_review"]["model_info"].get("provider"),
                "model": workflow_data["editor_review"]["model_info"].get("model"),
                "temperature": workflow_data["editor_review"]["model_info"].get("temperature")
            }),
            timestamp=datetime.fromisoformat(workflow_data["editor_review"]["timestamp"]),
            created_at=datetime.now(UTC_PLUS_8)
        )
        steps.append(editor_step)

        # Step 3: Revised Translation
        revised_metrics = workflow_data["revised_translation"]
        revised_step = TranslationWorkflowStep(
            id=generate_ulid(),
            translation_id=translation_id,
            ai_log_id=ai_log_id,
            workflow_id=workflow_id,
            step_type="revised_translation",
            step_order=3,
            content=workflow_data["revised_translation"]["revised_translation"],
            notes=workflow_data["revised_translation"]["revised_translation_notes"],
            model_info=json.dumps(workflow_data["revised_translation"]["model_info"]),
            # NEW: Use dedicated metric columns
            tokens_used=revised_metrics.get("tokens_used", 0),
            prompt_tokens=revised_metrics.get("prompt_tokens", 0),
            completion_tokens=revised_metrics.get("completion_tokens", 0),
            duration_seconds=revised_metrics.get("duration", 0.0),
            cost=revised_metrics.get("cost", 0.0),
            # Keep additional metrics in JSON
            additional_metrics=json.dumps({
                "provider": workflow_data["revised_translation"]["model_info"].get("provider"),
                "model": workflow_data["revised_translation"]["model_info"].get("model"),
                "temperature": workflow_data["revised_translation"]["model_info"].get("temperature")
            }),
            translated_title=workflow_data["revised_translation"]["refined_translated_poem_title"],
            translated_poet_name=workflow_data["revised_translation"]["refined_translated_poet_name"],
            timestamp=datetime.fromisoformat(workflow_data["revised_translation"]["timestamp"]),
            created_at=datetime.now(UTC_PLUS_8)
        )
        steps.append(revised_step)

        # IMPROVED: Add steps to session but DON'T commit - let caller handle transaction
        for step in steps:
            self.db.add(step)

        # Return steps for caller to commit
        return steps

    def get_workflow_steps_by_translation(self, translation_id: str) -> List[TranslationWorkflowStep]:
        """Get all workflow steps for a translation"""
        return (
            self.db.query(TranslationWorkflowStep)
            .filter(TranslationWorkflowStep.translation_id == translation_id)
            .order_by(TranslationWorkflowStep.step_order)
            .all()
        )

    def get_workflow_steps_by_ai_log(self, ai_log_id: str) -> List[TranslationWorkflowStep]:
        """Get all workflow steps for an AI log"""
        return (
            self.db.query(TranslationWorkflowStep)
            .filter(TranslationWorkflowStep.ai_log_id == ai_log_id)
            .order_by(TranslationWorkflowStep.step_order)
            .all()
        )
```

#### 3.2 Update AILog CRUD to Handle Workflow Steps
**File**: `src/vpsweb/repository/crud.py` (update AILogCRUD.create method)

```python
class AILogCRUD:
    def create(self, ai_log_data: AILogCreate, workflow_steps_data: Optional[Dict] = None) -> AILog:
        """Create a new AI log entry with optional workflow steps - SINGLE TRANSACTION"""

        # Generate ULID for time-sortable unique ID
        ai_log_id = generate_ulid()

        db_ai_log = AILog(
            id=ai_log_id,
            translation_id=ai_log_data.translation_id,
            model_name=ai_log_data.model_name,
            workflow_mode=ai_log_data.workflow_mode,
            token_usage_json=ai_log_data.token_usage_json,
            cost_info_json=ai_log_data.cost_info_json,
            runtime_seconds=ai_log_data.runtime_seconds,
            notes=ai_log_data.notes,
        )

        try:
            self.db.add(db_ai_log)
            self.db.flush()  # Get the ID without committing

            # Create workflow steps in same transaction
            if workflow_steps_data:
                workflow_steps_crud = TranslationWorkflowStepCRUD(self.db)
                workflow_steps_crud.create_workflow_steps(
                    translation_id=ai_log_data.translation_id,
                    ai_log_id=ai_log_id,
                    workflow_id=workflow_steps_data.get("workflow_id"),
                    workflow_data=workflow_steps_data.get("workflow_output")
                )
                # NOTE: No commit here - let caller handle it

            # IMPROVED: SINGLE COMMIT POINT - atomic operation
            self.db.commit()
            self.db.refresh(db_ai_log)
            return db_ai_log

        except Exception as e:
            # IMPROVED: Rollback entire transaction on any error
            self.db.rollback()
            raise
```

### Phase 4: VPSWeb Adapter Enhancement (Week 2)

#### 4.1 Update VPSWebAdapter to Save Workflow Steps
**File**: `src/vpsweb/webui/services/vpsweb_adapter.py`

```python
# Update _execute_workflow_task_with_callback method
async def _execute_workflow_task_with_callback(
    self,
    task_id: str,
    poem_id: str,
    source_lang: str,
    target_lang: str,
    workflow_mode_str: str,
) -> None:
    # ... existing code until workflow execution ...

    try:
        # Execute workflow as a single, encapsulated unit
        final_result = await workflow.execute(
            translation_input, show_progress=False
        )

        # NEW: Save to database with workflow steps
        print(f"[DB SAVE] 💾 Starting database save with workflow steps...")

        db = SessionLocal()
        try:
            # Create translation record
            translation_crud = TranslationCRUD(db)
            translation_data = TranslationCreate(
                poem_id=poem_id,
                translator_type="ai",
                translator_info=f"{final_result.initial_translation.model_info.get('provider')}/{final_result.initial_translation.model_info.get('model')}",
                target_language=target_lang,
                translated_text=final_result.revised_translation.revised_translation,
                translated_poem_title=final_result.revised_translation.refined_translated_poem_title,
                translated_poet_name=final_result.revised_translation.refined_translated_poet_name,
            )
            translation = translation_crud.create(translation_data)
            translation_id = translation.id

            print(f"[DB SAVE] ✅ [STEP 1] Translation created: {translation_id}")

            # Create AI log with workflow steps
            ai_log_crud = AILogCRUD(db)

            # Calculate aggregated metrics
            total_tokens = (
                final_result.initial_translation.tokens_used +
                final_result.editor_review.tokens_used +
                final_result.revised_translation.tokens_used
            )

            total_cost = (
                final_result.initial_translation.cost +
                final_result.editor_review.cost +
                final_result.revised_translation.cost
            )

            total_duration = (
                final_result.initial_translation.duration +
                final_result.editor_review.duration +
                final_result.revised_translation.duration
            )

            ai_log_data = AILogCreate(
                translation_id=translation_id,
                model_name=final_result.initial_translation.model_info.get('model'),
                workflow_mode=workflow_mode_str,
                token_usage_json=json.dumps({"total_tokens": total_tokens}),
                cost_info_json=json.dumps({"total_cost": total_cost}),
                runtime_seconds=total_duration,
                notes=f"Workflow completed in {total_duration:.2f}s with {total_tokens} total tokens"
            )

            workflow_steps_data = {
                "workflow_id": final_result.workflow_id,
                "workflow_output": final_result.to_dict()
            }

            ai_log = ai_log_crud.create(ai_log_data, workflow_steps_data)
            print(f"[DB SAVE] ✅ [STEP 2] AI log with workflow steps created: {ai_log.id}")

            # Save JSON file as backup (write-only after DB save)
            try:
                json_path = self.storage_handler.save_translation_with_poet_dir(
                    output=final_result,
                    poet_name=translation_input.metadata.get("author", "Unknown"),
                    workflow_mode=workflow_mode.value,
                    include_mode_tag=True,
                )
                print(f"[DB SAVE] ✅ [STEP 3] JSON backup saved: {json_path}")
            except Exception as json_error:
                print(f"[DB SAVE] ⚠️ [STEP 3 WARNING] Failed to save JSON backup: {json_error}")

        except Exception as e:
            print(f"[DB SAVE] ❌ Database save failed: {e}")
            raise
        finally:
            db.close()

    # ... rest of the method ...
```

### Phase 5: API Layer Enhancement (Week 3)

#### 5.1 Create Translation Notes Service
**File**: `src/vpsweb/webui/services/translation_notes_service.py`

```python
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..repository.models import Translation, AILog, TranslationWorkflowStep, HumanNote, Poem

class TranslationNotesService:
    def __init__(self, db: Session):
        self.db = db

    def get_translation_notes(self, translation_id: str) -> Dict[str, Any]:
        """Get complete translation notes for both AI and human translations"""

        # Get translation with poem
        translation = (
            self.db.query(Translation, Poem)
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Translation.id == translation_id)
            .first()
        )

        if not translation:
            raise ValueError(f"Translation not found: {translation_id}")

        translation_record, poem_record = translation

        result = {
            "translation_id": translation_id,
            "translation_type": translation_record.translator_type,
            "target_language": translation_record.target_language,
            "poem": {
                "id": poem_record.id,
                "title": poem_record.poem_title,
                "author": poem_record.poet_name,
                "original_text": poem_record.original_text,
                "source_language": poem_record.source_language
            },
            "final_translation": {
                "text": translation_record.translated_text,
                "title": translation_record.translated_poem_title,
                "poet_name": translation_record.translated_poet_name
            }
        }

        if translation_record.translator_type == "ai":
            # Get AI workflow steps
            result["workflow_steps"] = self._get_ai_workflow_steps(translation_id)
        else:
            # Get human notes
            result["workflow_steps"] = self._get_human_notes(translation_id)

        return result

    def _get_ai_workflow_steps(self, translation_id: str) -> List[Dict[str, Any]]:
        """Get complete T-E-T workflow steps for AI translation"""

        workflow_steps = (
            self.db.query(TranslationWorkflowStep)
            .join(AILog, TranslationWorkflowStep.ai_log_id == AILog.id)
            .filter(TranslationWorkflowStep.translation_id == translation_id)
            .order_by(TranslationWorkflowStep.step_order)
            .all()
        )

        steps = []
        for step in workflow_steps:
            step_data = {
                "step_type": step.step_type,
                "step_order": step.step_order,
                "content": step.content,
                "notes": step.notes,
                "timestamp": step.timestamp.isoformat(),
                "model_info": json.loads(step.model_info) if step.model_info else None,
                "performance_metrics": json.loads(step.performance_metrics) if step.performance_metrics else None
            }

            # Add translated metadata for relevant steps
            if step.step_type in ["initial_translation", "revised_translation"]:
                if step.translated_title:
                    step_data["translated_title"] = step.translated_title
                if step.translated_poet_name:
                    step_data["translated_poet_name"] = step.translated_poet_name

            steps.append(step_data)

        return steps

    def _get_human_notes(self, translation_id: str) -> List[Dict[str, Any]]:
        """Get human translation notes"""

        human_note = (
            self.db.query(HumanNote)
            .filter(HumanNote.translation_id == translation_id)
            .first()
        )

        if not human_note:
            return [{
                "step_type": "human_translation",
                "step_order": 1,
                "content": "No human notes available.",
                "notes": "",
                "timestamp": None,
                "model_info": None,
                "performance_metrics": None
            }]

        return [{
            "step_type": "human_translation",
            "step_order": 1,
            "content": "Human translation with detailed notes.",
            "notes": human_note.note_text,
            "timestamp": human_note.created_at.isoformat(),
            "model_info": None,
            "performance_metrics": None
        }]

    def get_poem_translation_notes(self, poem_id: str, target_language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all translation notes for a poem"""

        query = (
            self.db.query(Translation, Poem)
            .join(Poem, Translation.poem_id == Poem.id)
            .filter(Poem.id == poem_id)
        )

        if target_language:
            query = query.filter(Translation.target_language == target_language)

        translations = query.order_by(Translation.created_at.desc()).all()

        results = []
        for translation_record, poem_record in translations:
            try:
                notes = self.get_translation_notes(translation_record.id)
                results.append(notes)
            except Exception as e:
                print(f"Error getting notes for translation {translation_record.id}: {e}")

        return results
```

#### 5.2 Add API Endpoint for Translation Notes
**File**: `src/vpsweb/webui/api/translations.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..services.translation_notes_service import TranslationNotesService
from ..repository.database import get_db

router = APIRouter(prefix="/translation-notes", tags=["translation-notes"])

@router.get("/{translation_id}")
async def get_translation_notes(
    translation_id: str,
    db: Session = Depends(get_db)
):
    """Get complete translation notes for a specific translation"""
    try:
        service = TranslationNotesService(db)
        notes = service.get_translation_notes(translation_id)
        return notes
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/poem/{poem_id}")
async def get_poem_translation_notes(
    poem_id: str,
    target_language: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all translation notes for a poem"""
    try:
        service = TranslationNotesService(db)
        notes = service.get_poem_translation_notes(poem_id, target_language)
        return {"poem_id": poem_id, "translations": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
```

### Phase 6: Frontend Integration (Week 3)

#### 6.1 Update Translation Detail Template
**File**: `src/vpsweb/webui/web/templates/poem_detail.html`

Add Translation Notes section:

```html
<!-- Translation Notes Section -->
{% if translation.translator_type == 'ai' %}
<div id="translation-notes" class="mt-8 bg-white rounded-lg shadow-md p-6">
    <h3 class="text-xl font-bold text-gray-900 mb-4">Translation Process Notes</h3>
    <div id="workflow-steps" class="space-y-6">
        <!-- Steps will be loaded via JavaScript -->
        <div class="text-gray-500">Loading translation notes...</div>
    </div>
</div>
{% else %}
<div id="translation-notes" class="mt-8 bg-white rounded-lg shadow-md p-6">
    <h3 class="text-xl font-bold text-gray-900 mb-4">Human Translation Notes</h3>
    <div id="human-notes" class="space-y-4">
        <!-- Human notes will be loaded via JavaScript -->
        <div class="text-gray-500">Loading human notes...</div>
    </div>
</div>
{% endif %}
```

#### 6.2 Add JavaScript for Translation Notes
**File**: `src/vpsweb/webui/web/templates/poem_detail.html`

```javascript
// Load translation notes
async function loadTranslationNotes(translationId) {
    try {
        const response = await fetch(`/api/v1/translation-notes/${translationId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const notes = await response.json();
        displayTranslationNotes(notes);

    } catch (error) {
        console.error('Error loading translation notes:', error);
        document.getElementById('translation-notes').innerHTML =
            '<div class="text-red-500">Failed to load translation notes</div>';
    }
}

function displayTranslationNotes(notes) {
    const container = notes.translation_type === 'ai' ?
        document.getElementById('workflow-steps') :
        document.getElementById('human-notes');

    if (!container) return;

    let html = '';

    notes.workflow_steps.forEach(step => {
        html += `
            <div class="border-l-4 border-blue-500 pl-4">
                <div class="flex items-center justify-between mb-2">
                    <h4 class="text-lg font-semibold text-gray-900">
                        ${formatStepTitle(step.step_type)}
                    </h4>
                    ${step.timestamp ? `<span class="text-sm text-gray-500">${formatTimestamp(step.timestamp)}</span>` : ''}
                </div>

                ${step.content ? `
                    <div class="mb-4">
                        <h5 class="text-sm font-medium text-gray-700 mb-2">Content:</h5>
                        <div class="bg-gray-50 p-3 rounded whitespace-pre-wrap">${escapeHtml(step.content)}</div>
                    </div>
                ` : ''}

                ${step.notes ? `
                    <div class="mb-4">
                        <h5 class="text-sm font-medium text-gray-700 mb-2">Notes:</h5>
                        <div class="bg-blue-50 p-3 rounded whitespace-pre-wrap">${escapeHtml(step.notes)}</div>
                    </div>
                ` : ''}

                ${step.performance_metrics ? `
                    <div class="text-sm text-gray-600">
                        <span class="mr-4">Tokens: ${step.performance_metrics.tokens_used || 0}</span>
                        <span class="mr-4">Duration: ${step.performance_metrics.duration ? step.performance_metrics.duration.toFixed(2) + 's' : 'N/A'}</span>
                        <span>Cost: ¥${step.performance_metrics.cost ? step.performance_metrics.cost.toFixed(4) : '0.0000'}</span>
                    </div>
                ` : ''}
            </div>
        `;
    });

    container.innerHTML = html;
}

function formatStepTitle(stepType) {
    const titles = {
        'initial_translation': 'Step 1: Initial Translation',
        'editor_review': 'Step 2: Editor Review',
        'revised_translation': 'Step 3: Revised Translation',
        'human_translation': 'Human Translation'
    };
    return titles[stepType] || stepType;
}

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load notes when page loads
document.addEventListener('DOMContentLoaded', function() {
    const translationId = '{{ translation.id }}';
    if (translationId) {
        loadTranslationNotes(translationId);
    }
});
```

### Phase 7: Data Migration Script (Week 4)

#### 7.1 Create Migration Script for Existing JSON Files
**File**: `scripts/migrate_json_to_db.py`

```python
#!/usr/bin/env python3
"""
Migration script to import existing JSON workflow data into the database.
This script reads existing JSON files and populates the translation_workflow_steps table.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vpsweb.repository.database import SessionLocal, engine
from vpsweb.repository.models import Translation, AILog, TranslationWorkflowStep
from vpsweb.utils.ulid_utils import generate_ulid

def migrate_json_files(json_dir: str = "outputs/json"):
    """Migrate all JSON files to database"""

    if not os.path.exists(json_dir):
        print(f"JSON directory not found: {json_dir}")
        return

    db = SessionLocal()
    migrated_count = 0
    error_count = 0

    try:
        # Find all JSON files
        json_files = []
        for root, dirs, files in os.walk(json_dir):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))

        print(f"Found {len(json_files)} JSON files to migrate")

        for json_file_path in json_files:
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract poem information
                poem_title = data.get('input', {}).get('metadata', {}).get('title', 'Unknown')
                poet_name = data.get('input', {}).get('metadata', {}).get('author', 'Unknown')
                target_lang = data.get('input', {}).get('target_lang', 'Unknown')

                # IMPROVED: Find translation with deterministic matching and safety checks
                translation = (
                    db.query(Translation)
                    .join(Poem, Translation.poem_id == Poem.id)
                    .outerjoin(AILog, Translation.id == AILog.translation_id)
                    .outerjoin(TranslationWorkflowStep,
                              and_(Translation.id == TranslationWorkflowStep.translation_id,
                                   TranslationWorkflowStep.workflow_id == workflow_id))
                    .filter(
                        Poem.poem_title == poem_title,
                        Poem.poet_name == poet_name,
                        Translation.target_language == target_lang,
                        Translation.translator_type == 'ai',
                        AILog.id == None,  # Translation without AI log yet
                        TranslationWorkflowStep.id == None  # No workflow steps yet
                    )
                    .order_by(Translation.created_at.desc())  # Deterministic ordering
                    .first()
                )

                if not translation:
                    print(f"⚠️  No matching translation found for: {poet_name} - {poem_title} ({target_lang})")
                    continue

                # ADDITIONAL SAFETY: Verify workflow ID uniqueness
                existing_workflow = (
                    db.query(TranslationWorkflowStep)
                    .filter(TranslationWorkflowStep.workflow_id == workflow_id)
                    .first()
                )

                if existing_workflow:
                    print(f"⏭️  Skipping {json_file_path} - workflow ID already exists: {workflow_id}")
                    continue

                # IMPROVED: Verify translation details match JSON content
                if not _verify_translation_match(translation, data):
                    print(f"⚠️  Translation details don't match JSON content: {json_file_path}")
                    continue

                # Create AI log record
                ai_log_id = generate_ulid()
                ai_log = AILog(
                    id=ai_log_id,
                    translation_id=translation.id,
                    model_name=data.get('initial_translation', {}).get('model_info', {}).get('model', 'Unknown'),
                    workflow_mode=data.get('workflow_mode', 'hybrid'),
                    token_usage_json=json.dumps({"total_tokens": data.get('total_tokens', 0)}),
                    cost_info_json=json.dumps({"total_cost": data.get('total_cost', 0)}),
                    runtime_seconds=data.get('duration_seconds', 0),
                    notes=f"Migrated from JSON: {os.path.basename(json_file_path)}"
                )
                db.add(ai_log)
                db.flush()

                # IMPROVED: Create workflow steps with dedicated metric columns
                workflow_id = data.get('workflow_id', generate_ulid())
                steps = _create_workflow_steps_from_json(data, translation.id, ai_log_id, workflow_id)

                for step in steps:
                    db.add(step)

                db.commit()
                migrated_count += 1
                print(f"✅ Migrated: {os.path.basename(json_file_path)} ({len(steps)} steps)")

            except Exception as e:
                error_count += 1
                print(f"❌ Error migrating {json_file_path}: {e}")
                db.rollback()
                continue

    finally:
        db.close()

    print(f"\nMigration complete:")
    print(f"  ✅ Successfully migrated: {migrated_count} files")
    print(f"  ❌ Errors: {error_count} files")

def _verify_translation_match(translation: Translation, json_data: Dict[str, Any]) -> bool:
    """Verify that translation record matches JSON content"""
    # Check if target language matches
    expected_lang = json_data.get('input', {}).get('target_lang')
    if translation.target_language != expected_lang:
        return False

    # Check if final translation content matches (basic validation)
    expected_final = json_data.get('revised_translation', {}).get('revised_translation', '')
    if not translation.translated_text or not expected_final:
        return False

    # Additional validation logic as needed
    return True

def _create_workflow_steps_from_json(data: Dict[str, Any],
                                   translation_id: str,
                                   ai_log_id: str,
                                   workflow_id: str) -> List[TranslationWorkflowStep]:
    """Create workflow steps from JSON data with dedicated metric columns and proper error handling"""
    steps = []

    step_configs = [
        ("initial_translation", "initial_translation", 1),
        ("editor_review", "editor_suggestions", 2),
        ("revised_translation", "revised_translation", 3)
    ]

    for json_key, content_field, step_order in step_configs:
        if json_key in data:
            step_data = data[json_key]

            step = TranslationWorkflowStep(
                id=generate_ulid(),
                translation_id=translation_id,
                ai_log_id=ai_log_id,
                workflow_id=workflow_id,
                step_type=json_key,
                step_order=step_order,
                content=step_data.get(content_field, ''),
                notes=step_data.get(f'{json_key}_notes', ''),
                model_info=json.dumps(step_data.get('model_info', {})),
                # NEW: Use dedicated metric columns
                tokens_used=step_data.get('tokens_used', 0),
                prompt_tokens=step_data.get('prompt_tokens', 0),
                completion_tokens=step_data.get('completion_tokens', 0),
                duration_seconds=step_data.get('duration', 0.0),
                cost=step_data.get('cost', 0.0),
                # Keep additional metrics in JSON
                additional_metrics=json.dumps({
                    "provider": step_data.get('model_info', {}).get('provider'),
                    "model": step_data.get('model_info', {}).get('model'),
                    "temperature": step_data.get('model_info', {}).get('temperature')
                }),
                # Set translated metadata for relevant steps
                translated_title=step_data.get('translated_poem_title') if step_order in [1, 3] else None,
                translated_poet_name=step_data.get('translated_poet_name') if step_order in [1, 3] else None,
                timestamp=datetime.fromisoformat(step_data.get('timestamp', datetime.now().isoformat())),
                created_at=datetime.now()
            )
            steps.append(step)

    return steps

if __name__ == "__main__":
    migrate_json_files()
```

### Phase 8: Testing and Validation (Week 4)

#### 8.1 Unit Tests for New Functionality
**File**: `tests/unit/test_translation_workflow_steps.py`

```python
import pytest
from vpsweb.repository.models import TranslationWorkflowStep
from vpsweb.repository.crud import TranslationWorkflowStepCRUD
from vpsweb.models.translation import TranslationOutput

class TestTranslationWorkflowStepCRUD:
    def test_create_workflow_steps(self, db_session, sample_translation, sample_ai_log):
        """Test creating workflow steps from TranslationOutput"""
        crud = TranslationWorkflowStepCRUD(db_session)

        # Create sample workflow data
        workflow_data = {
            "workflow_id": "01H8GD8C2TEST123456789ABCDEF",
            "initial_translation": {
                "initial_translation": "Test initial translation",
                "initial_translation_notes": "Test initial notes",
                "model_info": {"provider": "tongyi", "model": "qwen-plus"},
                "tokens_used": 1000,
                "prompt_tokens": 500,
                "completion_tokens": 500,
                "duration": 30.5,
                "cost": 0.001,
                "translated_poem_title": "Test Title",
                "translated_poet_name": "Test Poet",
                "timestamp": "2025-01-XXT12:00:00"
            },
            "editor_review": {
                "editor_suggestions": "Test suggestions",
                "model_info": {"provider": "deepseek", "model": "reasoner"},
                "tokens_used": 2000,
                "prompt_tokens": 1000,
                "completion_tokens": 1000,
                "duration": 60.0,
                "cost": 0.002,
                "timestamp": "2025-01-XXT12:01:00"
            },
            "revised_translation": {
                "revised_translation": "Test revised translation",
                "revised_translation_notes": "Test revised notes",
                "model_info": {"provider": "tongyi", "model": "qwen-plus"},
                "tokens_used": 1500,
                "prompt_tokens": 750,
                "completion_tokens": 750,
                "duration": 45.0,
                "cost": 0.0015,
                "refined_translated_poem_title": "Test Title Refined",
                "refined_translated_poet_name": "Test Poet Refined",
                "timestamp": "2025-01-XXT12:02:00"
            }
        }

        # Create workflow steps
        steps = crud.create_workflow_steps(
            translation_id=sample_translation.id,
            ai_log_id=sample_ai_log.id,
            workflow_id=workflow_data["workflow_id"],
            workflow_data=workflow_data
        )

        # Verify results
        assert len(steps) == 3

        # Check initial translation step
        initial_step = steps[0]
        assert initial_step.step_type == "initial_translation"
        assert initial_step.step_order == 1
        assert initial_step.content == "Test initial translation"
        assert initial_step.notes == "Test initial notes"
        assert initial_step.translated_title == "Test Title"
        assert initial_step.translated_poet_name == "Test Poet"

        # Check editor review step
        editor_step = steps[1]
        assert editor_step.step_type == "editor_review"
        assert editor_step.step_order == 2
        assert editor_step.content == "Test suggestions"

        # Check revised translation step
        revised_step = steps[2]
        assert revised_step.step_type == "revised_translation"
        assert revised_step.step_order == 3
        assert revised_step.content == "Test revised translation"
        assert revised_step.notes == "Test revised notes"
        assert revised_step.translated_title == "Test Title Refined"
        assert revised_step.translated_poet_name == "Test Poet Refined"
```

#### 8.2 Integration Tests
**File**: `tests/integration/test_translation_notes_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from vpsweb.webui.main import app
from vpsweb.repository.database import SessionLocal
from vpsweb.webui.services.translation_notes_service import TranslationNotesService

class TestTranslationNotesAPI:
    def test_get_ai_translation_notes(self, client: TestClient, sample_ai_translation_with_steps):
        """Test getting AI translation notes"""
        response = client.get(f"/api/v1/translation-notes/{sample_ai_translation_with_steps.id}")

        assert response.status_code == 200

        notes = response.json()
        assert notes["translation_type"] == "ai"
        assert len(notes["workflow_steps"]) == 3

        # Check step types
        step_types = [step["step_type"] for step in notes["workflow_steps"]]
        assert "initial_translation" in step_types
        assert "editor_review" in step_types
        assert "revised_translation" in step_types

        # Check content exists
        for step in notes["workflow_steps"]:
            assert "content" in step
            assert "step_order" in step
            assert "timestamp" in step

    def test_get_human_translation_notes(self, client: TestClient, sample_human_translation_with_note):
        """Test getting human translation notes"""
        response = client.get(f"/api/v1/translation-notes/{sample_human_translation_with_note.id}")

        assert response.status_code == 200

        notes = response.json()
        assert notes["translation_type"] == "human"
        assert len(notes["workflow_steps"]) == 1

        step = notes["workflow_steps"][0]
        assert step["step_type"] == "human_translation"
        assert "notes" in step
```

### Phase 9: Documentation and Cleanup (Week 4)

#### 9.1 Update Documentation
**File**: `docs/database-schema.md`

```markdown
# Database Schema

## Overview

VPSWeb uses a 5-table schema to store poetry translations and detailed workflow information.

## Tables

### 1. poems
Original poetry content.

### 2. translations
Final translation results.

### 3. ai_logs
AI workflow execution records.

### 4. translation_workflow_steps ⭐ NEW
Detailed T-E-T workflow step content.

### 5. human_notes
Human translation annotations.

## Relationships

```
poem (1) → (N) translations
   ├── translation.ai (1) → (1) ai_log (1) → (3) translation_workflow_steps
   └── translation.human (1) → (1) human_note
```

## Usage Examples

See [api-patterns.md](api-patterns.md) for detailed usage examples.
```

#### 9.2 Update API Documentation
**File**: `docs/api-patterns.md`

```markdown
# Translation Notes API

## Get Translation Notes

```http
GET /api/v1/translation-notes/{translation_id}
```

Response:
```json
{
  "translation_id": "01K8GD8D3ABCD123456789EFGH",
  "translation_type": "ai",
  "target_language": "Chinese",
  "poem": {
    "id": "01K8GD8C28JQEQ1WTRPFENWBSM",
    "title": "The Warm and the Cold",
    "author": "Ted Hughes",
    "original_text": "Freezing dusk is closing...",
    "source_language": "English"
  },
  "workflow_steps": [
    {
      "step_type": "initial_translation",
      "step_order": 1,
      "content": "冻结的暮色正缓缓合拢...",
      "notes": "Detailed translation reasoning...",
      "timestamp": "2025-01-XXT12:00:00Z",
      "model_info": {"provider": "tongyi", "model": "qwen-plus"},
      "performance_metrics": {"tokens_used": 2638, "duration": 40.84, "cost": 0.0036812}
    }
  ]
}
```
```

## Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| **Week 1** | Database Schema & ID Standardization | Alembic migration, SQLAlchemy models, ULID standardization |
| **Week 2** | CRUD Operations & Adapter Enhancement | TranslationWorkflowStep CRUD, VPSWeb adapter updates |
| **Week 3** | API Layer & Frontend Integration | Translation notes service, API endpoints, frontend UI |
| **Week 4** | Migration & Testing | Data migration script, comprehensive tests, documentation |

## Expert Feedback Integration

Based on expert review, the following critical improvements have been incorporated:

### ✅ Schema Design: Dedicated Metric Columns
**Issue**: Storing metrics in JSON makes SQL aggregations difficult and less performant.
**Solution**: Added dedicated numeric columns for key metrics while keeping JSON for flexibility.

**Benefits**:
```sql
-- Now possible with dedicated columns:
SELECT
    step_type,
    AVG(cost) as avg_cost,
    AVG(duration_seconds) as avg_duration,
    SUM(tokens_used) as total_tokens
FROM translation_workflow_steps
GROUP BY step_type;

-- Performance analysis:
SELECT model_name, AVG(cost)
FROM translation_workflow_steps tws
JOIN ai_logs al ON tws.ai_log_id = al.id
WHERE tws.step_type = 'editor_review'
GROUP BY model_name
ORDER BY avg_cost DESC;
```

### ✅ Transactional Integrity: Unit of Work Pattern
**Issue**: Nested commits violate proper transaction boundaries.
**Solution**: Removed redundant commits, implemented single transaction boundary.

**Benefits**:
- Atomicity: All-or-nothing operations across related entities
- Reusability: CRUD functions become more testable and composable
- Consistency: Single commit point for complex business operations
- Error Handling: Cleaner rollback scenarios

### ✅ Migration Script Robustness: Deterministic Matching
**Issue**: Arbitrary matching could link data incorrectly on duplicate translations.
**Solution**: Added deterministic matching with conflict prevention and validation.

**Safety Features**:
- Workflow ID uniqueness checking
- Translation content validation
- Deterministic ordering (created_at DESC)
- Idempotent migration (safe to run multiple times)

## Updated Success Criteria

1. ✅ **Database Storage**: All T-E-T workflow content stored in database with queryable metrics
2. ✅ **JSON Backup**: JSON files generated as write-only backups
3. ✅ **API Access**: Complete translation notes available via REST API with analytics support
4. ✅ **Frontend Integration**: Translation Notes page displays database content
5. ✅ **Data Migration**: Existing JSON data migrated safely and deterministically
6. ✅ **Performance**: Fast queries with dedicated metric indexes and SQL aggregations
7. ✅ **Consistency**: ULID IDs used throughout system
8. ✅ **Transaction Integrity**: Atomic operations with proper rollback handling
9. ✅ **Migration Safety**: No data corruption, idempotent and reproducible

## Risk Mitigation

1. **Data Loss**: JSON backups maintained during transition
2. **Performance**: Enhanced indexing strategy with dedicated metric columns
3. **Rollback**: Alembic migration includes rollback path
4. **Testing**: Unit and integration tests for all new functionality
5. **Documentation**: Complete API and schema documentation provided
6. **Data Integrity**: Transaction boundaries prevent partial data corruption
7. **Migration Safety**: Deterministic matching prevents relationship errors

## Next Steps

After implementation:
1. Monitor database performance with new workflow steps table
2. Gather feedback on Translation Notes page usability
3. Consider adding workflow step comparison features
4. Evaluate need for additional workflow analytics (now easily possible with SQL)
5. Plan for future workflow step types (e.g., collaborative editing)
6. Leverage new analytical capabilities for cost optimization and model comparison

---

**Status**: 📋 Planning Complete with Expert Feedback
**Next Action**: Begin Phase 1 - Database Schema Implementation