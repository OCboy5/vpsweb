#!/usr/bin/env python3
"""
Simple test script for Phase 1 Day 1 implementation.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Set up PYTHONPATH for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_imports():
    """Test if all modules can be imported."""
    print("🧪 Testing imports...")

    try:
        from vpsweb.repository.config import load_config
        print("✅ Configuration module imported")

        from vpsweb.repository.database import get_database_manager
        print("✅ Database module imported")

        from vpsweb.repository.models import Poem, Translation, AiLog, HumanNote
        print("✅ Models module imported")

        from vpsweb.repository.base import BaseRepository
        print("✅ Base repository module imported")

        from vpsweb.repository.init_db import DatabaseInitializer
        print("✅ Database initializer module imported")

        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_config():
    """Test configuration loading."""
    print("\n🧪 Testing configuration...")

    try:
        from vpsweb.repository.config import load_config
        config = load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Database URL: {config.repository.database_url}")
        print(f"   Repository root: {config.repository.repo_root}")
        return config

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def test_database_connection():
    """Test database connection."""
    print("\n🧪 Testing database connection...")

    try:
        from vpsweb.repository.config import load_config
        from vpsweb.repository.database import get_database_manager

        config = load_config()
        db_manager = await get_database_manager(config.repository.database_url)

        # Test health check
        health = await db_manager.health_check()
        print(f"✅ Database health check: {health['status']}")
        print(f"   Can connect: {health.get('can_connect', 'Unknown')}")

        # Create tables
        await db_manager.create_tables()
        print("✅ Database tables created successfully")

        return True

    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Starting Simple Phase 1 Day 1 Test")
    print("=" * 50)

    success = True

    # Test imports
    if not await test_imports():
        success = False

    # Test configuration
    if success and not await test_config():
        success = False

    # Test database
    if success and not await test_database_connection():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 All simple tests passed!")
        print("✅ Day 1 implementation working correctly")
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    # Set PYTHONPATH if needed
    current_dir = Path(__file__).parent
    if "src" not in str(current_dir):
        sys.path.insert(0, str(current_dir / "src"))

    # Configure basic logging
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())