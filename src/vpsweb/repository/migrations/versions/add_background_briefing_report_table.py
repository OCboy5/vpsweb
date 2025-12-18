"""add_background_briefing_report_table

Revision ID: add_background_briefing_report_table
Revises: 08eb9e1eac6d
Create Date: 2025-11-15 15:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_background_briefing_report_table"
down_revision = "08eb9e1eac6d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create background_briefing_reports table
    op.create_table(
        "background_briefing_reports",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("poem_id", sa.String(length=26), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_info", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("time_spent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["poem_id"], ["poems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("poem_id"),
    )

    # Create indexes
    op.create_index(
        "idx_bbr_poem_id",
        "background_briefing_reports",
        ["poem_id"],
        unique=False,
    )
    op.create_index(
        "idx_bbr_created_at",
        "background_briefing_reports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_bbr_cost", "background_briefing_reports", ["cost"], unique=False
    )
    op.create_index(
        "idx_bbr_time_spent",
        "background_briefing_reports",
        ["time_spent"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "idx_bbr_time_spent", table_name="background_briefing_reports"
    )
    op.drop_index("idx_bbr_cost", table_name="background_briefing_reports")
    op.drop_index(
        "idx_bbr_created_at", table_name="background_briefing_reports"
    )
    op.drop_index("idx_bbr_poem_id", table_name="background_briefing_reports")

    # Drop table
    op.drop_table("background_briefing_reports")
