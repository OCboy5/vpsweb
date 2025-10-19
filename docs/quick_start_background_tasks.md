# VPSWeb Repository - Background Tasks Quick Start Guide

## Overview

This guide helps you get started with the VPSWeb Repository Background Task System quickly. You'll learn how to submit tasks, monitor progress, and handle translation jobs.

## Prerequisites

- VPSWeb Repository v0.3.0 or later
- Python 3.8+ with Poetry
- SQLite database support
- Localhost development environment

## Quick Setup

### 1. Start the Repository System

```bash
# Navigate to the repository directory
cd /Volumes/Work/Dev/vpsweb/vpsweb

# Start the repository server
python -m vpsweb.repository.server

# The server will start on http://127.0.0.1:8000
```

### 2. Verify System Health

```bash
# Check if the system is running
curl http://127.0.0.1:8000/api/v1/monitoring/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-01-19T10:30:00Z",
#   "cpu_usage": 15.2,
#   "memory_usage": 45.8,
#   ...
# }
```

## Basic Usage

### Submit a Simple Background Task

```python
import httpx
import asyncio

async def submit_simple_task():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/background-tasks/submit",
            json={
                "task_name": "My First Task",
                "task_type": "example",
                "priority": "normal",
                "max_retries": 3,
                "timeout_seconds": 60,
                "metadata": {
                    "user": "demo_user",
                    "purpose": "learning"
                }
            }
        )
        return response.json()

# Run the example
result = asyncio.run(submit_simple_task())
task_id = result["task_id"]
print(f"Task submitted successfully! ID: {task_id}")
```

### Monitor Task Progress

```python
async def check_task_progress(task_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://127.0.0.1:8000/api/v1/monitoring/tasks/{task_id}/progress"
        )
        return response.json()

progress = asyncio.run(check_task_progress(task_id))
print(f"Progress: {progress['progress']:.1%}")
print(f"Status: {progress['status']}")
print(f"Message: {progress['message']}")
```

### Submit a Translation Job

```python
async def submit_translation_job():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/background-tasks/translation",
            json={
                "original_text": "The quick brown fox jumps over the lazy dog.",
                "source_language": "en",
                "target_language": "zh-Hans",
                "workflow_mode": "hybrid",
                "metadata": {
                    "author": "Example Author",
                    "title": "Example Translation"
                }
            }
        )
        return response.json()

# Submit translation job
translation_result = asyncio.run(submit_translation_job())
job_id = translation_result["job_id"]
print(f"Translation job submitted! ID: {job_id}")
```

### Get Translation Result

```python
async def get_translation_result(job_id):
    async with httpx.AsyncClient() as client:
        # First check if job is complete
        status_response = await client.get(
            f"http://127.0.0.1:8000/api/v1/background-tasks/translation/{job_id}"
        )
        status = status_response.json()

        if status["status"] == "completed":
            # Get the full result
            result_response = await client.get(
                f"http://127.0.0.1:8000/api/v1/background-tasks/translation/{job_id}/result"
            )
            return result_response.json()
        else:
            return {"status": status["status"], "message": "Job not yet completed"}

# Get translation result
result = asyncio.run(get_translation_result(job_id))
if result["status"] == "completed":
    print(f"Original: {result['result']['original_text']}")
    print(f"Translated: {result['result']['translated_text']}")
    print(f"Quality Score: {result['result']['quality_score']}")
else:
    print(f"Job status: {result['status']}")
```

## Advanced Features

### Batch Translation Jobs

```python
async def submit_batch_translation():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/background-tasks/translation/batch",
            json={
                "jobs": [
                    {
                        "original_text": "Hello world",
                        "source_language": "en",
                        "target_language": "zh-Hans",
                        "workflow_mode": "hybrid"
                    },
                    {
                        "original_text": "Good morning",
                        "source_language": "en",
                        "target_language": "zh-Hans",
                        "workflow_mode": "reasoning"
                    }
                ],
                "priority": "normal",
                "metadata": {
                    "batch_id": "demo_batch_001"
                }
            }
        )
        return response.json()

batch_result = asyncio.run(submit_batch_translation())
for i, job in enumerate(batch_result):
    print(f"Job {i+1}: {job['job_id']} - {job['status']}")
```

