# Rotating File Logging Guide for VPSWeb

**Date**: 2025-10-19
**Version**: v0.3.1
**Purpose**: Complete guide to rotating file logging implementation and management

## 🎯 Overview

VPSWeb includes a comprehensive rotating file logging system that automatically manages log file size, creates backups, and provides structured logging capabilities. This system helps maintain disk space while preserving important application logs.

## 📁 Log File Structure

```
logs/
├── vpsweb.log              # Main log file
├── vpsweb.log.1            # Backup 1 (most recent)
├── vpsweb.log.2            # Backup 2
├── vpsweb.log.3            # Backup 3
└── vpsweb_timed.log        # Time-based log file (optional)
```

## 🚀 Quick Start

### 1. Interactive Demo

```bash
# Run comprehensive logging demonstration
python scripts/demo_rotating_logging.py --mode demo

# Check current logging status
python scripts/demo_rotating_logging.py --mode status

# Generate test log entries
python scripts/demo_rotating_logging.py --mode test --count 100

# Clean up old log files
python scripts/demo_rotating_logging.py --mode cleanup --days 7
```

### 2. Basic Usage in Code

```python
from src.vpsweb.utils.logger import get_logger, setup_logging

# Get a logger
logger = get_logger(__name__)

# Use different log levels
logger.debug("Detailed debugging information")
logger.info("General application information")
logger.warning("Something unexpected but not fatal")
logger.error("Something went wrong")
logger.critical("Serious error occurred")

# Structured logging with context
workflow_data = {
    "workflow_id": "workflow-123",
    "source_lang": "English",
    "target_lang": "Chinese",
    "tokens_used": 1250
}
context_str = " | ".join(f"{k}={v}" for k, v in workflow_data.items())
logger.info(f"Workflow completed | {context_str}")
```

## ⚙️ Configuration

### Configuration in YAML

```yaml
# config/default.yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/vpsweb.log"
  max_file_size: 10485760  # 10MB
  backup_count: 5
```

### Configuration via Code

```python
from src.vpsweb.models.config import LoggingConfig, LogLevel
from src.vpsweb.utils.logger import setup_logging

# Create logging configuration
log_config = LoggingConfig(
    level=LogLevel.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    file="logs/vpsweb.log",
    max_file_size=10 * 1024 * 1024,  # 10MB
    backup_count=5,
)

# Initialize logging
setup_logging(log_config)
```

## 🔄 Rotation Types

### Size-Based Rotation

The default rotation method based on file size:

- **Default Max Size**: 10MB (configurable)
- **Default Backups**: 5 files
- **Rotation Trigger**: When current log file reaches max size
- **Backup Naming**: `vpsweb.log.1`, `vpsweb.log.2`, etc.

### Time-Based Rotation

Optional time-based rotation for daily logs:

```python
import logging.handlers
from datetime import datetime

# Create time-based rotating handler
time_handler = logging.handlers.TimedRotatingFileHandler(
    filename="logs/vpsweb_daily.log",
    when="midnight",     # Rotate at midnight
    interval=1,           # Every day
    backupCount=30,       # Keep 30 days
    encoding="utf-8",
)

# Add to logger
logger = get_logger("vpsweb.daily")
logger.addHandler(time_handler)
```

## 📊 Log Levels

### Available Levels

1. **DEBUG** (10): Detailed information for troubleshooting
2. **INFO** (20): General application information
3. **WARNING** (30): Something unexpected but not fatal
4. **ERROR** (40): Something went wrong
5. **CRITICAL** (50): Serious error occurred

### Setting Log Levels

```python
# Set log level for all handlers
from src.vpsweb.utils.logger import set_log_level
set_log_level("DEBUG")  # Most verbose
set_log_level("INFO")   # Default
set_log_level("WARNING") # Less verbose
```

## 🏗️ Structured Logging

### Contextual Logging

```python
from src.vpsweb.utils.logger import (
    log_workflow_start, log_workflow_step, log_workflow_completion,
    log_api_call, log_error_with_context
)

# Workflow logging
log_workflow_start("workflow-123", "English", "Chinese", 156)
log_workflow_step("workflow-123", "initial_translation", 334, 2.5)
log_workflow_completion("workflow-123", 1250, 15.7)

# API call logging
log_api_call("tongyi", "qwen-max", 89, 245)

# Error logging with context
log_error_with_context(
    error=exception,
    context="translation_step",
    workflow_id="workflow-123"
)
```

