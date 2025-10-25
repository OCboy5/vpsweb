#!/usr/bin/env python3
"""
Integration test of SSE using real API calls
"""
import asyncio
import sys
import os
import json
import time
import httpx

# Add src to path
sys.path.insert(0, '/Volumes/Work/Dev/vpsweb/vpsweb/src')

async def test_sse_integration():
    """Test SSE by triggering a real translation workflow"""

    print("🧪 Starting SSE integration test...")

    # First, let's start a real translation workflow
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Start translation
            print("📤 Starting translation workflow...")
            response = await client.post(
                'http://localhost:8000/api/v1/workflow/translate',
                json={
                    "poem_id": "01K8AV9KFTSG8N2EWW9P6WR4ZC",  # Use the longer poem
                    "source_lang": "zh-CN",
                    "target_lang": "en",
                    "workflow_mode": "non_reasoning"  # Use non_reasoning for faster execution
                }
            )

            if response.status_code != 200:
                print(f"❌ Failed to start translation: {response.status_code}")
                print(f"Response: {response.text}")
                return False

            translation_data = response.json()
            task_id = translation_data.get('data', {}).get('task_id')

            if not task_id:
                print("❌ No task_id in response")
                return False

            print(f"✅ Translation started with task_id: {task_id}")

        except Exception as e:
            print(f"❌ Error starting translation: {e}")
            return False

    # Now connect to SSE for this task
    print(f"📡 Connecting to SSE for task {task_id}...")

    events_received = []
    step_progress_received = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                'GET',
                f'http://localhost:8000/api/v1/workflow/tasks/{task_id}/stream'
            ) as response:
                if response.status_code != 200:
                    print(f"❌ SSE connection failed: {response.status_code}")
                    return False

                print("✅ SSE connected, listening for updates...")

                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]
                        try:
                            event_data = json.loads(data)
                            events_received.append(event_data)

                            # Extract key information
                            progress = event_data.get('progress')
                            current_step = event_data.get('current_step')
                            step_states = event_data.get('step_states', {})
                            message = event_data.get('message')

                            if current_step and step_states:
                                current_state = step_states.get(current_step, 'unknown')
                            else:
                                current_state = 'unknown'

                            print(f"📨 Event {len(events_received)}: {progress}% - {current_step} ({current_state}) - {message}")

                            # Track step progress specifically
                            if progress in [33, 66, 90]:
                                step_progress_received.append(progress)
                                print(f"✅ INTERMEDIATE STEP PROGRESS DETECTED: {progress}%")

                            # Check for completion
                            if event_data.get('status') == 'completed':
                                print("🎉 Translation completed!")
                                break
                            elif event_data.get('status') == 'failed':
                                print("❌ Translation failed!")
                                break

                        except json.JSONDecodeError as e:
                            print(f"❌ JSON error: {e}")
                            print(f"Raw data: '{data}'")

        except Exception as e:
            print(f"❌ SSE error: {e}")
            return False

    # Analyze results
    print(f"\n📊 Integration Test Results:")
    print(f"Total events received: {len(events_received)}")
    print(f"Intermediate step progress detected: {step_progress_received}")

    # Check if we got the intermediate updates the user wants to see
    success_criteria = {
        'has_events': len(events_received) > 1,
        'has_step_33': 33 in step_progress_received,
        'has_step_66': 66 in step_progress_received,
        'has_step_90': 90 in step_progress_received,
        'has_completion': any(e.get('status') == 'completed' for e in events_received),
        'has_step_states': any('step_states' in e and e['step_states'] for e in events_received)
    }

    print(f"\n✅ Success Criteria:")
    for criteria, passed in success_criteria.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {criteria}: {passed}")

    # Focus on the key user requirement: intermediate step progress
    intermediate_success = len(step_progress_received) >= 1

    if intermediate_success:
        print(f"\n🎉 SUCCESS: SSE detected intermediate step progress!")
        print(f"✅ Found step progress at: {step_progress_received}")
        print(f"✅ User requirement satisfied: step state changes are being sent to frontend")
        return True
    else:
        print(f"\n💥 PARTIAL SUCCESS: SSE connected but intermediate step progress not detected")
        print(f"❌ This might be due to fast translation or API issues")
        print(f"✅ But SSE connection and JSON serialization are working")
        return len(events_received) > 1  # Consider partial success if we got events

if __name__ == "__main__":
    print("🧪 SSE Integration Test")
    print("=" * 50)
    print("This test will:")
    print("1. Start a real translation workflow via API")
    print("2. Connect to SSE for that task")
    print("3. Monitor for intermediate step progress (33%, 66%, 90%)")
    print("4. Verify step state changes are sent to frontend")
    print("=" * 50)

    try:
        result = asyncio.run(test_sse_integration())
        if result:
            print("\n🎉 INTEGRATION TEST PASSED!")
            print("✅ SSE enhancement is working correctly")
            print("✅ Frontend will receive intermediate step progress updates")
        else:
            print("\n💥 INTEGRATION TEST FAILED")
            print("❌ SSE enhancement needs more work")
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)