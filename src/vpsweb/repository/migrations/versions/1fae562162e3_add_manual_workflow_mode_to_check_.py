"""Add manual workflow mode to check constraint

Revision ID: 1fae562162e3
Revises: 2f53a08a2bdd
Create Date: 2025-12-16 22:27:20.404657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fae562162e3'
down_revision: Union[str, Sequence[str], None] = '2f53a08a2bdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use batch mode for SQLite which doesn't support direct constraint alteration
    with op.batch_alter_table('ai_logs') as batch_op:
        # Create new check constraint that includes 'manual'
        # Note: The constraint might not exist in the actual database, only in the model
        batch_op.create_check_constraint(
            'ck_workflow_mode',
            sa.text("workflow_mode IN ('reasoning', 'non_reasoning', 'hybrid', 'manual')")
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Use batch mode for SQLite
    with op.batch_alter_table('ai_logs') as batch_op:
        # Drop the check constraint with manual
        batch_op.drop_constraint('ck_workflow_mode', type_='check')

        # Recreate original check constraint without manual
        batch_op.create_check_constraint(
            'ck_workflow_mode',
            sa.text("workflow_mode IN ('reasoning', 'non_reasoning', 'hybrid')")
        )