### Custom Structured Logging

```python
import json

def log_structured_event(event_type: str, data: dict):
    """Log structured event with JSON data."""
    logger = get_logger("vpsweb.events")
    context_str = json.dumps(data, separators=(',', ':'))
    logger.info(f"Event: {event_type} | {context_str}")

# Usage
log_structured_event("user_action", {
    "user_id": "user-123",
    "action": "create_poem",
    "poem_title": "Test Poem",
    "timestamp": datetime.now().isoformat()
})
```

## 📁 Log File Management

### Monitoring Log Files

```bash
# Check current log file status
python scripts/demo_rotating_logging.py --mode status

# List all log files
ls -la logs/

# Monitor log file growth in real-time
tail -f logs/vpsweb.log

# Check log file sizes
du -h logs/*
```

### Manual Log Rotation

```python
from src.vpsweb.utils.logger import get_log_file_info
import logging.handlers

# Force rotation of current log file
logger = get_logger(__name__)
for handler in logger.handlers:
    if isinstance(handler, logging.handlers.RotatingFileHandler):
        # Trigger rotation by calling doRollover
        handler.doRollover()
```

### Log File Cleanup

```bash
# Clean up logs older than 7 days
python scripts/demo_rotating_logging.py --mode cleanup --days 7

# Custom cleanup (keep last N MB)
find logs/ -name "*.log*" -size +50M -delete
```

## 🔧 Advanced Configuration

### Multiple Log Files

```python
import logging
import logging.handlers
from src.vpsweb.utils.logger import setup_logging

# Setup main application logging
setup_logging(log_config)

# Add separate log files for different components
# API access logs
api_handler = logging.handlers.RotatingFileHandler(
    "logs/api.log",
    maxBytes=5*1024*1024,  # 5MB
    backupCount=3,
    encoding="utf-8"
)
api_formatter = logging.Formatter('%(asctime)s - %(message)s')
api_handler.setFormatter(api_formatter)

api_logger = logging.getLogger("vpsweb.api")
api_logger.addHandler(api_handler)

# Database operation logs
db_handler = logging.handlers.RotatingFileHandler(
    "logs/database.log",
    maxBytes=2*1024*1024,  # 2MB
    backupCount=2,
    encoding="utf-8"
)
db_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
db_handler.setFormatter(db_formatter)

db_logger = logging.getLogger("vpsweb.database")
db_logger.addHandler(db_handler)
```

### Conditional Logging

```python
import os
from src.vpsweb.utils.logger import get_logger

logger = get_logger(__name__)

# Log differently based on environment
if os.getenv("ENVIRONMENT") == "production":
    logger.info("Production mode: Detailed error logging enabled")
    # In production, log more details for errors
    def log_production_error(error, context=""):
        logger.error(f"Production Error: {str(error)}", exc_info=True)
        if context:
            logger.error(f"Context: {context}")
else:
    logger.info("Development mode: Verbose logging enabled")
    # In development, log everything with debug details
    logger.debug("Development debug information")
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Logging Not Initialized

**Problem**: `get_logger()` returns a logger that doesn't output anything.

**Solution**: Initialize logging first:
```python
from src.vpsweb.utils.logger import setup_logging, get_logger

setup_logging(log_config)  # Initialize first
logger = get_logger(__name__)  # Then get logger
```

#### 2. Log Files Not Created

**Problem**: No log files appear in the logs directory.

**Solution**: Check permissions and paths:
```bash
# Check if logs directory exists and is writable
ls -la logs/
python -c "import os; print('Writable:', os.access('logs/', os.W_OK))"
```

#### 3. No Rotation Happening

**Problem**: Log files grow indefinitely without rotation.

**Solution**: Check if the file handler is properly configured:
```python
from src.vpsweb.utils.logger import get_log_file_info

log_info = get_log_file_info()
if log_info:
    print(f"Max size: {log_info['max_size']}")
    print(f"Current size: {log_info['file_size']}")
    print(f"Rotation should trigger at: {log_info['max_size']}")
else:
    print("No file logging configured")
```

#### 4. Too Many Log Files

**Problem**: Log directory filling up with old backups.

**Solution**: Reduce backup count or implement cleanup:
```bash
# Reduce backup count to 3
# In config: backup_count: 3

