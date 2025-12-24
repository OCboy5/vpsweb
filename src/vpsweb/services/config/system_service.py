"""
System Service - Domain-specific system configuration access

This service provides high-level interfaces for accessing system-level
configuration like storage, logging, and monitoring settings.
"""

import logging
from typing import Any, Dict, List, Optional

from ...models.config import LoggingConfig, MonitoringConfig, StorageConfig

logger = logging.getLogger(__name__)


class SystemService:
    """
    Service for accessing system-level configuration.

    Provides clean interfaces for:
    - Storage configuration and paths
    - Logging configuration and setup
    - Monitoring and performance settings
    - Translation strategy settings
    """

    def __init__(
        self,
        storage_config: StorageConfig,
        logging_config: LoggingConfig,
        monitoring_config: Optional[MonitoringConfig] = None,
    ):
        """Initialize with system configuration components."""
        self._storage = storage_config
        self._logging = logging_config
        self._monitoring = monitoring_config

    # Storage configuration
    def get_output_directory(self) -> str:
        """Get the main output directory."""
        return self._storage.output_dir

    def get_output_format(self) -> str:
        """Get the output file format."""
        return self._storage.format

    def should_include_timestamp(self) -> bool:
        """Check if output filenames should include timestamp."""
        return self._storage.include_timestamp

    def should_pretty_print(self) -> bool:
        """Check if JSON output should be pretty-printed."""
        return self._storage.pretty_print

    def should_include_workflow_mode_tag(self) -> bool:
        """Check if output filenames should include workflow mode tag."""
        return self._storage.workflow_mode_tag

    def get_wechat_articles_directory(self) -> str:
        """Get WeChat articles output directory."""
        return getattr(self._storage, "wechat_articles_dir", "outputs/wechat_articles")

    def get_cache_directory(self) -> str:
        """Get cache directory."""
        return getattr(self._storage, "cache_dir", "outputs/.cache")

    def get_storage_config_summary(self) -> Dict[str, Any]:
        """Get complete storage configuration summary."""
        return {
            "output_dir": self._storage.output_dir,
            "format": self._storage.format,
            "include_timestamp": self._storage.include_timestamp,
            "pretty_print": self._storage.pretty_print,
            "workflow_mode_tag": self._storage.workflow_mode_tag,
            "wechat_articles_dir": self.get_wechat_articles_directory(),
            "cache_dir": self.get_cache_directory(),
        }

    # Logging configuration
    def get_logging_level(self) -> str:
        """Get logging level."""
        return self._logging.level.value

    def get_logging_format(self) -> str:
        """Get logging format string."""
        return self._logging.format

    def get_log_file_path(self) -> Optional[str]:
        """Get log file path."""
        return self._logging.file

    def get_max_file_size(self) -> int:
        """Get maximum log file size in bytes."""
        return self._logging.max_file_size

    def get_backup_count(self) -> int:
        """Get number of backup log files to keep."""
        return self._logging.backup_count

    def should_log_reasoning_tokens(self) -> bool:
        """Check if reasoning model token usage should be tracked separately."""
        return self._logging.log_reasoning_tokens

    def get_logging_config_summary(self) -> Dict[str, Any]:
        """Get complete logging configuration summary."""
        return {
            "level": self._logging.level.value,
            "format": self._logging.format,
            "file": self._logging.file,
            "max_file_size": self._logging.max_file_size,
            "backup_count": self._logging.backup_count,
            "log_reasoning_tokens": self._logging.log_reasoning_tokens,
        }

    # Monitoring configuration
    def should_track_latency(self) -> bool:
        """Check if request latency should be tracked."""
        return self._monitoring.track_latency if self._monitoring else False

    def should_track_token_usage(self) -> bool:
        """Check if token usage should be tracked."""
        return self._monitoring.track_token_usage if self._monitoring else False

    def should_track_cost(self) -> bool:
        """Check if API costs should be estimated."""
        return self._monitoring.track_cost if self._monitoring else False

    def should_compare_workflows(self) -> bool:
        """Check if A/B workflow comparison is enabled."""
        return self._monitoring.compare_workflows if self._monitoring else False

    def get_monitoring_config_summary(self) -> Dict[str, Any]:
        """Get complete monitoring configuration summary."""
        if not self._monitoring:
            return {"enabled": False}

        return {
            "enabled": True,
            "track_latency": self._monitoring.track_latency,
            "track_token_usage": self._monitoring.track_token_usage,
            "track_cost": self._monitoring.track_cost,
            "compare_workflows": self._monitoring.compare_workflows,
        }

    # Translation strategy settings (accessed via MainConfig)
    def get_translation_strategy(self, main_config) -> Dict[str, Any]:
        """
        Get translation strategy configuration.

        Args:
            main_config: MainConfig object containing translation_strategy

        Returns:
            Dictionary with translation strategy settings
        """
        if hasattr(main_config, "translation_strategy"):
            strategy = main_config.translation_strategy
            return {
                "adaptation_level": getattr(strategy, "adaptation_level", "balanced"),
                "repetition_policy": getattr(strategy, "repetition_policy", "strict"),
                "additions_policy": getattr(strategy, "additions_policy", "forbid"),
                "prosody_target": getattr(strategy, "prosody_target", "free verse, cadence-aware"),
                "few_shots": getattr(strategy, "few_shots", ""),
            }
        return {}

    # System configuration access
    def get_system_preview_lengths(self, main_config) -> Dict[str, int]:
        """
        Get system preview length settings.

        Args:
            main_config: MainConfig object containing system settings

        Returns:
            Dictionary with preview length settings
        """
        if hasattr(main_config, "system") and hasattr(main_config.system, "preview_lengths"):
            return main_config.system.preview_lengths
        return {
            "input_preview": 100,
            "response_preview": 200,
            "editor_preview": 200,
        }

    def get_system_defaults(self, main_config) -> Dict[str, Any]:
        """
        Get system default settings.

        Args:
            main_config: MainConfig object containing system settings

        Returns:
            Dictionary with system default settings
        """
        if hasattr(main_config, "system"):
            system_config = main_config.system
            return {
                "default_digest": getattr(
                    system_config,
                    "default_digest",
                    "诗歌翻译作品，展现中英文学之美，传递文化精髓。",
                ),
                "token_refresh_buffer": getattr(system_config, "token_refresh_buffer", 300),
                "default_token_expiry": getattr(system_config, "default_token_expiry", 7200),
            }
        return {}

    # Validation and utility methods
    def validate_system_config(self) -> List[str]:
        """Validate system configuration and return any errors."""
        errors = []

        # Validate storage configuration
        if not self._storage.output_dir:
            errors.append("Storage output directory not configured")

        # Validate logging configuration
        if self._logging.max_file_size <= 0:
            errors.append("Logging max_file_size must be positive")

        if self._logging.backup_count < 0:
            errors.append("Logging backup_count cannot be negative")

        return errors

    def get_complete_system_summary(self, main_config) -> Dict[str, Any]:
        """Get complete system configuration summary."""
        return {
            "storage": self.get_storage_config_summary(),
            "logging": self.get_logging_config_summary(),
            "monitoring": self.get_monitoring_config_summary(),
            "translation_strategy": self.get_translation_strategy(main_config),
            "preview_lengths": self.get_system_preview_lengths(main_config),
            "system_defaults": self.get_system_defaults(main_config),
        }
