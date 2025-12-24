# VPSWeb Repository - Background Task System Documentation

## Overview

The VPSWeb Repository Background Task System is a comprehensive, production-ready solution for managing asynchronous tasks, translation jobs, and system monitoring. Built on FastAPI BackgroundTasks with SQLite persistence, it provides enterprise-grade features including priority queuing, retry logic, circuit breakers, and real-time monitoring.

### Key Features

- **Priority-based Task Queue**: Intelligent task scheduling with configurable priorities
- **Comprehensive Retry Logic**: Exponential backoff, jitter, and category-based retry strategies
- **Circuit Breaker Pattern**: Protection against cascading failures in external services
- **Real-time Monitoring**: Task progress tracking, system health monitoring, and performance metrics
- **Database Persistence**: Full audit trail with SQLite (WAL mode) for reliability
- **VPSWeb Integration**: Seamless integration with VPSWeb translation workflows
- **API-first Design**: RESTful APIs for all system operations
- **Error Handling**: Sophisticated error classification and dead letter queue management

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  Background Tasks API  │  Monitoring API  │  Translation API    │
├─────────────────────────────────────────────────────────────────┤
│                     Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  Task Manager  │  Task Queue  │  VPSWeb Adapter  │  Monitor     │
├─────────────────────────────────────────────────────────────────┤
│                    Error Handling Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  Error Handler  │  Circuit Breakers  │  Retry Logic           │
├─────────────────────────────────────────────────────────────────┤
│                     Database Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  SQLite (WAL)  │  Task Models  │  Metrics  │  Queue State      │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Task Submission**: API receives task request → Task Manager creates context → Task Queue schedules execution
2. **Task Execution**: Queue processes task → Error handling manages retries → Progress tracking updates status
3. **Monitoring**: Real-time metrics collection → Health checks → Performance analytics
4. **Persistence**: All operations logged to database → Audit trail maintained → Historical analysis available

## Configuration

### Background Task Configuration

```yaml
background_tasks:
  enabled: true
  max_concurrent_jobs: 3
  job_timeout: 300  # 5 minutes
  cleanup_interval: 3600  # 1 hour

  # Enhanced task management
  max_retry_attempts: 3
  retry_delay: 60  # Base retry delay in seconds
  max_queue_size: 100
  queue_check_interval: 1.0  # Queue processing interval in seconds
  task_retention_hours: 24

  # Task-specific timeouts
  task_timeouts:
    translation: 600  # 10 minutes
    maintenance: 300  # 5 minutes
    cleanup: 120  # 2 minutes
    backup: 1800  # 30 minutes

  # Resource limits
  max_memory_mb: 512
  max_cpu_percent: 80.0

  # Queue management
  enable_priority_queue: true
  pause_on_overload: true
  overload_threshold: 0.9
```

### Monitoring Configuration

```yaml
task_monitoring:
  enable_health_checks: true
  health_check_interval: 60  # seconds
  enable_task_metrics: true
  metrics_history_size: 1000

  # Alert thresholds
  failed_task_threshold: 5
  queue_size_warning: 50
  memory_usage_warning: 0.8

  # Task lifecycle monitoring
  track_task_lifecycle: true
  enable_task_tracing: false
```

### System Resource Configuration

```yaml
system_resources:
  enable_resource_monitoring: true
  resource_check_interval: 30  # seconds

  # CPU thresholds
  max_cpu_usage: 80.0  # percentage
  cpu_warning_threshold: 70.0

  # Memory thresholds
  max_memory_usage_percent: 85.0
  memory_warning_threshold: 75.0

  # Disk thresholds
  max_disk_usage_percent: 90.0
  disk_warning_threshold: 80.0
```

## API Reference

### Background Tasks API

#### Task Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/background-tasks/submit` | POST | Submit a new background task |
| `/api/v1/background-tasks/status/{task_id}` | GET | Get task status and progress |
| `/api/v1/background-tasks/active` | GET | List all active tasks |
| `/api/v1/background-tasks/completed` | GET | List completed tasks |
| `/api/v1/background-tasks/statistics` | GET | Get comprehensive task statistics |
| `/api/v1/background-tasks/cancel/{task_id}` | POST | Cancel a running task |

