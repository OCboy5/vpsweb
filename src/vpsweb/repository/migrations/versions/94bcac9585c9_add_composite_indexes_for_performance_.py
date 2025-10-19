"""Add composite indexes for performance optimization

Revision ID: 94bcac9585c9
Revises: 001_initial_schema
Create Date: 2025-10-19 20:09:45.460734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94bcac9585c9'
down_revision: Union[str, Sequence[str], None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Composite indexes for Poem table
    # Common queries: "Get poems by poet with pagination" and "Search poems by poet and title"
    op.create_index('idx_poems_poet_name_created_at', 'poems', ['poet_name', 'created_at'])
    op.create_index('idx_poems_poet_title', 'poems', ['poet_name', 'poem_title'])
    op.create_index('idx_poems_language_created_at', 'poems', ['source_language', 'created_at'])

    # Composite indexes for Translation table
    # Common queries: "Get translations by poem and language" and "Filter by type and language"
    op.create_index('idx_translations_poem_language', 'translations', ['poem_id', 'target_language'])
    op.create_index('idx_translations_type_language', 'translations', ['translator_type', 'target_language'])
    op.create_index('idx_translations_poem_type', 'translations', ['poem_id', 'translator_type'])
    op.create_index('idx_translations_language_created_at', 'translations', ['target_language', 'created_at'])

    # Composite indexes for AILog table
    # Common queries: "Get AI logs by model with pagination" and "Performance analysis by model and mode"
    op.create_index('idx_ai_logs_model_created_at', 'ai_logs', ['model_name', 'created_at'])
    op.create_index('idx_ai_logs_mode_created_at', 'ai_logs', ['workflow_mode', 'created_at'])
    op.create_index('idx_ai_logs_translation_model', 'ai_logs', ['translation_id', 'model_name'])

    # Composite indexes for WorkflowTask table
    # Common queries: "Get active tasks by status" and "Task monitoring by poem and status"
    op.create_index('idx_workflow_tasks_status_created_at', 'workflow_tasks', ['status', 'created_at'])
    op.create_index('idx_workflow_tasks_poem_status', 'workflow_tasks', ['poem_id', 'status'])
    op.create_index('idx_workflow_tasks_mode_status', 'workflow_tasks', ['workflow_mode', 'status'])
    op.create_index('idx_workflow_tasks_poem_mode', 'workflow_tasks', ['poem_id', 'workflow_mode'])

    # Composite indexes for HumanNote table
    # Common queries: "Get notes by translation with pagination"
    op.create_index('idx_human_notes_translation_created_at', 'human_notes', ['translation_id', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""

    # Drop composite indexes for Poem table
    op.drop_index('idx_poems_poet_name_created_at', 'poems')
    op.drop_index('idx_poems_poet_title', 'poems')
    op.drop_index('idx_poems_language_created_at', 'poems')

    # Drop composite indexes for Translation table
    op.drop_index('idx_translations_poem_language', 'translations')
    op.drop_index('idx_translations_type_language', 'translations')
    op.drop_index('idx_translations_poem_type', 'translations')
    op.drop_index('idx_translations_language_created_at', 'translations')

    # Drop composite indexes for AILog table
    op.drop_index('idx_ai_logs_model_created_at', 'ai_logs')
    op.drop_index('idx_ai_logs_mode_created_at', 'ai_logs')
    op.drop_index('idx_ai_logs_translation_model', 'ai_logs')

    # Drop composite indexes for WorkflowTask table
    op.drop_index('idx_workflow_tasks_status_created_at', 'workflow_tasks')
    op.drop_index('idx_workflow_tasks_poem_status', 'workflow_tasks')
    op.drop_index('idx_workflow_tasks_mode_status', 'workflow_tasks')
    op.drop_index('idx_workflow_tasks_poem_mode', 'workflow_tasks')

    # Drop composite indexes for HumanNote table
    op.drop_index('idx_human_notes_translation_created_at', 'human_notes')
