#!/usr/bin/env python3
"""
Simple test script to identify which import is hanging in the background task.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

print("🔍 Testing imports one by one to identify the hanging import...")

async def test_imports():
    """Test each import separately to identify the hanging one."""

    print("🧪 [TEST 1] Importing vpsweb.repository.settings...")
    try:
        from vpsweb.repository.settings import settings
        print("✅ [TEST 1] SUCCESS: settings imported successfully")
        print(f"   Database URL: {settings.database_url}")
    except Exception as e:
        print(f"❌ [TEST 1] FAILED: {e}")
        return

    print("🧪 [TEST 2] Importing sqlalchemy.create_engine...")
    try:
        from sqlalchemy import create_engine
        print("✅ [TEST 2] SUCCESS: create_engine imported successfully")
    except Exception as e:
        print(f"❌ [TEST 2] FAILED: {e}")
        return

    print("🧪 [TEST 3] Importing sqlalchemy.orm.sessionmaker...")
    try:
        from sqlalchemy.orm import sessionmaker
        print("✅ [TEST 3] SUCCESS: sessionmaker imported successfully")
    except Exception as e:
        print(f"❌ [TEST 3] FAILED: {e}")
        return

    print("🧪 [TEST 4] Importing sqlalchemy.pool.StaticPool...")
    try:
        from sqlalchemy.pool import StaticPool
        print("✅ [TEST 4] SUCCESS: StaticPool imported successfully")
    except Exception as e:
        print(f"❌ [TEST 4] FAILED: {e}")
        return

    print("🧪 [TEST 5] Testing database engine creation...")
    try:
        background_engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        print("✅ [TEST 5] SUCCESS: Database engine created successfully")
    except Exception as e:
        print(f"❌ [TEST 5] FAILED: {e}")
        return

    print("🧪 [TEST 6] Testing session creation...")
    try:
        BackgroundSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=background_engine)
        db = BackgroundSessionLocal()
        print("✅ [TEST 6] SUCCESS: Database session created successfully")
        db.close()
    except Exception as e:
        print(f"❌ [TEST 6] FAILED: {e}")
        return

    print("🎉 ALL TESTS PASSED! The imports are not the problem.")

if __name__ == "__main__":
    asyncio.run(test_imports())