#### Queue Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/background-tasks/queue/status` | GET | Get queue status and information |
| `/api/v1/background-tasks/queue/tasks` | GET | List queued tasks |
| `/api/v1/background-tasks/queue/running` | GET | List running tasks |
| `/api/v1/background-tasks/queue/clear` | POST | Clear all pending tasks |
| `/api/v1/background-tasks/queue/pause` | POST | Pause queue processing |
| `/api/v1/background-tasks/queue/resume` | POST | Resume queue processing |

#### Translation Jobs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/background-tasks/translation` | POST | Submit translation job |
| `/api/v1/background-tasks/translation/{job_id}` | GET | Get translation job status |
| `/api/v1/background-tasks/translation/{job_id}/result` | GET | Get translation job result |
| `/api/v1/background-tasks/translation/{job_id}/retry` | POST | Retry failed translation job |
| `/api/v1/background-tasks/translation/{job_id}` | DELETE | Cancel translation job |
| `/api/v1/background-tasks/translation/batch` | POST | Submit batch translation jobs |
| `/api/v1/background-tasks/translation/compare` | POST | Compare workflow modes |

#### System Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/background-tasks/health` | GET | System health check |
| `/api/v1/background-tasks/vpsweb/status` | GET | VPSWeb integration status |
| `/api/v1/background-tasks/vpsweb/health` | GET | VPSWeb comprehensive health check |

### Monitoring API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/monitoring/health` | GET | Current system health status |
| `/api/v1/monitoring/summary` | GET | Complete monitoring summary |
| `/api/v1/monitoring/metrics/performance` | GET | Performance metrics history |
| `/api/v1/monitoring/tasks/statistics` | GET | Task statistics |
| `/api/v1/monitoring/tasks/{task_id}/progress` | GET | Task progress information |
| `/api/v1/monitoring/tasks/{task_id}/history` | GET | Task progress history |
| `/api/v1/monitoring/alerts` | GET | Current alert status |
| `/api/v1/monitoring/system/resources` | GET | System resource usage |
| `/api/v1/monitoring/start` | POST | Start monitoring system |
| `/api/v1/monitoring/stop` | POST | Stop monitoring system |

## Usage Examples

### Submitting a Background Task

```python
import asyncio
import httpx

async def submit_task():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/background-tasks/submit",
            json={
                "task_name": "Data Processing Task",
                "task_type": "data_processing",
                "priority": "normal",
                "max_retries": 3,
                "timeout_seconds": 300,
                "metadata": {
                    "source_file": "data.csv",
                    "output_format": "json"
                }
            }
        )
        return response.json()

result = asyncio.run(submit_task())
print(f"Task submitted: {result['task_id']}")
```

### Submitting a Translation Job

```python
async def submit_translation():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/background-tasks/translation",
            json={
                "original_text": "Hello world, how are you?",
                "source_language": "en",
                "target_language": "zh-Hans",
                "workflow_mode": "hybrid",
                "metadata": {
                    "author": "Test Author",
                    "title": "Test Poem"
                }
            }
        )
        return response.json()

result = asyncio.run(submit_translation())
print(f"Translation job submitted: {result['job_id']}")
```

### Monitoring Task Progress

```python
async def monitor_task(task_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8000/api/v1/monitoring/tasks/{task_id}/progress"
        )
        return response.json()

progress = asyncio.run(monitor_task("task_id_here"))
print(f"Task progress: {progress['progress']:.1%} - {progress['message']}")
```

### Getting System Health Status

```python
async def get_system_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/monitoring/health"
        )
        return response.json()

health = asyncio.run(get_system_health())
print(f"System status: {health['status']}")
print(f"CPU usage: {health['cpu_usage']:.1f}%")
print(f"Memory usage: {health['memory_usage']:.1f}%")
print(f"Active tasks: {health['active_tasks']}")
```

## Error Handling and Retry Logic

### Error Categories

The system classifies errors into categories with appropriate retry strategies:

| Category | Description | Default Strategy | Max Attempts |
|----------|-------------|------------------|--------------|
| `network` | Network connectivity issues | Exponential backoff | 3 |
| `database` | Database operation failures | Exponential backoff | 2 |
| `external_service` | Third-party API failures | Exponential backoff | 5 |
| `timeout` | Operation timeouts | Linear backoff | 2 |
| `validation` | Input validation errors | No retry | 1 |
| `permission` | Authorization failures | No retry | 1 |
| `resource` | Resource exhaustion | Fixed interval | 3 |

