"""
VPSWeb Repository System - Database Initialization

This module provides database initialization utilities including
schema creation, migration support, and data seeding.

Features:
- Database schema creation with proper error handling
- Migration support for future schema changes
- Data seeding for development/testing
- Database health verification
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .config import load_config
from .database import DatabaseManager, get_database_manager
from .models import Base, Poem, Translation, AiLog, HumanNote

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Handles database initialization and migration tasks.

    Provides utilities for creating database schema, running migrations,
    and verifying database health.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the database initializer.

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.db_manager: Optional[DatabaseManager] = None

    async def initialize(self) -> None:
        """
        Initialize the database with schema creation.

        Creates the database manager, sets up the engine, and creates
        all tables defined in the models.
        """
        logger.info("Starting database initialization")

        try:
            # Initialize database manager
            self.db_manager = await get_database_manager(
                self.config.repository.database_url,
                echo=self.config.server.debug
            )

            # Create all tables
            await self.db_manager.create_tables()

            logger.info("Database initialization completed successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def create_tables(self) -> None:
        """
        Create all database tables.

        Should be called after initialize() to ensure all tables exist.
        """
        if not self.db_manager:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.info("Creating database tables")
        await self.db_manager.create_tables()

    async def drop_tables(self) -> None:
        """
        Drop all database tables.

        WARNING: This will delete all data! Use only for testing.
        """
        if not self.db_manager:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.warning("Dropping all database tables")
        await self.db_manager.drop_tables()

    async def verify_schema(self) -> dict:
        """
        Verify database schema integrity.

        Returns:
            dict: Schema verification results
        """
        if not self.db_manager:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.info("Verifying database schema")

        try:
            async with self.db_manager.get_session_context() as session:
                # Check if all tables exist
                tables_to_check = ["poems", "translations", "ai_logs", "human_notes"]
                existing_tables = []

                for table_name in tables_to_check:
                    try:
                        result = await session.execute(
                            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                        )
                        if result.fetchone():
                            existing_tables.append(table_name)
                    except Exception as e:
                        logger.error(f"Error checking table {table_name}: {e}")

                # Check if all expected tables exist
                missing_tables = set(tables_to_check) - set(existing_tables)
                all_tables_exist = len(missing_tables) == 0

                # Check table schemas (basic validation)
                schema_valid = True
                schema_details = {}

                for table_name in existing_tables:
                    try:
                        result = await session.execute(f"PRAGMA table_info({table_name})")
                        columns = result.fetchall()
                        schema_details[table_name] = [
                            {"name": col[1], "type": col[2], "notnull": col[3], "pk": col[5]}
                            for col in columns
                        ]
                    except Exception as e:
                        logger.error(f"Error getting schema for {table_name}: {e}")
                        schema_valid = False

                return {
                    "status": "success" if all_tables_exist and schema_valid else "warning",
                    "all_tables_exist": all_tables_exist,
                    "missing_tables": list(missing_tables),
                    "existing_tables": existing_tables,
                    "schema_valid": schema_valid,
                    "schema_details": schema_details
                }

        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def seed_development_data(self) -> None:
        """
        Seed database with sample data for development.

        Creates sample poems and translations for testing and development.
        """
        if not self.db_manager:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.info("Seeding development data")

        try:
            async with self.db_manager.get_session_context() as session:
                # Create sample poems
                sample_poems = [
                    {
                        "poet_name": "Emily Dickinson",
                        "poem_title": "Hope is the thing with feathers",
                        "source_language": "en",
                        "original_text": """Hope is the thing with feathers
That perches in the soul,
And sings the tune without the words,
And never stops at all,

And sweetest in the gale is heard;
And sore must be the storm
That could abash the little bird
That kept so many warm.

I've heard it in the chillest land,
And on the strangest sea;
Yet, never, in extremity,
It asked a crumb of me.""",
                        "genre": "Nature"
                    },
                    {
                        "poet_name": "Li Bai",
                        "poem_title": "靜夜思 (Quiet Night Thought)",
                        "source_language": "zh-Hans",
                        "original_text": """床前明月光，
疑是地上霜。
舉頭望明月，
低頭思故鄉。""",
                        "genre": "Classical",
                        "publication_year": 756
                    }
                ]

                for poem_data in sample_poems:
                    poem = Poem(**poem_data)
                    session.add(poem)

                await session.commit()
                logger.info(f"Created {len(sample_poems)} sample poems")

                # Create sample translations
                sample_translations = [
                    {
                        "poem_id": 1,  # First poem
                        "target_language": "zh-Hans",
                        "version": 1,
                        "translated_text": """希望是长着翅膀的东西
栖息在灵魂里，
唱着没有歌词的曲调，
永不停止，

在狂风中听到最甜美的歌；
风暴一定很猛烈
才能让那小小的鸟儿感到惊惶
它却保持了那么多温暖。

我在最寒冷的土地听到过它，
也在最奇怪的海上；
然而，即使在极端的境地，
它也从未向我索要过一点碎屑。""",
                        "translator_type": "human",
                        "translator_info": "Sample translation",
                        "is_published": True
                    },
                    {
                        "poem_id": 2,  # Second poem
                        "target_language": "en",
                        "version": 1,
                        "translated_text": """Before my bed, the moonlight is bright,
