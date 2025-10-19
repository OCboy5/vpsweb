"""
VPSWeb Repository System - Configuration Management

This module handles configuration loading and validation for the repository system.
Uses Pydantic for type-safe configuration with YAML file support.

Features:
- YAML-based configuration with environment variable substitution
- Pydantic model validation
- Environment-specific configuration support
- Type-safe configuration access
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import asyncio
from datetime import datetime
from enum import Enum

import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class TaskPriority(str, Enum):
    """Task priority levels for queue management."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class WorkflowMode(str, Enum):
    """VPSWeb workflow modes."""
    REASONING = "reasoning"
    NON_REASONING = "non_reasoning"
    HYBRID = "hybrid"


class RepositoryConfig(BaseModel):
    """Repository-specific configuration."""

    database_url: str = Field(
        default="sqlite+aiosqlite:///./repository_root/repo.db",
        description="SQLite database URL with aiosqlite driver"
    )
    repo_root: str = Field(
        default="./repository_root",
        description="Root directory for repository files"
    )
    auto_create_dirs: bool = Field(
        default=True,
        description="Automatically create repository directories"
    )
    enable_wal_mode: bool = Field(
        default=True,
        description="Enable SQLite WAL mode for better performance"
    )

    @validator("repo_root")
    def validate_repo_root(cls, v: str) -> str:
        """Ensure repo_root is a valid path."""
        path = Path(v).resolve()
        return str(path)


class SecurityConfig(BaseModel):
    """Security configuration (localhost-only for v0.3)."""

    require_auth: bool = Field(
        default=False,
        description="Whether authentication is required (v0.3: false)"
    )
    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds (v0.4+)"
    )
    api_key_required: bool = Field(
        default=False,
        description="Whether API key is required (v0.4+)"
    )


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(
        default="127.0.0.1",
        description="Server host (localhost-only for v0.3)"
    )
    port: int = Field(
        default=8000,
        description="Server port"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload for development"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes (SQLite: 1)"
    )

    @validator("port")
    def validate_port(cls, v: int) -> int:
        """Ensure port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class DataConfig(BaseModel):
    """Data management configuration."""

    default_language: str = Field(
        default="en",
        description="Default language code"
    )
    supported_languages: List[str] = Field(
        default=["en", "zh-Hans", "zh-Hant"],
        description="Supported language codes"
    )
    default_license: str = Field(
        default="CC-BY-4.0",
        description="Default license for translations"
    )
    max_poem_length: int = Field(
        default=10000,
        description="Maximum allowed poem length in characters"
    )
    max_translation_length: int = Field(
        default=20000,
        description="Maximum allowed translation length in characters"
    )
    enable_validation: bool = Field(
        default=True,
        description="Enable data validation"
    )

    @validator("max_poem_length", "max_translation_length")
    def validate_max_length(cls, v: int) -> int:
        """Ensure maximum length is reasonable."""
        if v <= 0:
            raise ValueError("Maximum length must be positive")
        if v > 1000000:  # 1MB
            raise ValueError("Maximum length too large")
        return v


class BackgroundTasksConfig(BaseModel):
    """Comprehensive background task configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable background task processing"
    )
    max_concurrent_jobs: int = Field(
        default=3,
        description="Maximum concurrent background jobs"
    )
    job_timeout: int = Field(
        default=300,
        description="Default job timeout in seconds"
    )
    cleanup_interval: int = Field(
        default=3600,
        description="Cleanup interval in seconds"
    )

    # Enhanced task management settings
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum retry attempts for failed jobs"
    )
    retry_delay: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Base retry delay in seconds"
    )
    max_queue_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum task queue size"
    )
    queue_check_interval: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Queue processing interval in seconds"
    )
    task_retention_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Task retention period in hours"
    )

    # Task-specific timeouts
    task_timeouts: Dict[str, int] = Field(
        default_factory=lambda: {
            "translation": 600,
            "maintenance": 300,
            "cleanup": 120,
            "backup": 1800
        },
        description="Task-specific timeouts in seconds"
    )

    # Resource limits
    max_memory_mb: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Maximum memory usage per task in MB"
    )
    max_cpu_percent: float = Field(
        default=80.0,
        ge=10.0,
        le=100.0,
        description="Maximum CPU usage per task"
    )

    # Queue management settings
    enable_priority_queue: bool = Field(
        default=True,
        description="Enable priority-based task queuing"
    )
    pause_on_overload: bool = Field(
        default=True,
        description="Pause queue processing when system is overloaded"
    )
    overload_threshold: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        description="System overload threshold (0.5-1.0)"
    )

    @validator("max_concurrent_jobs")
    def validate_max_concurrent_jobs(cls, v: int) -> int:
        """Ensure concurrent jobs is reasonable."""
        if v <= 0:
            raise ValueError("Max concurrent jobs must be positive")
        if v > 10:
            raise ValueError("Max concurrent jobs too large for localhost")
        return v

    @validator("task_timeouts")
    def validate_task_timeouts(cls, v: Dict[str, int]) -> Dict[str, int]:
        """Validate task timeout values."""
        for task, timeout in v.items():
            if timeout < 30 or timeout > 3600:
                raise ValueError(f"Task timeout for {task} must be between 30 and 3600 seconds")
        return v

    @validator("overload_threshold")
    def validate_overload_threshold(cls, v: float) -> float:
        """Validate overload threshold."""
        if not 0.5 <= v <= 1.0:
            raise ValueError("Overload threshold must be between 0.5 and 1.0")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="json",
        description="Log format: 'json' or 'text'"
    )
    file_path: Optional[str] = Field(
        default="./repository_root/logs/repository.log",
        description="Log file path"
    )
    max_file_size: str = Field(
        default="10MB",
        description="Maximum log file size"
    )
    backup_count: int = Field(
        default=5,
        description="Number of log backup files"
    )

    @validator("level")
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class VPSWebIntegrationConfig(BaseModel):
    """VPSWeb integration configuration."""

    config_path: str = Field(
        default="config",
        description="Path to vpsweb configuration directory"
    )
    workflow_mode: str = Field(
        default="hybrid",
        description="Default vpsweb workflow mode"
    )
    timeout: int = Field(
        default=300,
        description="Timeout for vpsweb operations in seconds"
    )

    @validator("workflow_mode")
    def validate_workflow_mode(cls, v: str) -> str:
        """Ensure workflow mode is valid."""
        valid_modes = ["reasoning", "non_reasoning", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"Workflow mode must be one of: {valid_modes}")
        return v