### Compare Workflow Modes

```python
async def compare_workflows():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/background-tasks/translation/compare",
            json={
                "original_text": "Technology transforms how we communicate",
                "source_language": "en",
                "target_language": "zh-Hans",
                "workflow_modes": ["reasoning", "non_reasoning", "hybrid"],
                "metadata": {
                    "comparison_purpose": "quality_analysis"
                }
            }
        )
        return response.json()

comparison_result = asyncio.run(compare_workflows())
for job in comparison_result:
    print(f"Workflow: {job['message']} - Job ID: {job['job_id']}")
```

## Monitoring and Management

### View System Statistics

```python
async def get_system_stats():
    async with httpx.AsyncClient() as client:
        # Get task statistics
        tasks_response = await client.get(
            "http://127.0.0.1:8000/api/v1/monitoring/tasks/statistics"
        )

        # Get queue status
        queue_response = await client.get(
            "http://127.0.0.1:8000/api/v1/background-tasks/queue/status"
        )

        # Get performance metrics
        metrics_response = await client.get(
            "http://127.0.0.1:8000/api/v1/monitoring/metrics/performance?limit=10"
        )

        return {
            "tasks": tasks_response.json(),
            "queue": queue_response.json(),
            "metrics": metrics_response.json()
        }

stats = asyncio.run(get_system_stats())
print(f"Active Tasks: {stats['tasks']['derived_statistics']['active_tasks']}")
print(f"Success Rate: {stats['tasks']['derived_statistics']['success_rate']:.1%}")
print(f"Queue Size: {stats['queue']['queue_size']}")
```

### Manage Task Queue

```python
async def manage_queue():
    async with httpx.AsyncClient() as client:
        # Pause queue processing
        await client.post("http://127.0.0.1:8000/api/v1/background-tasks/queue/pause")
        print("Queue paused")

        # View queued tasks
        queued = await client.get("http://127.0.0.1:8000/api/v1/background-tasks/queue/tasks")
        print(f"Queued tasks: {len(queued.json())}")

        # Resume queue processing
        await client.post("http://127.0.0.1:8000/api/v1/background-tasks/queue/resume")
        print("Queue resumed")

# asyncio.run(manage_queue())
```

### View System Resources

```python
async def check_system_resources():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:8000/api/v1/monitoring/system/resources"
        )
        return response.json()

resources = asyncio.run(check_system_resources())
print(f"CPU Usage: {resources['cpu']['usage_percent']:.1f}%")
print(f"Memory Usage: {resources['memory']['usage_percent']:.1f}%")
print(f"Disk Usage: {resources['disk']['usage_percent']:.1f}%")
```

## Error Handling

### Handle Failed Tasks

```python
async def handle_failed_task(task_id):
    async with httpx.AsyncClient() as client:
        # Get task status
        response = await client.get(
            f"http://127.0.0.1:8000/api/v1/background-tasks/status/{task_id}"
        )
        task_status = response.json()

        if task_status["status"] in ["failed", "cancelled"]:
            print(f"Task failed: {task_status['error']}")

            # Check if retry is possible
            if task_status["retry_count"] < task_status["max_retries"]:
                print("Task can be retried")
                # Implement retry logic here
            else:
                print("Max retries exceeded")
        else:
            print(f"Task status: {task_status['status']}")

# Example usage
# asyncio.run(handle_failed_task("your_task_id_here"))
```

### Retry Failed Translation Job

