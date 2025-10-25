#!/usr/bin/env python3
"""
Direct test of SSE change detection by manually updating app.state
"""
import asyncio
import sys
import os
import json
import time
import httpx

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

async def test_sse_direct():
    """Test SSE by manually manipulating app.state"""

    # Import after setting path
    from vpsweb.webui.main import app
    from vpsweb.webui.task_models import TaskStatus, TaskStatusEnum

    print("🧪 Starting direct SSE test...")

    # Initialize app.state
    if not hasattr(app.state, 'tasks'):
        app.state.tasks = {}
    if not hasattr(app.state, 'task_locks'):
        app.state.task_locks = {}

    from threading import Lock

    task_id = "direct-sse-test"

    # Create task lock
    app.state.task_locks[task_id] = Lock()

    # Create initial task
    task_status = TaskStatus(
        task_id=task_id,
        status=TaskStatusEnum.RUNNING,
        progress=10,
        current_step="Initial Translation",
        step_details={"provider": "Test", "mode": "direct"},
        step_progress={"Initial Translation": 10},
        step_states={
            "Initial Translation": "running",
            "Editor Review": "waiting",
            "Translator Revision": "waiting"
        },
        message="Starting direct SSE test..."
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

                                step_states = event_data.get('step_states', {})
                                current_step = event_data.get('current_step', 'unknown')
                                current_state = step_states.get(current_step, 'unknown')

                                print(f"📨 Event {len(events_received)}: {event_data['progress']}% - {current_step} ({current_state})")

                                if event_data['status'] == 'completed':
                                    break

                            except json.JSONDecodeError as e:
                                print(f"❌ JSON error: {e}")

            except Exception as e:
                print(f"❌ SSE error: {e}")

        return events_received

    # Start SSE client
    sse_task = asyncio.create_task(sse_client())

    # Wait for initial connection
    await asyncio.sleep(1)

    print("\n🎭 Simulating step progress changes...")

    # Simulate the exact scenario: Step 1 -> Step 2 (66%) -> Step 3 (90%) -> Complete

    # Step 1 completion (33%)
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Initial Translation",
            step_details={"provider": "Test", "mode": "direct", "status": "Completed"},
            step_percent=33,
            message="Step 1 completed",
            step_state="completed"
        )
    print("📝 Step 1 completed (33%)")

    await asyncio.sleep(2)

    # Step 2 start and completion (66%)
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Editor Review",
            step_details={"provider": "Editor", "mode": "direct"},
            step_percent=66,
            message="Step 2 running",
            step_state="running"
        )
    print("📝 Step 2 started (66%)")

    await asyncio.sleep(2)

    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Editor Review",
            step_details={"provider": "Editor", "mode": "direct", "status": "Completed"},
            step_percent=66,
            message="Step 2 completed",
            step_state="completed"
        )
    print("📝 Step 2 completed (66%)")

    await asyncio.sleep(2)

    # Step 3 start and completion (90% -> 100%)
    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Translator Revision",
            step_details={"provider": "Translator", "mode": "direct"},
            step_percent=90,
            message="Step 3 running",
            step_state="running"
        )
    print("📝 Step 3 started (90%)")

    await asyncio.sleep(2)

    with app.state.task_locks[task_id]:
        task_status.update_step(
            step_name="Translator Revision",
            step_details={"provider": "Translator", "mode": "direct", "status": "Completed"},
            step_percent=100,
            message="All steps completed",
            step_state="completed"
        )
        # Manually set completed status
        task_status.status = TaskStatusEnum.COMPLETED
        task_status.progress = 100
        task_status.message = "Translation completed successfully"
    print("📝 Step 3 completed (100%) - Task finished")

    # Wait for SSE client to receive all events
    await asyncio.sleep(2)
    events = await sse_task

    # Analyze results
    print(f"\n📊 Results:")
    print(f"Total events received: {len(events)}")

    # Check for intermediate progress values
    progress_values = [e.get('progress') for e in events]
    intermediate_updates = [p for p in progress_values if p in [33, 66, 90]]

    print(f"Progress values received: {progress_values}")
    print(f"Intermediate updates (33, 66, 90): {intermediate_updates}")

    # Check step state changes
    step_changes = []
    for event in events:
        step_states = event.get('step_states', {})
        current_step = event.get('current_step')
        if current_step and step_states:
            current_state = step_states.get(current_step)
            step_changes.append(f"{current_step}: {current_state}")

    print(f"Step state changes: {step_changes}")

    # Evaluate success
    success_criteria = {
        'has_initial': any(e.get('progress') == 10 for e in events),
        'has_step1': any(e.get('progress') == 33 for e in events),
        'has_step2': any(e.get('progress') == 66 for e in events),
        'has_step3': any(e.get('progress') == 90 for e in events),
        'has_completion': any(e.get('progress') == 100 for e in events),
        'total_events': len(events) >= 5  # Should have at least 5 events
    }

    print(f"\n✅ Success Criteria:")
    for criteria, passed in success_criteria.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criteria}: {passed}")

    all_passed = all(success_criteria.values())

    if all_passed:
        print(f"\n🎉 TEST PASSED: SSE enhancement working correctly!")
        print(f"✅ Detected all intermediate step progress updates (33%, 66%, 90%)")
        return True
    else:
        print(f"\n💥 TEST FAILED: SSE enhancement not working properly")
        failed_criteria = [k for k, v in success_criteria.items() if not v]
        print(f"❌ Failed criteria: {failed_criteria}")
        return False

if __name__ == "__main__":
    print("🧪 Direct SSE Change Detection Test")
    print("=" * 50)

    try:
        result = asyncio.run(test_sse_direct())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)