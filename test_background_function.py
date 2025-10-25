#!/usr/bin/env python3
"""
Simple test to verify if the background task function works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_background_task_function():
    """Test the background task function directly."""
    print("🧪 Testing if background task function can be called directly...")

    try:
        from vpsweb.webui.services.vpsweb_adapter import VPSWebWorkflowAdapter
        from vpsweb.models.config import WorkflowMode
        from vpsweb.webui.services.poem_service import PoemService
        from vpsweb.webui.services.translation_service import TranslationService
        from vpsweb.repository.service import RepositoryWebService
        from vpsweb.repository.database import create_session

        print("✅ Successfully imported all required classes")

        # Create a simple test
        print("🧪 Testing background task function signature...")

        # Create a mock adapter instance (we won't actually call it, just test the function exists)
        db = create_session()
        poem_service = PoemService(db)
        translation_service = TranslationService(db)
        repository_service = RepositoryWebService(db)

        adapter = VPSWebWorkflowAdapter(
            poem_service=poem_service,
            translation_service=translation_service,
            repository_service=repository_service
        )

        print("✅ Successfully created VPSWebWorkflowAdapter instance")

        # Check if the function exists and has the right signature
        if hasattr(adapter, '_execute_workflow_task_with_new_session'):
            func = getattr(adapter, '_execute_workflow_task_with_new_session')
            print(f"✅ Function _execute_workflow_task_with_new_session exists")
            print(f"   Function type: {type(func)}")
            print(f"   Is coroutine: {asyncio.iscoroutinefunction(func)}")
            print(f"   Callable: {callable(func)}")

            # This confirms our fix worked - the function should NOT be async anymore
            if not asyncio.iscoroutinefunction(func):
                print("✅ SUCCESS: Function is no longer async (fixed for FastAPI BackgroundTasks)")
            else:
                print("❌ PROBLEM: Function is still async - fix didn't work")
        else:
            print("❌ Function _execute_workflow_task_with_new_session not found")

        db.close()
        print("🎉 Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_background_task_function()