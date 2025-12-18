"""Add translation_workflow_steps table for detailed T-E-T workflow content

Revision ID: 08eb9e1eac6d
Revises: add_poet_file_organization_fields
Create Date: 2025-10-27 16:16:46.335753

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08eb9e1eac6d"
down_revision: Union[str, Sequence[str], None] = "add_poet_file_organization_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create translation_workflow_steps table
    op.create_table(
        "translation_workflow_steps",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("translation_id", sa.String(length=26), nullable=False, index=True),
        sa.Column("ai_log_id", sa.String(length=26), nullable=False, index=True),
        sa.Column("workflow_id", sa.String(length=26), nullable=False, index=True),
        sa.Column("step_type", sa.String(length=30), nullable=False, index=True),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("model_info", sa.Text(), nullable=True),
        # NEW: Dedicated columns for key metrics (SQL-queryable)
        sa.Column("tokens_used", sa.Integer(), nullable=True, index=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True, index=True),
        sa.Column("cost", sa.Float(), nullable=True, index=True),
        # Keep JSON for additional/future metrics (flexibility)
        sa.Column("additional_metrics", sa.Text(), nullable=True),
        # Translated metadata (for initial_translation and revised_translation steps)
        sa.Column("translated_title", sa.String(length=500), nullable=True),
        sa.Column("translated_poet_name", sa.String(length=200), nullable=True),
        # Timestamps
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ai_log_id"], ["ai_logs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["translation_id"], ["translations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "idx_workflow_steps_translation_id",
        "translation_workflow_steps",
        ["translation_id"],
    )
    op.create_index(
        "idx_workflow_steps_ai_log_id",
        "translation_workflow_steps",
        ["ai_log_id"],
    )
    op.create_index(
        "idx_workflow_steps_workflow_id",
        "translation_workflow_steps",
        ["workflow_id"],
    )
    op.create_index(
        "idx_workflow_steps_type_order",
        "translation_workflow_steps",
        ["translation_id", "step_order"],
    )

    # Performance indexes for analytics
    op.create_index("idx_workflow_steps_cost", "translation_workflow_steps", ["cost"])
    op.create_index(
        "idx_workflow_steps_duration",
        "translation_workflow_steps",
        ["duration_seconds"],
    )
    op.create_index(
        "idx_workflow_steps_tokens",
        "translation_workflow_steps",
        ["tokens_used"],
    )
    op.create_index(
        "idx_workflow_steps_step_metrics",
        "translation_workflow_steps",
        ["step_type", "cost", "duration_seconds"],
    )

    # Skip check constraint for SQLite compatibility - enforced at application level
    # Note: SQLite doesn't support ALTER of constraints directly


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the table
    op.drop_table("translation_workflow_steps")
