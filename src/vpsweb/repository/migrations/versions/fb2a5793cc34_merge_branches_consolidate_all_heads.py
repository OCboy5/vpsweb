"""merge branches - consolidate all heads

Revision ID: fb2a5793cc34
Revises: 84e779a661b5, 90eb279fd688, add_background_briefing_report_table
Create Date: 2025-12-15 18:48:04.145419

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "fb2a5793cc34"
down_revision: Union[str, Sequence[str], None] = (
    "84e779a661b5",
    "90eb279fd688",
    "add_background_briefing_report_table",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name):
    """Check if table exists"""
    result = conn.execute(
        text(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        )
    ).scalar()
    return result is not None


def _column_exists(conn, table_name, column_name):
    """Check if column exists in table"""
    result = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(col[1] == column_name for col in result)


def _index_exists(conn, index_name):
    """Check if index exists"""
    result = conn.execute(
        text(
            f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
        )
    ).scalar()
    return result is not None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Apply changes from 94bcac9585c9 (composite indexes)
    # Composite indexes for Poem table
    if not _index_exists(conn, "idx_poems_poet_name_created_at"):
        op.create_index(
            "idx_poems_poet_name_created_at",
            "poems",
            ["poet_name", "created_at"],
        )
    if not _index_exists(conn, "idx_poems_poet_title"):
        op.create_index("idx_poems_poet_title", "poems", ["poet_name", "poem_title"])
    if not _index_exists(conn, "idx_poems_language_created_at"):
        op.create_index(
            "idx_poems_language_created_at",
            "poems",
            ["source_language", "created_at"],
        )

    # Composite indexes for Translation table
    if not _index_exists(conn, "idx_translations_poem_language"):
        op.create_index(
            "idx_translations_poem_language",
            "translations",
            ["poem_id", "target_language"],
        )
    if not _index_exists(conn, "idx_translations_type_language"):
        op.create_index(
            "idx_translations_type_language",
            "translations",
            ["translator_type", "target_language"],
        )
    if not _index_exists(conn, "idx_translations_poem_type"):
        op.create_index(
            "idx_translations_poem_type",
            "translations",
            ["poem_id", "translator_type"],
        )
    if not _index_exists(conn, "idx_translations_language_created_at"):
        op.create_index(
            "idx_translations_language_created_at",
            "translations",
            ["target_language", "created_at"],
        )
    if not _index_exists(conn, "idx_translations_composite_created"):
        op.create_index(
            "idx_translations_composite_created",
            "translations",
            ["poem_id", "created_at"],
        )

    # Apply changes from add_poet_file_organization_fields
    # Add file organization fields to translations table
    if not _column_exists(conn, "translations", "poet_subdirectory"):
        op.add_column(
            "translations",
            sa.Column("poet_subdirectory", sa.String(length=100), nullable=True),
        )
    if not _column_exists(conn, "translations", "relative_json_path"):
        op.add_column(
            "translations",
            sa.Column("relative_json_path", sa.String(length=500), nullable=True),
        )
    if not _column_exists(conn, "translations", "file_category"):
        # Create enum if not exists
        file_category_enum = sa.Enum(
            "recent", "poet_archive", name="file_category_enum"
        )
        file_category_enum.create(op.get_bind())
        op.add_column(
            "translations",
            sa.Column("file_category", file_category_enum, nullable=True),
        )

    # Add indexes for new fields
    if not _index_exists(conn, "idx_translations_poet_subdir"):
        op.create_index(
            "idx_translations_poet_subdir",
            "translations",
            ["poet_subdirectory"],
            unique=False,
        )
    if not _index_exists(conn, "idx_translations_file_category"):
        op.create_index(
            "idx_translations_file_category",
            "translations",
            ["file_category"],
            unique=False,
        )
    if not _index_exists(conn, "idx_translations_composite_file"):
        op.create_index(
            "idx_translations_composite_file",
            "translations",
            ["poet_subdirectory", "file_category"],
            unique=False,
        )

    # Apply changes from 08eb9e1eac6d (translation_workflow_steps table)
    if not _table_exists(conn, "translation_workflow_steps"):
        # Create translation_workflow_steps table
        op.create_table(
            "translation_workflow_steps",
            sa.Column("id", sa.String(length=26), nullable=False),
            sa.Column(
                "translation_id",
                sa.String(length=26),
                nullable=False,
                index=True,
            ),
            sa.Column("ai_log_id", sa.String(length=26), nullable=False, index=True),
            sa.Column("workflow_id", sa.String(length=26), nullable=False, index=True),
            sa.Column("step_type", sa.String(length=30), nullable=False, index=True),
            sa.Column("step_order", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("model_info", sa.Text(), nullable=True),
            sa.Column("tokens_used", sa.Integer(), nullable=True, index=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True, index=True),
            sa.Column("cost", sa.Float(), nullable=True, index=True),
            sa.Column("additional_metrics", sa.Text(), nullable=True),
            sa.Column("translated_title", sa.String(length=500), nullable=True),
            sa.Column("translated_poet_name", sa.String(length=200), nullable=True),
            sa.Column(
                "manual_mode",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
            sa.Column("user_model_name", sa.String(length=200), nullable=True),
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
        op.create_index(
            "idx_workflow_steps_cost", "translation_workflow_steps", ["cost"]
        )
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
        op.create_index(
            "idx_workflow_steps_manual_mode",
            "translation_workflow_steps",
            ["manual_mode"],
        )

    # Apply changes from add_background_briefing_report_table
    if not _table_exists(conn, "background_briefing_reports"):
        # Create background_briefing_reports table
        op.create_table(
            "background_briefing_reports",
            sa.Column("id", sa.String(length=26), nullable=False),
            sa.Column(
                "poem_id",
                sa.String(length=26),
                nullable=False,
                unique=True,
                index=True,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("model_info", sa.Text(), nullable=True),
            sa.Column("tokens_used", sa.Integer(), nullable=True, index=True),
            sa.Column("cost", sa.Float(), nullable=True, index=True),
            sa.Column("time_spent", sa.Float(), nullable=True, index=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["poem_id"], ["poems.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

        # Create indexes
        op.create_index("idx_bbr_poem_id", "background_briefing_reports", ["poem_id"])
        op.create_index(
            "idx_bbr_created_at", "background_briefing_reports", ["created_at"]
        )
        op.create_index("idx_bbr_cost", "background_briefing_reports", ["cost"])
        op.create_index(
            "idx_bbr_time_spent", "background_briefing_reports", ["time_spent"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_bbr_time_spent", table_name="background_briefing_reports")
    op.drop_index("idx_bbr_cost", table_name="background_briefing_reports")
    op.drop_index("idx_bbr_created_at", table_name="background_briefing_reports")
    op.drop_index("idx_bbr_poem_id", table_name="background_briefing_reports")

    # Drop background_briefing_reports table
    op.drop_table("background_briefing_reports")

    # Drop workflow steps indexes
    op.drop_index(
        "idx_workflow_steps_manual_mode",
        table_name="translation_workflow_steps",
    )
    op.drop_index(
        "idx_workflow_steps_step_metrics",
        table_name="translation_workflow_steps",
    )
    op.drop_index("idx_workflow_steps_tokens", table_name="translation_workflow_steps")
    op.drop_index(
        "idx_workflow_steps_duration", table_name="translation_workflow_steps"
    )
    op.drop_index("idx_workflow_steps_cost", table_name="translation_workflow_steps")
    op.drop_index(
        "idx_workflow_steps_type_order",
        table_name="translation_workflow_steps",
    )
    op.drop_index(
        "idx_workflow_steps_workflow_id",
        table_name="translation_workflow_steps",
    )
    op.drop_index(
        "idx_workflow_steps_ai_log_id", table_name="translation_workflow_steps"
    )
    op.drop_index(
        "idx_workflow_steps_translation_id",
        table_name="translation_workflow_steps",
    )

    # Drop translation_workflow_steps table
    op.drop_table("translation_workflow_steps")

    # Drop indexes
    op.drop_index("idx_translations_composite_file", table_name="translations")
    op.drop_index("idx_translations_file_category", table_name="translations")
    op.drop_index("idx_translations_poet_subdir", table_name="translations")

    # Drop columns
    op.drop_column("translations", "file_category")
    op.drop_column("translations", "relative_json_path")
    op.drop_column("translations", "poet_subdirectory")

    # Drop file_category enum
    sa.Enum(name="file_category_enum").drop(op.get_bind())

    # Drop composite indexes
    op.drop_index("idx_translations_composite_created", table_name="translations")
    op.drop_index("idx_translations_language_created_at", table_name="translations")
    op.drop_index("idx_translations_poem_type", table_name="translations")
    op.drop_index("idx_translations_type_language", table_name="translations")
    op.drop_index("idx_translations_poem_language", table_name="translations")

    op.drop_index("idx_poems_language_created_at", table_name="poems")
    op.drop_index("idx_poems_poet_title", table_name="poems")
    op.drop_index("idx_poems_poet_name_created_at", table_name="poems")
