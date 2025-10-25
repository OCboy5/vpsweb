#!/usr/bin/env python3
"""
Database initialization script for VPSWeb repository system.

This script creates the database tables and performs basic setup.
"""

import asyncio
import sys
from pathlib import Path

# Set up PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vpsweb.repository.config import load_config
from vpsweb.repository.database import initialize_database
from vpsweb.repository.models import Base


async def init_database():
    """Initialize the database with all tables."""
    print("🚀 Initializing VPSWeb repository database...")

    try:
        # Load configuration
        config = load_config()
        print(f"✅ Configuration loaded from: {config.repository.repo_root}")

        # Initialize database
        db_manager = await initialize_database(
            database_url=config.repository.database_url,
            echo=config.server.debug
        )
        print("✅ Database initialized successfully")

        # Check database health
        health = await db_manager.health_check()
        print(f"✅ Database health check: {health['status']}")
        if health.get('size_mb'):
            print(f"   Database size: {health['size_mb']:.2f} MB")

        print("🎉 Database initialization completed!")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_tables():
    """Check if all tables were created successfully."""
    print("\n🔍 Checking database tables...")

    try:
        import sqlite3
        import os

        # Get database path from config
        config = load_config()
        db_path = config.repository.database_url.replace("sqlite+aiosqlite:///", "")

        # Connect directly to SQLite to check tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get table names
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        expected_tables = ['ai_logs', 'human_notes', 'poems', 'translations']
        created_tables = [t for t in expected_tables if t in tables]

        print(f"   Expected tables: {expected_tables}")
        print(f"   Created tables: {created_tables}")

        if set(created_tables) == set(expected_tables):
            print("✅ All tables created successfully")
            return True
        else:
            missing = set(expected_tables) - set(created_tables)
            print(f"❌ Missing tables: {missing}")
            return False

    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False


async def main():
    """Main initialization function."""
    print("VPSWeb Repository Database Initialization")
    print("=" * 50)

    # Initialize database
    if not await init_database():
        sys.exit(1)

    # Check tables
    if not await check_tables():
        sys.exit(1)

    print("\n🎯 Database is ready for use!")


if __name__ == "__main__":
    asyncio.run(main())