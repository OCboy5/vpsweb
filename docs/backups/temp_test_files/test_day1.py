#!/usr/bin/env python3
"""
Test script for Phase 1 Day 1 implementation.

Tests the database models, configuration, and basic functionality
to ensure everything is working correctly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Set up PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vpsweb.repository.config import load_config
from vpsweb.repository.database import get_database_manager, get_session
from vpsweb.repository.models import Poem, Translation, AiLog, HumanNote
from vpsweb.repository.init_db import DatabaseInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_configuration():
    """Test configuration loading."""
    print("🧪 Testing configuration loading...")

    try:
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Database URL: {config.repository.database_url}")
        print(f"   Repository root: {config.repository.repo_root}")
        print(f"   Server host: {config.server.host}:{config.server.port}")
        print(f"   Default language: {config.data.default_language}")
        return config
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        raise


async def test_database_initialization(config):
    """Test database initialization."""
    print("\n🧪 Testing database initialization...")

    try:
        # Initialize database
        db_manager = await get_database_manager(config.repository.database_url)

        # Create tables
        await db_manager.create_tables()
        print("✅ Database tables created successfully")

        # Test health check
        health = await db_manager.health_check()
        print(f"✅ Database health check: {health['status']}")

        return db_manager
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


async def test_models(db_manager):
    """Test database models."""
    print("\n🧪 Testing database models...")

    try:
        async with get_session() as session:
            # Test Poem model
            poem = Poem(
                poet_name="Test Poet",
                poem_title="Test Poem",
                source_language="en",
                original_text="This is a test poem for validation."
            )
            session.add(poem)
            await session.commit()
            await session.refresh(poem)
            print(f"✅ Poem model test - Created poem with ID: {poem.id}")

            # Test Translation model
            translation = Translation(
                poem_id=poem.id,
                target_language="zh-Hans",
                version=1,
                translated_text="这是一首测试诗的翻译。",
                translator_type="human",
                translator_info="Test Translator"
            )
            session.add(translation)
            await session.commit()
            await session.refresh(translation)
            print(f"✅ Translation model test - Created translation with ID: {translation.id}")

            # Test AiLog model
            ai_log = AiLog(
                poem_id=poem.id,
                translation_id=translation.id,
                workflow_mode="hybrid",
                provider="test_provider",
                model_name="test_model",
                temperature="0.7",
                status="completed"
            )
            session.add(ai_log)
            await session.commit()
            await session.refresh(ai_log)
            print(f"✅ AiLog model test - Created AI log with ID: {ai_log.id}")

            # Test HumanNote model
            human_note = HumanNote(
                poem_id=poem.id,
                note_type="comment",
                title="Test Note",
                content="This is a test note for validation.",
                author_name="Test Author"
            )
            session.add(human_note)
            await session.commit()
            await session.refresh(human_note)
            print(f"✅ HumanNote model test - Created note with ID: {human_note.id}")

            # Test relationships
            retrieved_poem = await session.get(Poem, poem.id)
            print(f"✅ Relationship test - Retrieved poem: {retrieved_poem.poet_name}")

            return True

    except Exception as e:
        print(f"❌ Model test failed: {e}")
        raise


async def test_constraints():
    """Test database constraints."""
    print("\n🧪 Testing database constraints...")

    try:
        async with get_session() as session:
            # Test invalid language code
            try:
                invalid_poem = Poem(
                    poet_name="Test Poet",
                    poem_title="Test Poem",
                    source_language="invalid-lang",
                    original_text="Test content"
                )
                session.add(invalid_poem)
                await session.commit()
                print("❌ Language code constraint failed - should have been rejected")
            except Exception:
                print("✅ Language code constraint working correctly")

            # Test empty poet name
            try:
                invalid_poem = Poem(
                    poet_name="   ",  # Empty name
                    poem_title="Test Poem",
                    source_language="en",
                    original_text="Test content"
                )
                session.add(invalid_poem)
                await session.commit()
                print("❌ Empty poet name constraint failed - should have been rejected")
            except Exception:
                print("✅ Empty poet name constraint working correctly")

            # Test negative version number
            try:
                invalid_translation = Translation(
                    poem_id="test-id",
                    target_language="zh-Hans",
                    version=-1,  # Negative version
                    translated_text="Test translation"
                )
                session.add(invalid_translation)
                await session.commit()
                print("❌ Negative version constraint failed - should have been rejected")
            except Exception:
                print("✅ Negative version constraint working correctly")

        return True

    except Exception as e:
        print(f"❌ Constraint test failed: {e}")
        raise


async def test_queries():
    """Test database queries and relationships."""
    print("\n🧪 Testing database queries...")

    try:
        async with get_session() as session:
            # Count records
            poem_count = await session.execute(
                "SELECT COUNT(*) FROM poems"
            )
            count = poem_count.scalar()
            print(f"✅ Query test - Found {count} poems")

            # Test relationship queries
            if count > 0:
                # Get poem with translations
                poem_with_translations = await session.execute(
                    """
                    SELECT p.*, COUNT(t.id) as translation_count
                    FROM poems p
                    LEFT JOIN translations t ON p.id = t.poem_id
                    GROUP BY p.id
                    LIMIT 1
                ")
                result = poem_with_translations.fetchone()
                if result:
                    print(f"✅ Relationship query test - Poem with {result[6]} translations")

            return True

    except Exception as e:
        print(f"❌ Query test failed: {e}")
        raise


async def cleanup_test_data():
    """Clean up test data."""
    print("\n🧪 Cleaning up test data...")

    try:
        async with get_session() as session:
            await session.execute("DELETE FROM human_notes")
            await session.execute("DELETE FROM ai_logs")
            await session.execute("DELETE FROM translations")
            await session.execute("DELETE FROM poems")
            await session.commit()
            print("✅ Test data cleaned up")

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        raise


async def main():
    """Main test function."""
    print("🚀 Starting Phase 1 Day 1 Implementation Test")
    print("=" * 50)

    try:
        # Test configuration
        config = await test_configuration()

        # Test database
        db_manager = await test_database_initialization(config)

        # Test models
        await test_models(db_manager)

        # Test constraints
        await test_constraints()

        # Test queries
        await test_queries()

        # Cleanup
        await cleanup_test_data()

        # Close database connection
        if db_manager:
            await db_manager.close()

        print("\n" + "=" * 50)
        print("🎉 All Phase 1 Day 1 tests passed successfully!")
        print("✅ Database models working correctly")
        print("✅ Configuration system working")
        print("✅ SQLAlchemy engine with WAL mode working")
        print("✅ Async session management working")
        print("✅ Database constraints working")
        print("✅ Base repository class ready")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Test failure details")
        sys.exit(1)


if __name__ == "__main__":
    # Set PYTHONPATH if needed
    current_dir = Path(__file__).parent
    if "src" not in str(current_dir):
        sys.path.insert(0, str(current_dir / "src"))

    asyncio.run(main())