# Clean up old logs
python scripts/demo_rotating_logging.py --mode cleanup --days 7
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
# Set debug level
from src.vpsweb.utils.logger import set_log_level
set_log_level("DEBUG")

# Use debug logging
from src.vpsweb.utils.logger import debug_log
debug_log("Debug message", user_id="user-123", action="test")
```

## 📈 Performance Considerations

### Logging Best Practices

1. **Use Appropriate Log Levels**
   ```python
   # Good - use appropriate levels
   logger.info("User logged in")  # Important business event
   logger.debug("Cache hit")      # Technical detail only

   # Avoid - excessive logging
   logger.debug("Loop iteration 1")
   logger.debug("Loop iteration 2")
   # ... thousands of times
   ```

2. **Avoid Logging in Hot Paths**
   ```python
   # Bad - logging in tight loop
   for item in large_list:
       logger.debug(f"Processing {item}")  # This will be very slow

   # Good - log summary instead
   logger.info(f"Processing {len(large_list)} items")
   ```

3. **Use Lazy String Formatting**
   ```python
   # Bad - always creates string
   logger.debug(f"Processing user {user.name} with data {expensive_data}")

   # Good - only creates string if log level allows
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug(f"Processing user {user.name} with data {expensive_data}")
   ```

### Monitoring Log Performance

```python
import time
from src.vpsweb.utils.logger import get_logger

def performance_aware_log(logger, message, level=logging.INFO):
    """Log message with performance tracking."""
    start_time = time.time()
    logger.log(level, message)
    duration = time.time() - start_time

    if duration > 0.01:  # Log if takes more than 10ms
        logger.warning(f"Slow logging operation: {duration:.3f}s for '{message[:50]}...'")
```

## 📚 Integration Examples

### FastAPI Integration

```python
from fastapi import Request, HTTPException
from src.vpsweb.utils.logger import get_logger

logger = get_logger("vpsweb.api")

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log request
        logger.info(
            f"API Request: {request.method} {request.url.path} "
            f"- {response.status_code} - {process_time:.3f}s"
        )

        return response

    except HTTPException as e:
        logger.error(f"HTTP Exception: {e.status_code} {request.url.path}")
        raise
    except Exception as e:
        logger.error(f"Unhandled exception: {request.url.path}", exc_info=True)
        raise
```

### Background Task Integration

```python
from src.vpsweb.utils.logger import log_workflow_start, log_workflow_completion

async def process_translation_task(task_id: str, poem_data: dict):
    """Process translation in background."""
    logger = get_logger("vpsweb.background")

    try:
        log_workflow_start(task_id, poem_data['source_lang'],
                          poem_data['target_lang'], len(poem_data['text']))

        # ... processing logic ...

        log_workflow_completion(task_id, tokens_used, duration)
        logger.info(f"Background task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
```

## 🔍 Monitoring and Analytics

### Log Analysis Commands

```bash
# Count error messages in last 1000 lines
tail -1000 logs/vpsweb.log | grep -c "ERROR"

# Find most common log messages
tail -1000 logs/vpsweb.log | awk '{print $0}' | sort | uniq -c | sort -nr | head -10

# Filter logs by date range
grep "2025-10-19" logs/vpsweb.log

# Real-time error monitoring
tail -f logs/vpsweb.log | grep -E "(ERROR|CRITICAL)"
```

### Log Metrics

```python
import re
from collections import Counter
from datetime import datetime, timedelta

def analyze_logs(hours: int = 24):
    """Analyze log files for metrics."""
    logger = get_logger("vpsweb.analytics")

    cutoff = datetime.now() - timedelta(hours=hours)
    log_levels = Counter()
    components = Counter()

    with open("logs/vpsweb.log", "r") as f:
        for line in f:
            # Extract timestamp and log level
            if re.match(r'\d{4}-\d{2}-\d{2}', line):
                log_level_match = re.search(r' - (DEBUG|INFO|WARNING|ERROR|CRITICAL) -', line)
                if log_level_match:
                    log_levels[log_level_match.group(1)] += 1

                # Extract component name
                component_match = re.search(r' - (vpsweb\.[^ -]+) -', line)
                if component_match:
                    components[component_match.group(1)] += 1

    logger.info(f"Log analysis for last {hours} hours:")
    logger.info(f"  Log levels: {dict(log_levels)}")
    logger.info(f"  Components: {dict(components.most_common(5))}")
```

---

**Last Updated**: 2025-10-19
**Maintainer**: VPSWeb Development Team