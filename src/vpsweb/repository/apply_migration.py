#!/usr/bin/env python3
"""
Apply initial migration to create database tables
"""

import os
import sys
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

# Create database engine
database_url = "sqlite:///./repository_root/repo.db"
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def create_tables():
    """Create all tables using SQL"""

    # Ensure repository_root directory exists
    repo_dir = Path("repository_root")
    repo_dir.mkdir(exist_ok=True)

    # Create tables
    with engine.connect() as conn:
        # Create poems table
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS poems (
                id VARCHAR(26) PRIMARY KEY,
                poet_name VARCHAR(200) NOT NULL,
                poem_title VARCHAR(300) NOT NULL,
                source_language VARCHAR(10) NOT NULL,
                original_text TEXT NOT NULL,
                metadata_json TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """
            )
        )

        # Create translations table
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS translations (
                id VARCHAR(26) PRIMARY KEY,
                poem_id VARCHAR(26) NOT NULL,
                translator_type VARCHAR(10) NOT NULL,
                translator_info VARCHAR(200),
                target_language VARCHAR(10) NOT NULL,
                translated_text TEXT NOT NULL,
                quality_rating INTEGER,
                raw_path VARCHAR(500),
                created_at DATETIME NOT NULL,
                FOREIGN KEY (poem_id) REFERENCES poems(id) ON DELETE CASCADE
            )
        """
            )
        )

        # Create ai_logs table
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS ai_logs (
                id VARCHAR(26) PRIMARY KEY,
                translation_id VARCHAR(26) NOT NULL,
                model_name VARCHAR(100) NOT NULL,
                workflow_mode VARCHAR(20) NOT NULL,
                token_usage_json TEXT,
                cost_info_json TEXT,
                runtime_seconds INTEGER,
                notes TEXT,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE
            )
        """
            )
        )

        # Create human_notes table
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS human_notes (
                id VARCHAR(26) PRIMARY KEY,
                translation_id VARCHAR(26) NOT NULL,
                note_text TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE
            )
        """
            )
        )

        # Create indexes
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_poems_created_at ON poems (created_at)"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_poems_poet_name ON poems (poet_name)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_poems_title ON poems (poem_title)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_poems_language ON poems (source_language)"
            )
        )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_translations_poem_id ON translations (poem_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_translations_type ON translations (translator_type)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_translations_language ON translations (target_language)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_translations_created_at ON translations (created_at)"
            )
        )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_ai_logs_translation_id ON ai_logs (translation_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_ai_logs_model_name ON ai_logs (model_name)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_ai_logs_workflow_mode ON ai_logs (workflow_mode)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_ai_logs_created_at ON ai_logs (created_at)"
            )
        )

        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_human_notes_translation_id ON human_notes (translation_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_human_notes_created_at ON human_notes (created_at)"
            )
        )

        conn.commit()

    print("Database tables created successfully!")
    print("Tables: poems, translations, ai_logs, human_notes")
    print("Indexes created for optimal query performance")


if __name__ == "__main__":
    create_tables()