class WebUIConfig(BaseModel):
    """Web UI configuration."""

    title: str = Field(
        default="VPSWeb Repository",
        description="Web UI title"
    )
    description: str = Field(
        default="Central repository for poetry translations",
        description="Web UI description"
    )
    theme: str = Field(
        default="default",
        description="UI theme (v0.3: default only)"
    )
    items_per_page: int = Field(
        default=20,
        description="Items per page for listings"
    )
    enable_search: bool = Field(
        default=True,
        description="Enable search functionality"
    )
    enable_comparison: bool = Field(
        default=True,
        description="Enable translation comparison view"
    )

    @validator("items_per_page")
    def validate_items_per_page(cls, v: int) -> int:
        """Ensure items per page is reasonable."""
        if v <= 0:
            raise ValueError("Items per page must be positive")
        if v > 100:
            raise ValueError("Items per page too large")
        return v


class PerformanceConfig(BaseModel):
    """Performance optimization configuration."""

    database_pool_size: int = Field(
        default=1,
        description="Database connection pool size (SQLite: 1)"
    )
    query_timeout: int = Field(
        default=30,
        description="Query timeout in seconds"
    )
    enable_query_cache: bool = Field(
        default=True,
        description="Enable query result caching"
    )
    cache_size: int = Field(
        default=1000,
        description="Cache size for query results"
    )

    # Performance monitoring
    enable_metrics: bool = Field(
        default=True,
        description="Enable performance metrics collection"
    )
    metrics_retention_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Metrics retention period in days"
    )

    # Memory management
    gc_threshold: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Garbage collection threshold"
    )
    max_memory_usage: int = Field(
        default=1024,
        ge=256,
        le=4096,
        description="Maximum memory usage in MB"
    )