I wonder if it's frost on the ground.
I raise my head to gaze at the bright moon,
I lower my head and think of home.""",
                        "translator_type": "human",
                        "translator_info": "Sample translation",
                        "is_published": True
                    }
                ]

                for trans_data in sample_translations:
                    translation = Translation(**trans_data)
                    session.add(translation)

                await session.commit()
                logger.info(f"Created {len(sample_translations)} sample translations")

                # Create sample AI logs
                sample_ai_logs = [
                    {
                        "poem_id": 1,
                        "workflow_mode": "hybrid",
                        "provider": "tongyi",
                        "model_name": "qwen-max-latest",
                        "temperature": "0.7",
                        "prompt_tokens": 850,
                        "completion_tokens": 320,
                        "total_tokens": 1170,
                        "duration_seconds": 12.5,
                        "status": "completed"
                    },
                    {
                        "poem_id": 2,
                        "workflow_mode": "hybrid",
                        "provider": "tongyi",
                        "model_name": "qwen-max-latest",
                        "temperature": "0.7",
                        "prompt_tokens": 120,
                        "completion_tokens": 85,
                        "total_tokens": 205,
                        "duration_seconds": 3.2,
                        "status": "completed"
                    }
                ]

                for log_data in sample_ai_logs:
                    ai_log = AiLog(**log_data)
                    session.add(ai_log)

                await session.commit()
                logger.info(f"Created {len(sample_ai_logs)} sample AI logs")

                # Create sample human notes
                sample_notes = [
                    {
                        "poem_id": 1,
                        "note_type": "comment",
                        "title": "Translation Note",
                        "content": "This translation maintains the metaphorical structure while adapting the cultural context.",
                        "author_name": "Sample Reviewer",
                        "is_public": True
                    },
                    {
                        "poem_id": 2,
                        "note_type": "review",
                        "title": "Classical Interpretation",
                        "content": "Classic representation of homesickness and nostalgia in Chinese poetry.",
                        "author_name": "Sample Reviewer",
                        "is_public": True
                    }
                ]

                for note_data in sample_notes:
                    human_note = HumanNote(**note_data)
                    session.add(human_note)

                await session.commit()
                logger.info(f"Created {len(sample_notes)} sample human notes")

            logger.info("Development data seeding completed successfully")

        except Exception as e:
            logger.error(f"Development data seeding failed: {e}")
            raise

    async def cleanup_development_data(self) -> None:
        """
        Clean up development data.

        Removes all sample data created during development.
        """
        if not self.db_manager:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        logger.warning("Cleaning up development data")

        try:
            async with self.db_manager.get_session_context() as session:
                # Delete all records
                await session.execute("DELETE FROM human_notes")
                await session.execute("DELETE FROM ai_logs")
                await session.execute("DELETE FROM translations")
                await session.execute("DELETE FROM poems")

                await session.commit()
                logger.info("Development data cleanup completed")

        except Exception as e:
            logger.error(f"Development data cleanup failed: {e}")
            raise

    async def close(self) -> None:
        """Close database connections."""
        if self.db_manager:
            await self.db_manager.close()


# Convenience functions for common operations
async def init_database(config_path: Optional[str] = None) -> DatabaseInitializer:
    """
    Initialize database with configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        DatabaseInitializer: Initialized database initializer
    """
    initializer = DatabaseInitializer(config_path)
    await initializer.initialize()
    return initializer


async def create_sample_database(config_path: Optional[str] = None) -> DatabaseInitializer:
    """
    Create a sample database with test data.

    Args:
        config_path: Path to configuration file

    Returns:
        DatabaseInitializer: Initialized database with sample data
    """
    initializer = await init_database(config_path)
    await initializer.seed_development_data()
    return initializer


# CLI-compatible functions
async def run_init_command(config_path: Optional[str] = None, echo: bool = False) -> None:
    """
    Run database initialization from CLI.

    Args:
        config_path: Path to configuration file
        echo: Whether to enable SQLAlchemy echo
    """
    if echo:
        logging.basicConfig(level=logging.INFO)

    try:
        initializer = await init_database(config_path)
        print("✅ Database initialized successfully")

        # Verify schema
        verification = await initializer.verify_schema()
        if verification["status"] == "success":
            print("✅ Database schema verified")
        else:
            print(f"⚠️  Schema verification warnings: {verification}")

        await initializer.close()

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def run_seed_command(config_path: Optional[str] = None) -> None:
    """
    Run development data seeding from CLI.

    Args:
        config_path: Path to configuration file
    """
    try:
        initializer = DatabaseInitializer(config_path)
        await initializer.initialize()
        await initializer.seed_development_data()
        await initializer.close()

        print("✅ Development data seeded successfully")

    except Exception as e:
        print(f"❌ Development data seeding failed: {e}")
        raise


async def run_verify_command(config_path: Optional[str] = None) -> None:
    """
    Run database verification from CLI.

    Args:
        config_path: Path to configuration file
    """
    try:
        initializer = DatabaseInitializer(config_path)
        await initializer.initialize()

        verification = await initializer.verify_schema()

        print("📊 Database Verification Results:")
        print(f"   Status: {verification['status']}")
        print(f"   All tables exist: {verification['all_tables_exist']}")

        if verification.get('missing_tables'):
            print(f"   Missing tables: {verification['missing_tables']}")

        if verification.get('existing_tables'):
            print(f"   Existing tables: {verification['existing_tables']}")

        print(f"   Schema valid: {verification['schema_valid']}")

        await initializer.close()

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        raise


if __name__ == "__main__":
    # For testing purposes
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "init"
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "init":
        asyncio.run(run_init_command(config_path, echo=True))
    elif command == "seed":
        asyncio.run(run_seed_command(config_path))
    elif command == "verify":
        asyncio.run(run_verify_command(config_path))
    else:
        print("Available commands: init, seed, verify")
        sys.exit(1)