#!/usr/bin/env python3
"""
Test script to simulate the exact background task execution and identify where it hangs.
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("🔍 Testing background task execution simulation...")

async def simulate_background_task():
    """Simulate the exact background task execution."""

    task_id = str(uuid.uuid4())
    print(f"🌱 [BACKGROUND ENTRY] BACKGROUND TASK STARTING for task_id: {task_id}")
    logger.info(f"🌱 [BACKGROUND ENTRY] Starting background task execution for task_id: {task_id}")

    # Create a separate database engine for background task
    logger.info(f"🔗 [DB SETUP] Creating separate database connection for background task")

    # Debug each import
    logger.info(f"📦 [IMPORT 1] Importing vpsweb.repository.settings...")
    from vpsweb.repository.settings import settings
    logger.info(f"✅ [IMPORT 1] Successfully imported settings")

    logger.info(f"📦 [IMPORT 2] Importing sqlalchemy.create_engine...")
    from sqlalchemy import create_engine
    logger.info(f"✅ [IMPORT 2] Successfully imported create_engine")

    logger.info(f"📦 [IMPORT 3] Importing sqlalchemy.orm.sessionmaker...")
    from sqlalchemy.orm import sessionmaker
    logger.info(f"✅ [IMPORT 3] Successfully imported sessionmaker")

    logger.info(f"📦 [IMPORT 4] Importing sqlalchemy.pool.StaticPool...")
    from sqlalchemy.pool import StaticPool
    logger.info(f"✅ [IMPORT 4] Successfully imported StaticPool")

    logger.info(f"🏗️ [DB ENGINE] Creating database engine...")
    background_engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    logger.info(f"✅ [DB ENGINE] Database engine created successfully")

    logger.info(f"🔧 [SESSION MAKER] Creating session maker...")
    BackgroundSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=background_engine)
    logger.info(f"✅ [SESSION MAKER] Session maker created successfully")

    logger.info(f"📊 [DB SESSION] Creating database session...")
    db = BackgroundSessionLocal()
    logger.info(f"✅ [DB SESSION] Database session created successfully")

    try:
        logger.info(f"🛠️ [SERVICES] Creating fresh service instances with isolated database session")

        # Test service creation one by one
        logger.info(f"🛠️ [SERVICE 1] Creating PoemService...")
        from vpsweb.webui.services.poem_service import PoemService
        poem_service = PoemService(db)
        logger.info(f"✅ [SERVICE 1] PoemService created successfully")

        logger.info(f"🛠️ [SERVICE 2] Creating TranslationService...")
        from vpsweb.webui.services.translation_service import TranslationService
        translation_service = TranslationService(db)
        logger.info(f"✅ [SERVICE 2] TranslationService created successfully")

        logger.info(f"🛠️ [SERVICE 3] Creating RepositoryWebService...")
        from vpsweb.repository.service import RepositoryWebService
        repository_service = RepositoryWebService(db)
        logger.info(f"✅ [SERVICE 3] RepositoryWebService created successfully")

        logger.info(f"✅ [SERVICES] All service instances created successfully")

        # Test a simple database operation
        logger.info(f"🧪 [DB TEST] Testing simple database operation...")
        result = repository_service.get_workflow_task(task_id)
        if result is None:
            logger.info(f"✅ [DB TEST] Database operation completed (task not found as expected)")
        else:
            logger.info(f"✅ [DB TEST] Database operation completed (found task: {result})")

        logger.info(f"🎉 [SUCCESS] Background task simulation completed successfully!")

    except Exception as e:
        logger.error(f"❌ [ERROR] Background task simulation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info(f"🧹 [CLEANUP] Closing database session...")
        db.close()
        logger.info(f"✅ [CLEANUP] Database session closed")

if __name__ == "__main__":
    asyncio.run(simulate_background_task())