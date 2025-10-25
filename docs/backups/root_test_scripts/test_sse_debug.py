#!/usr/bin/env python3
"""
Debug SSE with more detailed logging
"""
import asyncio
import sys
import os
import json
import time
import httpx

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

async def test_sse_debug():
    """Debug SSE with detailed logging"""

    # Import after setting path
    from vpsweb.webui.main import app
    from vpsweb.webui.task_models import TaskStatus, TaskStatusEnum

    print("🧪 Starting detailed SSE debug...")

    # Initialize app.state
    if not hasattr(app.state, 'tasks'):
        app.state.tasks = {}
    if not hasattr(app.state, 'task_locks'):
        app.state.task_locks = {}

    from threading import Lock

    task_id = "debug-sse-test"

    # Create task lock
    app.state.task_locks[task_id] = Lock()

    # Create initial task
    task_status = TaskStatus(
        task_id=task_id,
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
        message="Starting debug test..."
    )

    app.state.tasks[task_id] = task_status
    print(f"✅ Test task created: {task_id}")

    # Start SSE client
    async def sse_client():
        events_received = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream(
                    'GET',
                    f'http://localhost:8000/api/v1/workflow/tasks/{task_id}/stream'
                ) as response:
                    if response.status_code != 200:
                        print(f"❌ SSE connection failed: {response.status_code}")
                        return events_received

                    print("✅ SSE connected, listening for updates...")

                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:]
                            try:
                                event_data = json.loads(data)
                                events_received.append(event_data)

                                print(f"\n📨 Event {len(events_received)} received:")
                                print(f"   Raw JSON: {json.dumps(event_data, indent=2)}")

                                # Check all fields
                                for key in ['task_id', 'status', 'progress', 'current_step', 'step_states', 'step_progress']:
                                    value = event_data.get(key)
                                    print(f"   {key}: {value} (type: {type(value)})")

                                if event_data.get('status') == 'completed':
                                    break

                            except json.JSONDecodeError as e:
                                print(f"❌ JSON error: {e}")
                                print(f"Raw data: '{data}'")

            except Exception as e:
                print(f"❌ SSE error: {e}")
                import traceback
                traceback.print_exc()

        return events_received

    # Start SSE client
    sse_task = asyncio.create_task(sse_client())

    # Wait for initial connection
    await asyncio.sleep(2)

    print("\n🎭 Manually updating task state...")

    # Check initial state
    print(f"Initial task_status.progress: {task_status.progress}")
    print(f"Initial task_status.to_dict(): {json.dumps(task_status.to_dict(), indent=2)}")

    # Update with set_progress to ensure overall progress changes
    task_status.set_progress(33, "Progress updated to 33%")
    print(f"After set_progress(33): {task_status.progress}")

    await asyncio.sleep(2)

    task_status.set_progress(66, "Progress updated to 66%")
    print(f"After set_progress(66): {task_status.progress}")

    await asyncio.sleep(2)

    task_status.set_progress(100, "Progress updated to 100%")
    print(f"After set_progress(100): {task_status.progress}")

    # Wait for SSE client
    await asyncio.sleep(2)
    events = await sse_task

    print(f"\n📊 Final Results:")
    print(f"Total events received: {len(events)}")

    return len(events) > 1

if __name__ == "__main__":
    print("🧪 SSE Debug Test")
    print("=" * 50)

    try:
        result = asyncio.run(test_sse_debug())
        if result:
            print("\n🎉 SSE working!")
        else:
            print("\n💥 SSE not working")
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)