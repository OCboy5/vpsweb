"""
Logging utilities for Vox Poetica Studio Web.

This module provides centralized logging configuration and utilities
for consistent logging throughout the application, following the
configuration specified in config/default.yaml.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class LoggerSetupError(Exception):
    """Raised when logging setup fails."""

    pass


# Global flag to track if logging has been initialized
_logging_initialized = False


def setup_logging(config) -> None:
    """
    Initialize logging configuration for the entire application.

    This function should be called once at application startup to configure
    the logging system according to the provided configuration.

    Args:
        config: Logging configuration from config/default.yaml or LogLevel enum

    Raises:
        LoggerSetupError: If logging setup fails
    """
    global _logging_initialized

    if _logging_initialized:
        # Logging already initialized, skip to avoid duplicate handlers
        return

    try:
        # Clear any existing handlers to avoid duplication
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Handle both LoggingConfig object and LogLevel enum
        if hasattr(config, "level"):
            # It's a LoggingConfig object
            level = config.level.value
            log_format = config.format
            max_file_size = config.max_file_size
            backup_count = config.backup_count
            log_file = config.file
        else:
            # It's a LogLevel enum
            level = config.value if hasattr(config, "value") else config
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            max_file_size = 10485760  # 10MB default
            backup_count = 5
            log_file = "logs/vpsweb.log"

        # Set the root logger level
        root_logger.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(log_format)

        # Console handler (always enabled)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler (if file path is specified)
        if log_file:
            log_file_path = Path(log_file)

            # Create log directory if it doesn't exist
            log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler with size-based rotation
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Configure specific loggers for our application
        _configure_application_loggers(level)

        _logging_initialized = True

        # Log successful initialization
        logger = get_logger(__name__)
        logger.info("Logging system initialized successfully")
        logger.debug(f"Log level: {level}")
        logger.debug(f"Log file: {log_file}")
        logger.debug(f"Max file size: {max_file_size} bytes")
        logger.debug(f"Backup count: {backup_count}")

    except Exception as e:
        # Fallback to basic console logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.error(f"Failed to setup logging: {e}")
        fallback_logger.info("Using fallback console logging")
        raise LoggerSetupError(f"Failed to setup logging: {e}")


def _configure_application_loggers(level: str) -> None:
    """
    Configure specific loggers for different parts of the application.

    Args:
        level: Logging level to set for all loggers
    """
    # Set levels for specific loggers
    loggers_config = {
        # Core application components
        "vpsweb": level,
        "vpsweb.core": level,
        "vpsweb.services": level,
        "vpsweb.models": level,
        "vpsweb.utils": level,
        # External libraries - reduce noise
        "httpx": "WARNING",
        "urllib3": "WARNING",
        "asyncio": "WARNING",
    }

    for logger_name, logger_level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        # Don't propagate to root logger to avoid duplicate messages
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance for the specified name.

    This function returns a logger that follows the application's
    logging configuration. If logging hasn't been initialized yet,
    it will return a basic logger that will be properly configured
    once setup_logging() is called.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logging.Logger instance
    """
    logger = logging.getLogger(name)

    # If logging hasn't been initialized, add a temporary handler
    # to avoid "No handlers could be found" warnings
    if not _logging_initialized and not logger.handlers:
        # Add a null handler to suppress warnings
        logger.addHandler(logging.NullHandler())

    return logger


def set_log_level(level: str) -> None:
    """
    Dynamically change the logging level for all handlers.

    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Raises:
        ValueError: If the level is invalid
    """
    if not _logging_initialized:
        raise LoggerSetupError("Logging not initialized. Call setup_logging() first.")

    # Validate level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    # Convert string level to logging constant
    level_constant = getattr(logging, level)

    # Update root logger and all handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(level_constant)

    for handler in root_logger.handlers:
        handler.setLevel(level_constant)

    # Update application-specific loggers
    _configure_application_loggers(level)

    logger = get_logger(__name__)
    logger.info(f"Log level changed to: {level}")