```python
async def retry_translation_job(job_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://127.0.0.1:8000/api/v1/background-tasks/translation/{job_id}/retry"
        )
        return response.json()

# Example usage
# retry_result = asyncio.run(retry_translation_job("failed_job_id"))
# print(f"Retry submitted: {retry_result['job_id']}")
```

## Configuration Examples

### Update Background Task Configuration

Edit `config/repository.yaml`:

```yaml
background_tasks:
  enabled: true
  max_concurrent_jobs: 5  # Increase for more parallelism
  job_timeout: 600        # 10 minutes for longer tasks

  # Retry configuration
  max_retry_attempts: 5
  retry_delay: 30        # 30 seconds base delay

  # Queue management
  max_queue_size: 200     # Larger queue for high volume
  enable_priority_queue: true
```

### Configure Monitoring Alerts

```yaml
task_monitoring:
  enable_health_checks: true
  health_check_interval: 30  # More frequent checks

  # Alert thresholds
  failed_task_threshold: 3   # Alert after 3 consecutive failures
  queue_size_warning: 25     # Alert at 25 queued tasks
  memory_usage_warning: 0.7  # Alert at 70% memory usage
```

## Common Patterns

### Custom Task with Progress Updates

```python
async def create_custom_task():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/background-tasks/submit",
            json={
                "task_name": "Custom Processing Task",
                "task_type": "custom_processing",
                "priority": "high",
                "max_retries": 3,
                "timeout_seconds": 300,
                "metadata": {
                    "input_file": "data.csv",
                    "output_format": "json",
                    "processing_steps": 5
                }
            }
        )
        return response.json()

# In your custom task implementation, update progress like this:
# await context.update_progress(0.2, "Step 1: Reading input file")
# await context.update_progress(0.6, "Step 3: Processing data")
# await context.update_progress(1.0, "Processing complete")
```

### Poll for Task Completion

```python
async def wait_for_completion(task_id, timeout=300):
    import time
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            response = await client.get(
                f"http://127.0.0.1:8000/api/v1/monitoring/tasks/{task_id}/progress"
            )
            progress = response.json()

            if progress["status"] in ["completed", "failed", "cancelled"]:
                return progress

            print(f"Progress: {progress['progress']:.1%} - {progress['message']}")
            await asyncio.sleep(5)  # Check every 5 seconds

        raise TimeoutError("Task did not complete within timeout period")

# Usage
# result = asyncio.run(wait_for_completion(task_id))
# print(f"Final status: {result['status']}")
```

## Troubleshooting

### Common Issues and Solutions

#### Task Not Starting
```bash
# Check if background tasks are enabled
curl http://127.0.0.1:8000/api/v1/background-tasks/health

# Check queue status
curl http://127.0.0.1:8000/api/v1/background-tasks/queue/status
```

#### High Error Rates
```bash
# Get error statistics
curl http://127.0.0.1:8000/api/v1/monitoring/alerts

# Check system resources
curl http://127.0.0.1:8000/api/v1/monitoring/system/resources
```

#### Translation Jobs Failing
```bash
# Check VPSWeb integration status
curl http://127.0.0.1:8000/api/v1/background-tasks/vpsweb/status

# Check VPSWeb health
curl http://127.0.0.1:8000/api/v1/background-tasks/vpsweb/health
```

## Next Steps

1. **Explore the Full API**: Check all available endpoints in the main documentation
2. **Implement Custom Tasks**: Create tasks specific to your use case
3. **Set Up Monitoring**: Configure alerts and monitoring for production use
4. **Review Configuration**: Optimize settings for your workload
5. **Run Integration Tests**: Test your implementation thoroughly

## Getting Help

- **Documentation**: See [background_task_system.md](background_task_system.md) for comprehensive details
- **Examples**: Check the `tests/` directory for more integration examples
- **Issues**: Report problems via GitHub issues
- **Logs**: Monitor `repository_root/logs/repository.log` for detailed information

---

*Happy task processing! 🚀*