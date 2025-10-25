#!/usr/bin/env python3
"""
Debug TaskStatus serialization
"""
import sys
import json

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

from vpsweb.webui.task_models import TaskStatus, TaskStatusEnum

def test_serialization():
    print("🧪 Testing TaskStatus serialization...")

    # Create a test task
    task_status = TaskStatus(
        task_id="test-123",
        status=TaskStatusEnum.RUNNING,
        progress=10,
        current_step="Initial Translation",
        step_details={"provider": "Test", "mode": "debug"},
        step_progress={"Initial Translation": 10},
        step_states={
            "Initial Translation": "running",
            "Editor Review": "waiting",
            "Translator Revision": "waiting"
        },
        message="Testing serialization..."
    )

    print("✅ TaskStatus created")

    # Test to_dict()
    try:
        task_dict = task_status.to_dict()
        print("✅ to_dict() successful")
        print(f"Keys: {list(task_dict.keys())}")
        print(f"Status: {task_dict['status']} (type: {type(task_dict['status'])})")
        print(f"Progress: {task_dict['progress']} (type: {type(task_dict['progress'])})")
    except Exception as e:
        print(f"❌ to_dict() failed: {e}")
        return False

    # Test JSON serialization
    try:
        json_str = json.dumps(task_dict)
        print("✅ JSON serialization successful")
        print(f"JSON length: {len(json_str)}")
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        return False

    # Test JSON deserialization
    try:
        parsed = json.loads(json_str)
        print("✅ JSON deserialization successful")
        print(f"Parsed status: {parsed['status']}")
        print(f"Parsed progress: {parsed['progress']}")
    except Exception as e:
        print(f"❌ JSON deserialization failed: {e}")
        return False

    print("🎉 All serialization tests passed!")
    return True

if __name__ == "__main__":
    test_serialization()