def get_log_file_info() -> Optional[dict]:
    """
    Get information about the current log file configuration.

    Returns:
        Dictionary with log file information, or None if no file handler
    """
    if not _logging_initialized:
        return None

    root_logger = logging.getLogger()
    file_handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, logging.handlers.RotatingFileHandler)
    ]

    if not file_handlers:
        return None

    handler = file_handlers[0]
    log_file = Path(handler.baseFilename)

    return {
        "file_path": str(log_file.absolute()),
        "file_size": log_file.stat().st_size if log_file.exists() else 0,
        "max_size": handler.maxBytes,
        "backup_count": handler.backupCount,
        "encoding": handler.encoding,
    }


def log_workflow_start(
    workflow_id: str, source_lang: str, target_lang: str, poem_length: int
) -> None:
    """
    Log the start of a translation workflow.

    Args:
        workflow_id: Unique workflow identifier
        source_lang: Source language
        target_lang: Target language
        poem_length: Length of the poem in characters
    """
    logger = get_logger("vpsweb.workflow")
    logger.info(
        f"Starting translation workflow {workflow_id}: "
        f"{source_lang} → {target_lang}, {poem_length} chars"
    )


def log_workflow_step(
    workflow_id: str, step_name: str, tokens_used: int, duration: float
) -> None:
    """
    Log the completion of a workflow step.

    Args:
        workflow_id: Unique workflow identifier
        step_name: Name of the completed step
        tokens_used: Number of tokens used in this step
        duration: Execution time in seconds
    """
    logger = get_logger("vpsweb.workflow")
    logger.info(
        f"Workflow {workflow_id} - {step_name}: "
        f"{tokens_used} tokens, {duration:.2f}s"
    )


def log_workflow_completion(
    workflow_id: str, total_tokens: int, total_duration: float
) -> None:
    """
    Log the successful completion of a translation workflow.

    Args:
        workflow_id: Unique workflow identifier
        total_tokens: Total tokens used across all steps
        total_duration: Total execution time in seconds
    """
    logger = get_logger("vpsweb.workflow")
    logger.info(
        f"Workflow {workflow_id} completed successfully: "
        f"{total_tokens} total tokens, {total_duration:.2f}s total"
    )


def log_api_call(
    provider: str, model: str, prompt_length: int, response_length: int
) -> None:
    """
    Log an API call to an LLM provider.

    Args:
        provider: LLM provider name
        model: Model name used
        prompt_length: Length of the prompt in characters
        response_length: Length of the response in characters
    """
    logger = get_logger("vpsweb.api")
    logger.debug(
        f"API call: {provider}/{model}, "
        f"prompt: {prompt_length} chars, response: {response_length} chars"
    )


def log_error_with_context(
    error: Exception, context: str = "", workflow_id: str = ""
) -> None:
    """
    Log an error with additional context information.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        workflow_id: Workflow ID if applicable
    """
    logger = get_logger("vpsweb.errors")

    message_parts = []
    if workflow_id:
        message_parts.append(f"Workflow: {workflow_id}")
    if context:
        message_parts.append(f"Context: {context}")

    context_str = " - ".join(message_parts)

    logger.error(f"Error occurred{f' - {context_str}' if context_str else ''}: {error}")


def is_logging_initialized() -> bool:
    """
    Check if logging has been initialized.

    Returns:
        True if logging has been initialized, False otherwise
    """
    return _logging_initialized


# Convenience function for quick debugging
def debug_log(message: str, **kwargs) -> None:
    """
    Quick debug logging with additional context.

    Args:
        message: Debug message
        **kwargs: Additional context as key-value pairs
    """
    logger = get_logger("vpsweb.debug")
    if kwargs:
        context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.debug(f"{message} [{context_str}]")
    else:
        logger.debug(message)
