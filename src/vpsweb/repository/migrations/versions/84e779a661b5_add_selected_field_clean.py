"""add selected field to poems table

Revision ID: 84e779a661b5
Revises: 7e0737517096
Create Date: 2025-11-23 11:53:25.399555

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "84e779a661b5"
down_revision: Union[str, Sequence[str], None] = "08eb9e1eac6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add selected column to poems table
    op.add_column(
        "poems",
        sa.Column("selected", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create index for selected field
    op.create_index("idx_poems_selected", "poems", ["selected"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index
    op.drop_index("idx_poems_selected", table_name="poems")

    # Drop the selected column
    op.drop_column("poems", "selected")