### Retry Strategies

1. **Exponential Backoff**: `delay = base_delay * (multiplier ^ attempt)` with jitter
2. **Linear Backoff**: `delay = base_delay * (attempt + 1)`
3. **Fixed Interval**: Constant delay between attempts
4. **Immediate**: No delay between attempts
5. **No Retry**: Fail immediately

### Circuit Breaker Pattern

The system implements circuit breakers for external services:

- **Closed**: Normal operation, calls allowed
- **Open**: Failing state, calls rejected immediately
- **Half-Open**: Testing recovery, limited calls allowed

Configuration:
```python
circuit_breaker_config = {
    "failure_threshold": 5,      # Failures before opening
    "recovery_timeout": 60.0,    # Seconds before attempting recovery
    "half_open_max_calls": 3     # Max calls in half-open state
}
```

## Monitoring and Observability

### Key Metrics

#### Task Metrics
- Task completion rate (tasks/minute)
- Average task duration
- Queue processing rate
- Error rate by category
- Retry success rate

#### System Metrics
- CPU usage percentage
- Memory usage percentage
- Disk usage percentage
- Active task count
- Queued task count

#### Health Indicators
- Overall system health (healthy/degraded/unhealthy)
- Service availability status
- Resource utilization levels
- Alert status and thresholds

### Progress Tracking

Tasks provide real-time progress updates:

```python
# Task progress update example
progress_update = {
    "task_id": "uuid-here",
    "progress": 0.75,  # 75% complete
    "message": "Processing step 3 of 4",
    "status": "running",
    "timestamp": "2025-01-19T10:30:00Z",
    "metadata": {
        "current_step": "translation",
        "total_steps": 4
    }
}
```

### Alert System

The system generates alerts for:

- High error rates (>10% warning, >20% critical)
- Resource usage exceeding thresholds
- Queue size limits approached
- Service health degradation
- Circuit breaker activations

## Database Schema

### Core Tables

#### `background_tasks`
Main task records with status, progress, and metadata.

#### `task_executions`
Individual execution attempts for retry analysis.

#### `task_metrics`
Performance metrics and resource usage tracking.

#### `translation_jobs`
Translation job records with VPSWeb integration data.

#### `system_metrics`
System-wide performance and resource metrics.

### Key Relationships

- `background_tasks` → `task_executions` (one-to-many)
- `background_tasks` → `task_metrics` (one-to-many)
- `background_tasks` → `translation_jobs` (one-to-one, optional)

## Performance Considerations

### Resource Management

- **Concurrent Tasks**: Configurable limit (default: 3)
- **Memory Usage**: Per-task memory limits enforced
- **Queue Size**: Maximum queue size prevents overload
- **Timeouts**: Task-specific timeout configurations

### Optimization Features

- **SQLite WAL Mode**: Improved concurrency for read operations
- **Connection Pooling**: Efficient database connection management
- **Query Caching**: Frequently accessed query results cached
- **Cleanup Automation**: Automatic removal of old data

### Scaling Guidelines

#### For v0.3 (Current - Localhost Only)
- Single worker process
- SQLite database with WAL mode
- In-memory task queue
- Suitable for development and small-scale use

#### Upgrade Path to v0.4+
- Multiple worker processes
- PostgreSQL database support
- Distributed queue (Redis/RabbitMQ)
- External service integration
- Authentication and authorization

## Troubleshooting

### Common Issues

#### Tasks Not Starting
1. Check if background task system is enabled
2. Verify queue capacity limits
3. Review system resource availability
4. Check for circuit breaker activations

#### High Error Rates
1. Review error classification in logs
2. Check external service availability
3. Verify retry configuration appropriateness
4. Monitor resource constraints

#### Performance Issues
1. Monitor system resource usage
2. Check database query performance
3. Review task timeout settings
4. Analyze queue processing bottlenecks

### Debugging Tools

