"""
Core Utility Tools for Phase 3 Refactoring.

This module provides essential utility functions and classes that support
the Phase 3 refactoring efforts, including common patterns for async
operations, error handling, and resource management.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
import hashlib
import json
import logging
from functools import wraps, partial
import traceback


# ============================================================================
# Async Utilities
# ============================================================================

class AsyncTimer:
    """Context manager for timing async operations."""

    def __init__(self, name: str = "operation", logger: Optional[logging.Logger] = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.end_time = None
        self.duration = None

    async def __aenter__(self):
        self.start_time = time.time()
        if self.logger:
            self.logger.debug(f"Starting {self.name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if self.logger:
            self.logger.debug(f"Completed {self.name} in {self.duration:.3f}s")

    def get_duration(self) -> Optional[float]:
        """Get the duration of the timed operation."""
        return self.duration


@asynccontextmanager
async def timeout_context(timeout_seconds: float, operation_name: str = "operation"):
    """
    Async context manager with timeout.

    Args:
        timeout_seconds: Timeout in seconds
        operation_name: Name of the operation for error messages

    Yields:
        None

    Raises:
        asyncio.TimeoutError: If operation times out
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            yield
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Operation '{operation_name}' timed out after {timeout_seconds}s")


async def gather_with_errors(*tasks, return_exceptions: bool = False) -> List[Any]:
    """
    Gather tasks with better error handling.

    Args:
        *tasks: Tasks to gather
        return_exceptions: Whether to return exceptions instead of raising

    Returns:
        List of results or exceptions
    """
    if return_exceptions:
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    errors = []

    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            results.append(result)
        except Exception as e:
            errors.append(e)
            results.append(e)

    if errors and not return_exceptions:
        # Raise the first error
        raise errors[0]

    return results


async def batch_process(
    items: List[Any],
    processor: Callable,
    batch_size: int = 10,
    concurrency: int = 5
) -> AsyncGenerator[Any, None]:
    """
    Process items in batches with controlled concurrency.

    Args:
        items: Items to process
        processor: Async processor function
        batch_size: Size of each batch
        concurrency: Maximum concurrent operations

    Yields:
        Processed results
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def process_with_semaphore(item):
        async with semaphore:
            return await processor(item)

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        tasks = [process_with_semaphore(item) for item in batch]
        batch_results = await gather_with_errors(*tasks)
        for result in batch_results:
            yield result


# ============================================================================
# Error Handling and Resilience
# ============================================================================

@dataclass
class ErrorInfo:
    """Structured error information."""
    error_type: str
    message: str
    traceback: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


class ErrorCollector:
    """Collector for managing errors during operations."""

    def __init__(self, max_errors: int = 100):
        self.errors: List[ErrorInfo] = []
        self.max_errors = max_errors

    def add_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorInfo:
        """Add an error to the collector."""
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context
        )

        self.errors.append(error_info)

        # Maintain max size
        if len(self.errors) > self.max_errors:
            self.errors.pop(0)

        return error_info

    def get_errors(self, error_type: Optional[str] = None) -> List[ErrorInfo]:
        """Get errors, optionally filtered by type."""
        if error_type:
            return [e for e in self.errors if e.error_type == error_type]
        return self.errors.copy()

    def clear_errors(self) -> None:
        """Clear all errors."""
        self.errors.clear()

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def get_error_summary(self) -> Dict[str, int]:
        """Get a summary of error types."""
        summary = {}
        for error in self.errors:
            summary[error.error_type] = summary.get(error.error_type, 0) + 1
        return summary


def async_error_handler(
    error_collector: Optional[ErrorCollector] = None,
    default_return: Any = None,
    log_errors: bool = True
):
    """
    Decorator for handling errors in async functions.

    Args:
        error_collector: Optional error collector
        default_return: Default return value on error
        log_errors: Whether to log errors
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if error_collector:
                    error_collector.add_error(e, context={'function': func.__name__})

                if log_errors:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)

                if default_return is not None:
                    return default_return
                raise

        return wrapper
    return decorator


# ============================================================================
# Resource Management
# ============================================================================

