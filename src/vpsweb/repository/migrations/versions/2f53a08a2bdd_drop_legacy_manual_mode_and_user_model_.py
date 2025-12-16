"""Drop legacy manual_mode and user_model_name columns from translation_workflow_steps

Revision ID: 2f53a08a2bdd
Revises: fb2a5793cc34
Create Date: 2025-12-16 00:35:04.334254

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f53a08a2bdd"
down_revision: Union[str, Sequence[str], None] = "fb2a5793cc34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("translation_workflow_steps", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("idx_workflow_steps_manual_mode"))
        batch_op.drop_column("manual_mode")
        batch_op.drop_column("user_model_name")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("translation_workflow_steps", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("user_model_name", sa.VARCHAR(length=200), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "manual_mode",
                sa.BOOLEAN(),
                server_default=sa.text("(FALSE)"),
                nullable=True,
            )
        )
        batch_op.create_index(
            batch_op.f("idx_workflow_steps_manual_mode"), ["manual_mode"], unique=False
        )