#### Health Check Endpoints
```bash
# System health
curl http://localhost:8000/api/v1/monitoring/health

# Task queue status
curl http://localhost:8000/api/v1/background-tasks/queue/status

# VPSWeb integration status
curl http://localhost:8000/api/v1/background-tasks/vpsweb/status
```

#### Log Analysis
```bash
# View recent task logs
tail -f repository_root/logs/repository.log | grep "Task"

# Filter by error level
grep "ERROR\|CRITICAL" repository_root/logs/repository.log

# Monitor specific task
grep "task_id:uuid-here" repository_root/logs/repository.log
```

## Security Considerations

### v0.3 (Localhost Only)
- No authentication required
- Localhost-only deployment (127.0.0.1)
- Single-user environment
- Development-focused security

### Future Security (v0.4+)
- Authentication and authorization
- API key management
- Role-based access control
- Audit logging
- Network security policies

## Best Practices

### Task Design
1. **Idempotent Operations**: Design tasks to be safely retryable
2. **Appropriate Timeouts**: Set reasonable timeouts based on task complexity
3. **Progress Updates**: Provide meaningful progress feedback
4. **Error Handling**: Handle expected errors gracefully
5. **Resource Cleanup**: Ensure proper cleanup on failure

### Configuration Management
1. **Environment-Specific Settings**: Use different configs for dev/prod
2. **Resource Limits**: Configure appropriate limits for your environment
3. **Monitoring Thresholds**: Set alert thresholds based on SLA requirements
4. **Backup Policies**: Regular database backups for production data

### Operational Procedures
1. **Regular Monitoring**: Monitor system health and performance metrics
2. **Log Review**: Regularly review logs for issues and optimization opportunities
3. **Capacity Planning**: Monitor resource usage and plan for scaling
4. **Testing**: Regular integration tests for all system components

## Integration Examples

### Custom Task Types

```python
from vpsweb.repository.tasks import TaskDefinition, get_task_manager

async def create_custom_task():
    task_manager = get_task_manager()

    task_def = TaskDefinition(
        name="Custom Data Processing",
        task_type="custom_processing",
        priority=TaskPriority.HIGH,
        max_retries=3,
        timeout_seconds=600,
        metadata={
            "input_source": "external_api",
            "output_destination": "database"
        }
    )

    async def custom_task_function(context):
        # Your custom logic here
        await context.update_progress(0.1, "Starting processing")
        # ... processing steps ...
        await context.update_progress(1.0, "Processing complete")
        return {"status": "success", "records_processed": 100}

    context = task_manager.create_task(task_def, custom_task_function)
    return context.task_id
```

### Monitoring Integration

```python
from vpsweb.repository.monitoring import get_task_monitor

async def setup_custom_monitoring():
    monitor = get_task_monitor()

    def progress_listener(update):
        print(f"Task {update.task_id}: {update.progress:.1%} - {update.message}")
        # Send to external monitoring system
        # webhook_notification(update)

    monitor.add_progress_listener("task_id_here", progress_listener)
```

### Error Handling Integration

```python
from vpsweb.repository.error_handling import with_retry, with_circuit_breaker

@with_retry(retry_config=RetryConfig(
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    max_attempts=5
))
@with_circuit_breaker("external_api_service")
async def external_api_call():
    # Your external API call here
    response = await some_external_api_call()
    return response
```

## Glossary

| Term | Definition |
|------|------------|
| **Background Task** | Asynchronous operation executed independently of the main request flow |
| **Task Queue** | Priority-based scheduling system for managing task execution order |
| **Circuit Breaker** | Pattern to prevent cascading failures in external service calls |
| **Exponential Backoff** | Retry strategy with increasing delay between attempts |
| **Dead Letter Queue** | Storage for tasks that have failed after all retry attempts |
| **Task Context** | Object containing task metadata, status, and execution information |
| **Progress Tracking** | Real-time monitoring of task execution progress |
| **Health Check** | System status verification for monitoring and alerting |

## Support and Contributing

For support, questions, or contributions to the background task system:

1. **Documentation**: Refer to this guide and inline code documentation
2. **Issues**: Report bugs or feature requests via GitHub issues
3. **Testing**: Run the comprehensive test suite before making changes
4. **Code Style**: Follow the established code patterns and conventions

---

*Last Updated: January 19, 2025*
*Version: v0.3.0*