class ResourceManager:
    """Manager for cleanup of resources."""

    def __init__(self):
        self.resources: List[Dict[str, Any]] = []

    def add_resource(
        self,
        resource: Any,
        cleanup_func: Optional[Callable] = None,
        name: Optional[str] = None
    ) -> None:
        """
        Add a resource to be managed.

        Args:
            resource: Resource to manage
            cleanup_func: Optional custom cleanup function
            name: Optional resource name for debugging
        """
        resource_info = {
            'resource': resource,
            'cleanup_func': cleanup_func,
            'name': name or str(resource),
            'created_at': time.time()
        }
        self.resources.append(resource_info)

    @contextmanager
    def managed_resource(self, resource: Any, cleanup_func: Optional[Callable] = None, name: Optional[str] = None):
        """Context manager for a single managed resource."""
        self.add_resource(resource, cleanup_func, name)
        try:
            yield resource
        finally:
            self.cleanup_resource(resource)

    def cleanup_resource(self, resource: Any) -> None:
        """Cleanup a specific resource."""
        for resource_info in reversed(self.resources):
            if resource_info['resource'] is resource:
                self._cleanup_resource_info(resource_info)
                self.resources.remove(resource_info)
                break

    def cleanup_all(self) -> None:
        """Cleanup all managed resources."""
        for resource_info in reversed(self.resources):
            self._cleanup_resource_info(resource_info)
        self.resources.clear()

    def _cleanup_resource_info(self, resource_info: Dict[str, Any]) -> None:
        """Cleanup a single resource info."""
        resource = resource_info['resource']
        cleanup_func = resource_info['cleanup_func']

        if cleanup_func:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    # For async cleanup, we need to handle this differently
                    # This is a limitation of sync cleanup
                    pass
                else:
                    cleanup_func(resource)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Error cleaning up {resource_info['name']}: {e}")

        # Generic cleanup methods
        for attr in ['close', 'cleanup', 'dispose']:
            if hasattr(resource, attr):
                try:
                    method = getattr(resource, attr)
                    if callable(method):
                        if asyncio.iscoroutinefunction(method):
                            # Note: Async cleanup would need to be awaited
                            pass
                        else:
                            method()
                    break
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error calling {attr} on {resource_info['name']}: {e}")


# ============================================================================
# Data Processing Utilities
# ============================================================================

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load JSON string.

    Args:
        json_str: JSON string to parse
        default: Default value on error

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump object to JSON string.

    Args:
        obj: Object to serialize
        default: Default string on error

    Returns:
        JSON string or default
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def generate_hash(data: Any, algorithm: str = 'sha256') -> str:
    """
    Generate hash of data.

    Args:
        data: Data to hash (will be converted to string)
        algorithm: Hash algorithm to use

    Returns:
        Hex digest of hash
    """
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data_str.encode('utf-8'))
    return hash_obj.hexdigest()


def generate_unique_id(prefix: Optional[str] = None) -> str:
    """
    Generate a unique ID with optional prefix.

    Args:
        prefix: Optional prefix for the ID

    Returns:
        Unique ID string
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def deep_merge_dict(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary (base)
        dict2: Second dictionary (overlay)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value

    return result


def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = '',
    sep: str = '.'
) -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


# ============================================================================
# Validation Utilities
# ============================================================================

class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that required fields are present in data.

    Args:
        data: Data to validate
        required_fields: List of required field names

    Raises:
        ValidationError: If required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {missing_fields}")


def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> None:
    """
    Validate field types in data.

    Args:
        data: Data to validate
        field_types: Dictionary of field name to expected type

    Raises:
        ValidationError: If field types don't match
    """
    for field, expected_type in field_types.items():
        if field in data and not isinstance(data[field], expected_type):
            raise ValidationError(
                f"Field '{field}' should be {expected_type.__name__}, "
                f"got {type(data[field]).__name__}"
            )


def validate_email(email: str) -> bool:
    """
    Simple email validation.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """
    Simple URL validation.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None


# ============================================================================
# Performance Monitoring
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    operation_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    error_count: int = 0

    @property
    def average_duration(self) -> float:
        """Calculate average duration."""
        return self.total_duration / max(self.operation_count, 1)

    def add_operation(self, duration: float, success: bool = True) -> None:
        """Add an operation measurement."""
        self.operation_count += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)

        if not success:
            self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'operation_count': self.operation_count,
            'average_duration': self.average_duration,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'error_count': self.error_count,
            'success_rate': (self.operation_count - self.error_count) / max(self.operation_count, 1)
        }


class PerformanceMonitor:
    """Performance monitoring utility."""

    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}

    def record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool = True
    ) -> None:
        """Record an operation performance."""
        if operation_name not in self.metrics:
            self.metrics[operation_name] = PerformanceMetrics()

        self.metrics[operation_name].add_operation(duration, success)

    async def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record HTTP request performance metrics."""
        operation_name = f"{method} {path}"
        success = status_code < 400

        self.record_operation(operation_name, duration_ms / 1000.0, success)

    def get_metrics(self, operation_name: str) -> Optional[PerformanceMetrics]:
        """Get metrics for a specific operation."""
        return self.metrics.get(operation_name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics as a dictionary."""
        return {name: metrics.get_summary() for name, metrics in self.metrics.items()}

    def reset_metrics(self, operation_name: Optional[str] = None) -> None:
        """Reset metrics for specific operation or all."""
        if operation_name:
            self.metrics.pop(operation_name, None)
        else:
            self.metrics.clear()

    @contextmanager
    def measure_operation(self, operation_name: str):
        """Context manager for measuring operation performance."""
        start_time = time.time()
        success = True

        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.record_operation(operation_name, duration, success)