class TaskMonitoringConfig(BaseModel):
    """Task monitoring and health check configuration."""

    enable_health_checks: bool = Field(
        default=True,
        description="Enable task system health checks"
    )
    health_check_interval: int = Field(
        default=60,
        ge=10,
        le=600,
        description="Health check interval in seconds"
    )
    enable_task_metrics: bool = Field(
        default=True,
        description="Enable detailed task metrics collection"
    )
    metrics_history_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Number of metrics data points to retain"
    )

    # Alert thresholds
    failed_task_threshold: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Alert threshold for consecutive failed tasks"
    )
    queue_size_warning: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Warning threshold for queue size"
    )
    memory_usage_warning: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Memory usage warning threshold (0.5-0.95)"
    )

    # Task lifecycle monitoring
    track_task_lifecycle: bool = Field(
        default=True,
        description="Track complete task lifecycle events"
    )
    enable_task_tracing: bool = Field(
        default=False,
        description="Enable detailed task execution tracing"
    )

    @validator("memory_usage_warning")
    def validate_memory_warning(cls, v: float) -> float:
        """Validate memory warning threshold."""
        if not 0.5 <= v <= 0.95:
            raise ValueError("Memory usage warning must be between 0.5 and 0.95")
        return v


class SystemResourceConfig(BaseModel):
    """System resource management configuration."""

    enable_resource_monitoring: bool = Field(
        default=True,
        description="Enable system resource monitoring"
    )
    resource_check_interval: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Resource monitoring interval in seconds"
    )

    # CPU thresholds
    max_cpu_usage: float = Field(
        default=80.0,
        ge=50.0,
        le=100.0,
        description="Maximum CPU usage percentage"
    )
    cpu_warning_threshold: float = Field(
        default=70.0,
        ge=40.0,
        le=90.0,
        description="CPU usage warning threshold"
    )

    # Memory thresholds
    max_memory_usage_percent: float = Field(
        default=85.0,
        ge=60.0,
        le=95.0,
        description="Maximum memory usage percentage"
    )
    memory_warning_threshold: float = Field(
        default=75.0,
        ge=50.0,
        le=90.0,
        description="Memory usage warning threshold"
    )

    # Disk thresholds
    max_disk_usage_percent: float = Field(
        default=90.0,
        ge=70.0,
        le=95.0,
        description="Maximum disk usage percentage"
    )
    disk_warning_threshold: float = Field(
        default=80.0,
        ge=60.0,
        le=90.0,
        description="Disk usage warning threshold"
    )

    @validator("max_cpu_usage", "cpu_warning_threshold")
    def validate_cpu_thresholds(cls, v: float) -> float:
        """Validate CPU threshold values."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("CPU thresholds must be between 0 and 100")
        return v

    @validator("max_memory_usage_percent", "memory_warning_threshold")
    def validate_memory_thresholds(cls, v: float) -> float:
        """Validate memory threshold values."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("Memory thresholds must be between 0 and 100")
        return v

    @validator("max_disk_usage_percent", "disk_warning_threshold")
    def validate_disk_thresholds(cls, v: float) -> float:
        """Validate disk threshold values."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("Disk thresholds must be between 0 and 100")
        return v


class RepositorySystemConfig(BaseModel):
    """Main configuration class for the repository system."""

    repository: RepositoryConfig = Field(default_factory=RepositoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    background_tasks: BackgroundTasksConfig = Field(default_factory=BackgroundTasksConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    integration: VPSWebIntegrationConfig = Field(default_factory=VPSWebIntegrationConfig)
    web_ui: WebUIConfig = Field(default_factory=WebUIConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    task_monitoring: TaskMonitoringConfig = Field(default_factory=TaskMonitoringConfig)
    system_resources: SystemResourceConfig = Field(default_factory=SystemResourceConfig)

    @validator("server")
    def validate_localhost_only(cls, v: ServerConfig) -> ServerConfig:
        """Ensure server configuration is localhost-only for v0.3."""
        if v.host not in ["127.0.0.1", "localhost", "::1"]:
            raise ValueError("v0.3 only supports localhost deployment")
        return v

    @classmethod
    def load_from_file(cls, config_path: str | Path) -> RepositorySystemConfig:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            RepositorySystemConfig: Loaded configuration
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Substitute environment variables
        config_data = cls._substitute_env_vars(config_data)

        return cls(**config_data)

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.

        Args:
            data: Configuration data to process

        Returns:
            Processed configuration data
        """
        if isinstance(data, dict):
            return {key: RepositorySystemConfig._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [RepositorySystemConfig._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and "${" in data:
            return RepositorySystemConfig._substitute_single_env_var(data)
        else:
            return data

    @staticmethod
    def _substitute_single_env_var(text: str) -> str:
        """
        Substitute a single environment variable in text.

        Args:
            text: Text containing environment variable placeholder

        Returns:
            Text with substituted value
        """
        import re

        def replace_var(match: re.Match) -> str:
            var_expr = match.group(1)
            if ":" in var_expr:
                var_name, default_value = var_expr.split(":", 1)
                return os.getenv(var_name, default_value)
            else:
                var_name = var_expr
                return os.getenv(var_name, "")

        # Replace ${VAR} or ${VAR:default} patterns
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, text)


class ConfigSettings(BaseSettings):
    """Settings class for environment variable override support."""

    # Override with environment variables if needed
    repo_database_url: Optional[str] = None
    repo_host: Optional[str] = None
    repo_port: Optional[int] = None
    repo_debug: Optional[bool] = None

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_config(
    config_path: Optional[str] = None,
    config_dir: Optional[str] = None
) -> RepositorySystemConfig:
    """
    Load repository system configuration.

    Args:
        config_path: Direct path to config file (overrides config_dir)
        config_dir: Directory containing config files

    Returns:
        RepositorySystemConfig: Loaded configuration
    """
    # Determine config file path
    if config_path:
        config_file = Path(config_path)
    elif config_dir:
        config_file = Path(config_dir) / "repository.yaml"
    else:
        # Default locations
        default_paths = [
            Path("config/repository.yaml"),
            Path("repository.yaml"),
            Path("config/repo_config.yaml"),
        ]

        config_file = None
        for path in default_paths:
            if path.exists():
                config_file = path
                break

        if config_file is None:
            # Create default config if none exists
            config_file = Path("config/repository.yaml")
            if not config_file.parent.exists():
                config_file.parent.mkdir(parents=True)

            # Create a minimal default config
            default_config = RepositorySystemConfig()
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(default_config.dict(), f, default_flow_style=False, indent=2)

    # Load configuration from file
    config = RepositorySystemConfig.load_from_file(config_file)

    # Override with environment variables if available
    settings = ConfigSettings()

    if settings.repo_database_url:
        config.repository.database_url = settings.repo_database_url
    if settings.repo_host:
        config.server.host = settings.repo_host
    if settings.repo_port:
        config.server.port = settings.repo_port
    if settings.repo_debug is not None:
        config.server.debug = settings.repo_debug

    # Ensure repository directories exist
    repo_root = Path(config.repository.repo_root)
    if config.repository.auto_create_dirs:
        repo_root.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (repo_root / "logs").mkdir(exist_ok=True)
        (repo_root / "backups").mkdir(exist_ok=True)
        (repo_root / "temp").mkdir(exist_ok=True)

    return config


class ConfigManager:
    """
    Configuration manager with hot-reload capability.

    Provides configuration reloading when files change and maintains
    a cache of the current configuration for efficient access.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or Path("config/repository.yaml")
        self._config: Optional[RepositorySystemConfig] = None
        self._last_modified: Optional[float] = None
        self._reload_callbacks: List[Callable[[RepositorySystemConfig], None]] = []
        self._lock = asyncio.Lock()

    async def get_config(self) -> RepositorySystemConfig:
        """
        Get current configuration, reloading if necessary.

        Returns:
            Current configuration
        """
        async with self._lock:
            if self._should_reload():
                await self._reload_config()
            return self._config or load_config(self.config_path)

    def _should_reload(self) -> bool:
        """
        Check if configuration should be reloaded.

        Returns:
            True if file has been modified since last load
        """
        if not self.config_path.exists():
            return False

        current_mtime = self.config_path.stat().st_mtime
        return self._last_modified is None or current_mtime > self._last_modified

    async def _reload_config(self) -> None:
        """
        Reload configuration from file and notify callbacks.
        """
        try:
            new_config = load_config(self.config_path)
            self._config = new_config
            self._last_modified = self.config_path.stat().st_mtime

            # Notify all callbacks
            for callback in self._reload_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(new_config)
                    else:
                        callback(new_config)
                except Exception as e:
                    # Log callback errors but don't fail reload
                    print(f"Error in config reload callback: {e}")

        except Exception as e:
            print(f"Failed to reload configuration: {e}")
            # Keep existing config if reload fails

    def add_reload_callback(self, callback: Callable[[RepositorySystemConfig], None]) -> None:
        """
        Add a callback to be called when configuration is reloaded.

        Args:
            callback: Function to call with new configuration
        """
        self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable[[RepositorySystemConfig], None]) -> None:
        """
        Remove a reload callback.

        Args:
            callback: Function to remove
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    async def start_auto_reload(self, check_interval: float = 1.0) -> None:
        """
        Start automatic configuration reloading in background.

        Args:
            check_interval: How often to check for file changes (seconds)
        """
        async def auto_reload_loop():
            while True:
                try:
                    await self.get_config()  # This will reload if needed
                    await asyncio.sleep(check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error in auto-reload loop: {e}")
                    await asyncio.sleep(check_interval)

        # Create background task
        asyncio.create_task(auto_reload_loop())

    def validate_config_schema(self) -> Dict[str, Any]:
        """
        Validate configuration schema and return validation results.

        Returns:
            Dictionary with validation results
        """
        try:
            config = self._config or load_config(self.config_path)

            # Basic schema validation through Pydantic
            schema = config.model_json_schema()

            # Validate required sections
            required_sections = [
                'repository', 'security', 'server', 'data',
                'background_tasks', 'logging', 'integration',
                'web_ui', 'performance', 'task_monitoring', 'system_resources'
            ]

            validation_results = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'sections': {}
            }

            for section in required_sections:
                section_data = getattr(config, section, None)
                if section_data is None:
                    validation_results['errors'].append(f"Missing required section: {section}")
                    validation_results['valid'] = False
                else:
                    validation_results['sections'][section] = {
                        'present': True,
                        'type': type(section_data).__name__
                    }

            # Additional validation for localhost-only deployment (v0.3)
            if config.server.host not in ["127.0.0.1", "localhost", "::1"]:
                validation_results['warnings'].append(
                    f"Server host {config.server.host} is not localhost - this violates v0.3 requirements"
                )

            if config.security.require_auth:
                validation_results['warnings'].append(
                    "Authentication is enabled but v0.3 is localhost-only"
                )

            # Validate database URL format
            db_url = config.repository.database_url
            if not db_url.startswith(("sqlite+aiosqlite:///", "postgresql://", "mysql://")):
                validation_results['warnings'].append(
                    f"Database URL format may be unsupported: {db_url[:20]}..."
                )

            return validation_results

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Configuration validation failed: {str(e)}"],
                'warnings': [],
                'sections': {}
            }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.

    Returns:
        Global configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


async def get_config_with_reload() -> RepositorySystemConfig:
    """
    Get configuration with automatic reload support.

    Returns:
        Current configuration (reloaded if necessary)
    """
    manager = get_config_manager()
    return await manager.get_config()