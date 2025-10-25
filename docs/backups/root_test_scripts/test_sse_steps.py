#!/usr/bin/env python3
"""
Test script to simulate SSE step progress updates
"""
import asyncio
import sys
import os
import json
import time
import httpx

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

from vpsweb.webui.task_models import TaskStatus, TaskStatusEnum

async def test_sse_step_updates():
    """Test SSE with simulated step progress updates"""

    # Initialize FastAPI app to access app.state
    from vpsweb.webui.main import app

    print("🧪 Creating test task with simulated step progress...")

    # Create a test task
    task_id = "test-sse-step-updates"

    # Initialize task in app.state
    if not hasattr(app.state, 'tasks'):
        app.state.tasks = {}
    if not hasattr(app.state, 'task_locks'):
        app.state.task_locks = {}

    from threading import Lock
    app.state.task_locks[task_id] = Lock()

    # Create initial task status
    task_status = TaskStatus(
        task_id=task_id,
        status=TaskStatusEnum.RUNNING,
        progress=10,
        current_step="Initial Translation",
        step_details={"provider": "Test", "mode": "simulation"},
        step_progress={"Initial Translation": 10},
        step_states={
            "Initial Translation": "running",
            "Editor Review": "waiting",
            "Translator Revision": "waiting"
        },
        message="Starting simulated step progress test..."
    )

    app.state.tasks[task_id] = task_status
    print(f"✅ Test task created: {task_id}")

    # Start SSE client in background
    print("📡 Starting SSE client...")

    async def sse_client():
        """Connect to SSE and receive updates"""
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    'GET',
                    f'http://localhost:8000/api/v1/workflow/tasks/{task_id}/stream',
                    timeout=30.0
                ) as response:
                    if response.status_code != 200:
                        print(f"❌ SSE connection failed: {response.status_code}")
                        return

                    print("✅ SSE connected, listening for updates...")

                    events_received = []
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            try:
                                event_data = json.loads(data)
                                events_received.append(event_data)
                                step_states = event_data.get('step_states', {})
                                current_step = event_data.get('current_step', 'unknown')
                                current_state = step_states.get(current_step, 'unknown')

                                print(f"📨 SSE Event: {event_data['status']} - {event_data['progress']}% - {current_step} ({current_state})")

                                # Stop after completion
                                if event_data['status'] == 'completed':
                                    break

                            except json.JSONDecodeError as e:
                                print(f"❌ JSON decode error: {e}")
                                print(f"Raw data: {data}")
                        elif line.startswith('event: '):
                            event_type = line[7:]  # Remove 'event: ' prefix
                            print(f"🔔 Event type: {event_type}")

                    print(f"✅ SSE received {len(events_received)} events")
                    return events_received

            except Exception as e:
                print(f"❌ SSE client error: {e}")
                return []

    # Run SSE client concurrently with simulated progress updates
    sse_task = asyncio.create_task(sse_client())

    # Simulate step progress updates
    print("🎭 Simulating step progress updates...")

    await asyncio.sleep(1)  # Initial delay

    # Step 1 completion
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Initial Translation",
            step_details={"provider": "Test", "mode": "simulation", "status": "Completed"},
            step_percent=33,
            message="Initial translation completed",
            step_state="completed"
        )
    print("📝 Step 1 completed (33%)")

    await asyncio.sleep(2)

    # Step 2 start
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Editor Review",
            step_details={"provider": "Editor", "mode": "simulation"},
            step_percent=66,
            message="Editor review in progress",
            step_state="running"
        )
    print("📝 Step 2 started (66%)")

    await asyncio.sleep(2)

    # Step 2 completion
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Editor Review",
            step_details={"provider": "Editor", "mode": "simulation", "status": "Completed"},
            step_percent=66,
            message="Editor review completed",
            step_state="completed"
        )
    print("📝 Step 2 completed (66%)")

    await asyncio.sleep(2)

    # Step 3 start
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Translator Revision",
            step_details={"provider": "Translator", "mode": "simulation"},
            step_percent=90,
            message="Translator revision in progress",
            step_state="running"
        )
    print("📝 Step 3 started (90%)")

    await asyncio.sleep(2)

    # Step 3 completion
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Translator Revision",
            step_details={"provider": "Translator", "mode": "simulation", "status": "Completed"},
            step_percent=100,
            message="All steps completed successfully",
            step_state="completed"
        )
        task_status.complete({"result": "Test completed successfully"})
    print("📝 Step 3 completed (100%) - Task finished")

    # Wait for SSE client to finish
    events = await sse_task

    # Analyze results
    print("\n📊 Test Results Analysis:")
    print(f"Total SSE events received: {len(events)}")

    step_changes = []
    for i, event in enumerate(events):
        if 'step_states' in event:
            step_states = event['step_states']
            current_step = event.get('current_step')
            current_state = step_states.get(current_step, 'unknown')
            step_changes.append(f"{current_step}: {current_state}")

    print(f"Step state changes detected: {len(step_changes)}")
    for change in step_changes:
        print(f"  - {change}")

    # Check if we detected intermediate updates
    intermediate_updates = [e for e in events if e.get('progress') in [33, 66, 90]]

    if len(intermediate_updates) >= 2:
        print("✅ SUCCESS: SSE detected intermediate step progress updates!")
        print(f"✅ Found {len(intermediate_updates)} intermediate updates (33%, 66%, 90%)")
        return True
    else:
        print("❌ FAILURE: SSE did not detect intermediate step progress updates")
        print(f"❌ Only found {len(intermediate_updates)} intermediate updates")
        return False

if __name__ == "__main__":
    print("🧪 Testing SSE Step Progress Detection")
    print("=" * 50)

    try:
        result = asyncio.run(test_sse_step_updates())
        if result:
            print("\n🎉 TEST PASSED: SSE enhancement working correctly!")
            sys.exit(0)
        else:
            print("\n💥 TEST FAILED: SSE enhancement not working")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)