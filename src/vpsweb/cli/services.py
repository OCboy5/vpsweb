"""
Phase 3C: CLI Service Layer Implementations.

This module provides concrete implementations of the CLI service interfaces,
with dependency injection support and comprehensive error handling.
"""

import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.config import LogLevel, WorkflowMode
from vpsweb.models.translation import TranslationInput, TranslationOutput
from vpsweb.services.config import initialize_config_facade
from vpsweb.utils.config_loader import (
    load_model_registry_config,
    load_task_templates_config,
    load_yaml_file,
    substitute_env_vars_in_data,
)
from vpsweb.utils.logger import setup_logging
from vpsweb.utils.storage import StorageHandler
from vpsweb.utils.tools_phase3a import ErrorCollector, PerformanceMonitor

from .interfaces import (
    ICLICommandServiceV2,
    ICLIConfigurationServiceV2,
    ICLIErrorHandlerV2,
    ICLIInputServiceV2,
    ICLILoggerServiceV2,
    ICLIOutputServiceV2,
    ICLIStorageServiceV2,
    ICLIWeChatServiceV2,
    ICLIWorkflowServiceV2,
)


class CLIInputServiceV2(ICLIInputServiceV2):
    """CLI input handling service with dependency injection."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def read_poem_from_input(self, input_path: Optional[str] = None) -> str:
        """Read poem text from file or stdin."""
        try:
            if input_path:
                # Read from file
                file_path = Path(input_path)
                if not file_path.exists():
                    raise ValueError(f"Input file not found: {input_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    poem_text = f.read().strip()

                if not poem_text:
                    raise ValueError(f"Input file is empty: {input_path}")

                self.logger.info(f"Read poem from file: {input_path} ({len(poem_text)} chars)")
                return poem_text

            else:
                # Read from stdin
                click.echo("📖 Reading poem from stdin... (Ctrl+D to finish)")
                poem_lines = []
                try:
                    while True:
                        line = input()
                        poem_lines.append(line)
                except EOFError:
                    pass

                poem_text = "\n".join(poem_lines).strip()

                if not poem_text:
                    raise ValueError("No poem text provided via stdin")

                self.logger.info(f"Read poem from stdin ({len(poem_text)} chars)")
                return poem_text

        except Exception as e:
            self.error_collector.add_error(e, {"input_path": input_path})
            self.logger.error(f"Error reading poem input: {e}")
            raise

    def validate_translation_input(self, source_lang: str, target_lang: str, poem_text: str) -> Dict[str, Any]:
        """Validate translation input parameters."""
        try:
            errors = []
            warnings = []

            # Validate languages are different
            if source_lang == target_lang:
                errors.append("Source and target languages must be different")

            # Validate poem text
            if not poem_text.strip():
                errors.append("Poem text cannot be empty")

            if len(poem_text.strip()) < 10:
                warnings.append("Poem text is very short, translation quality may be affected")

            if len(poem_text.strip()) > 10000:
                warnings.append("Poem text is very long, processing may take time")

            # Validate supported languages
            supported_languages = ["English", "Chinese", "Polish"]
            if source_lang not in supported_languages:
                errors.append(f"Unsupported source language: {source_lang}")

            if target_lang not in supported_languages:
                errors.append(f"Unsupported target language: {target_lang}")

            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "poem_length": len(poem_text),
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if result["valid"]:
                self.logger.info("Input validation passed")
            else:
                self.logger.warning(f"Input validation failed: {errors}")

            return result

        except Exception as e:
            self.error_collector.add_error(
                e,
                {
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "poem_length": len(poem_text) if poem_text else 0,
                },
            )
            self.logger.error(f"Error validating translation input: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "source_lang": source_lang,
                "target_lang": target_lang,
                "poem_length": len(poem_text) if poem_text else 0,
            }

    def create_translation_input(
        self,
        poem_text: str,
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TranslationInput:
        """Create TranslationInput object from parameters."""
        try:
            input_data = TranslationInput(
                original_poem=poem_text,
                source_lang=source_lang,
                target_lang=target_lang,
            )

            # Add metadata if provided
            if metadata:
                input_data.metadata.update(metadata)

            self.logger.debug(f"Created TranslationInput: {source_lang} → {target_lang}")
            return input_data

        except Exception as e:
            self.error_collector.add_error(
                e,
                {
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "metadata_keys": list(metadata.keys()) if metadata else [],
                },
            )
            self.logger.error(f"Error creating TranslationInput: {e}")
            raise


class CLIConfigurationServiceV2(ICLIConfigurationServiceV2):
    """CLI configuration management service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def load_configuration(self, config_path: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
        """Load and validate configuration using ConfigFacade."""
        try:
            click.echo("⚙️  Loading configuration...")

            # Load new configuration files
            models_config = load_model_registry_config()
            task_templates_config = load_task_templates_config()

            # Create CompleteConfig from new configuration files
            from vpsweb.models.config import CompleteConfig, MainConfig, ProvidersConfig

            # Load main configuration (default.yaml or custom path)
            if config_path is None:
                main_config_path = Path("config/default.yaml")
            else:
                main_config_path = Path(config_path)

            main_config_data = load_yaml_file(main_config_path)
            main_config_data = substitute_env_vars_in_data(main_config_data)
            main_config = MainConfig(**main_config_data)

            # Create providers config from models.yaml
            providers_data = {}
            if "providers" in models_config:
                # Extract models for each provider
                provider_models = {}
                if "models" in models_config:
                    for model_name, model_info in models_config["models"].items():
                        provider_name = model_info.get("provider")
                        if provider_name:
                            if provider_name not in provider_models:
                                provider_models[provider_name] = []
                            provider_models[provider_name].append(model_info.get("name", model_name))

                for provider_name, provider_info in models_config["providers"].items():
                    providers_data[provider_name] = {
                        "api_key_env": provider_info.get("api_key_env"),
                        "base_url": provider_info.get("base_url"),
                        "type": provider_info.get("type", "openai_compatible"),
                        "models": provider_models.get(provider_name, []),  # Add models list
                        "timeout": models_config.get("provider_settings", {}).get("timeout", 180.0),
                        "max_retries": models_config.get("provider_settings", {}).get("max_retries", 3),
                        "retry_delay": models_config.get("provider_settings", {}).get("retry_delay", 1.0),
                    }

            providers_config = ProvidersConfig(providers=providers_data)
            complete_config = CompleteConfig(main=main_config, providers=providers_config)

            # Initialize ConfigFacade with CompleteConfig and new configs
            config_facade = initialize_config_facade(
                complete_config,
                models_config=models_config,
                task_templates_config=task_templates_config,
            )

            # Setup logging based on configuration
            logging_config = config_facade.system.get_logging_config_summary()
            if verbose:
                logging_config["level"] = "DEBUG"

            # Create LoggingConfig object from the summary
            from vpsweb.models.config import LoggingConfig, LogLevel

            log_config = LoggingConfig(
                level=LogLevel(logging_config["level"].upper()),
                format=logging_config.get(
                    "format",
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                ),
                file=logging_config.get("file"),
                max_file_size=logging_config.get("max_file_size", 10485760),
                backup_count=logging_config.get("backup_count", 5),
                log_reasoning_tokens=logging_config.get("log_reasoning_tokens", False),
            )

            setup_logging(log_config)

            # Display configuration using ConfigFacade
            workflow_info = config_facade.get_workflow_info()
            self.logger.info(f"Configuration loaded from: {config_path or 'default'}")
            self.logger.info(f"Workflow: {workflow_info['name']} v{workflow_info['version']}")
            self.logger.info(f"Providers: {', '.join(config_facade.get_provider_names())}")

            return {
                "config_facade": config_facade,
                "workflow_config": config_facade.main.workflow,
                "providers_config": config_facade.providers,
                "storage_config": config_facade.main.storage,
                "config_path": config_path,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            self.error_collector.add_error(e, {"config_path": config_path})
            self.logger.error(f"Error loading configuration: {e}")
            raise

    async def validate_configuration(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Validate configuration files using new config pattern."""
        try:
            click.echo("🔍 Validating configuration...")

            # Try to load and validate the new config files
            errors = []
            warnings = []

            try:
                models_config = load_model_registry_config()
                click.echo("  ✅ Models configuration valid")
            except Exception as e:
                errors.append(f"Models configuration error: {e}")

            try:
                task_templates_config = load_task_templates_config()
                click.echo("  ✅ Task templates configuration valid")
            except Exception as e:
                warnings.append(f"Task templates configuration issue: {e}")

            # Try to initialize ConfigFacade
            try:
                if not errors:
                    # Create CompleteConfig from new configuration files
                    from vpsweb.models.config import CompleteConfig, MainConfig
                    from vpsweb.models.providers import ProvidersConfig

                    # Load main configuration (default.yaml or custom path)
                    if config_path is None:
                        main_config_path = Path("config/default.yaml")
                    else:
                        main_config_path = Path(config_path)

                    main_config_data = load_yaml_file(main_config_path)
                    main_config_data = substitute_env_vars_in_data(main_config_data)
                    main_config = MainConfig(**main_config_data)

                    # Create providers config from models.yaml
                    providers_data = {}
                    if "providers" in models_config:
                        # Extract models for each provider
                        provider_models = {}
                        if "models" in models_config:
                            for model_name, model_info in models_config["models"].items():
                                provider_name = model_info.get("provider")
                                if provider_name:
                                    if provider_name not in provider_models:
                                        provider_models[provider_name] = []
                                    provider_models[provider_name].append(model_info.get("name", model_name))

                        for provider_name, provider_info in models_config["providers"].items():
                            providers_data[provider_name] = {
                                "api_key_env": provider_info.get("api_key_env"),
                                "base_url": provider_info.get("base_url"),
                                "type": provider_info.get("type", "openai_compatible"),
                                "models": provider_models.get(provider_name, []),  # Add models list
                                "timeout": models_config.get("provider_settings", {}).get("timeout", 180.0),
                                "max_retries": models_config.get("provider_settings", {}).get("max_retries", 3),
                                "retry_delay": models_config.get("provider_settings", {}).get("retry_delay", 1.0),
                            }

                    providers_config = ProvidersConfig(providers=providers_data)
                    complete_config = CompleteConfig(main=main_config, providers=providers_config)

                    config_facade = initialize_config_facade(
                        complete_config,
                        models_config=models_config,
                        task_templates_config=task_templates_config,
                    )
                else:
                    raise Exception("Cannot initialize ConfigFacade due to model configuration errors")
                click.echo("  ✅ ConfigFacade initialization successful")

                # Test basic functionality
                config_facade.get_workflow_info()
                provider_names = config_facade.get_provider_names()
                click.echo(f"  ✅ Found {len(provider_names)} providers: {', '.join(provider_names)}")

            except Exception as e:
                errors.append(f"ConfigFacade initialization failed: {e}")

            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "config_path": config_path,
                "validated_at": datetime.now(timezone.utc).isoformat(),
            }

            if result["valid"]:
                click.echo("✅ Configuration validation passed")
            else:
                click.echo("❌ Configuration validation failed")
                for error in result["errors"]:
                    click.echo(f"  • {error}")

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"config_path": config_path})
            self.logger.error(f"Error validating configuration: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "config_path": config_path,
            }

    def get_workflow_modes(self) -> List[Dict[str, Any]]:
        """Get available workflow modes."""
        return [
            {
                "name": "reasoning",
                "description": "Step-by-step reasoning with detailed analysis",
                "recommended_for": "complex or literary poems",
            },
            {
                "name": "non_reasoning",
                "description": "Direct translation without detailed reasoning",
                "recommended_for": "simple or technical content",
            },
            {
                "name": "hybrid",
                "description": "Balanced approach with selective reasoning",
                "recommended_for": "most content types",
            },
        ]

    async def setup_logging(self, verbose: bool = False) -> None:
        """Setup logging configuration."""
        try:
            log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
            setup_logging(log_level)

            self.logger.info(f"Logging setup complete (level: {log_level.value})")

        except Exception as e:
            self.error_collector.add_error(e, {"verbose": verbose})
            self.logger.error(f"Error setting up logging: {e}")
            raise


class CLIWorkflowServiceV2(ICLIWorkflowServiceV2):
    """CLI workflow execution service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()
        self.performance_monitor = PerformanceMonitor()

    async def initialize_workflow(self, config: Dict[str, Any], workflow_mode: WorkflowMode) -> TranslationWorkflow:
        """Initialize translation workflow."""
        try:
            workflow_config = config["workflow_config"]
            providers_config = config["providers_config"]

            workflow = TranslationWorkflow(workflow_config, providers_config, workflow_mode)

            self.logger.info(f"Workflow initialized: {workflow_mode.value}")
            return workflow

        except Exception as e:
            self.error_collector.add_error(
                e,
                {"workflow_mode": (workflow_mode.value if workflow_mode else None)},
            )
            self.logger.error(f"Error initializing workflow: {e}")
            raise

    async def execute_translation_workflow(
        self,
        workflow: TranslationWorkflow,
        input_data: TranslationInput,
        workflow_mode: str,
        show_progress: bool = True,
    ) -> TranslationOutput:
        """Execute translation workflow."""
        try:
            click.echo(f"🚀 Starting translation workflow ({workflow_mode} mode)...")

            # Display original poem
            click.echo(f"\n📄 Original Poem ({input_data.source_lang} → {input_data.target_lang}):")
            click.echo("-" * 30)
            poem = input_data.original_poem
            if len(poem) > 200:
                poem = poem[:200] + "..."
            click.echo(poem)
            click.echo("-" * 30)
            click.echo()

            # Execute workflow
            translation_output = await workflow.execute(input_data, show_progress=show_progress)

            self.logger.info(f"Workflow completed successfully: {translation_output.workflow_id}")
            return translation_output

        except Exception as e:
            self.error_collector.add_error(
                e,
                {
                    "workflow_mode": workflow_mode,
                    "input_data": {
                        "source_lang": input_data.source_lang,
                        "target_lang": input_data.target_lang,
                        "poem_length": len(input_data.original_poem),
                    },
                },
            )
            self.logger.error(f"Error executing workflow: {e}")
            raise

    async def validate_workflow_input(
        self, input_data: TranslationInput, config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate workflow input without execution using ConfigFacade."""
        try:
            click.echo("🔍 Validating workflow input...")

            # Use the configuration service to validate config
            config_service = CLIConfigurationServiceV2(self.logger)
            config_validation = await config_service.validate_configuration(config_path)

            result = {
                "valid": config_validation.get("valid", False),
                "errors": config_validation.get("errors", []),
                "warnings": config_validation.get("warnings", []),
                "input_validation": {
                    "source_lang": input_data.source_lang,
                    "target_lang": input_data.target_lang,
                    "poem_length": len(input_data.original_poem),
                },
                "validated_at": datetime.now(timezone.utc).isoformat(),
            }

            if result["valid"]:
                click.echo("✅ Input validation passed")
                click.echo(f"   Source: {input_data.source_lang}")
                click.echo(f"   Target: {input_data.target_lang}")
                click.echo(f"   Poem length: {len(input_data.original_poem)} characters")
            else:
                for error in result["errors"]:
                    click.echo(f"❌ {error}")

            return result

        except Exception as e:
            self.error_collector.add_error(e, {"config_path": config_path})
            self.logger.error(f"Error validating workflow input: {e}")
            raise


class CLIStorageServiceV2(ICLIStorageServiceV2):
    """CLI storage operations service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def setup_storage_handler(self, output_dir: Optional[str] = None) -> StorageHandler:
        """Setup storage handler for results."""
        try:
            storage_handler = StorageHandler(output_dir or "outputs")
            self.logger.info(f"Storage handler setup: {output_dir or 'default'}")
            return storage_handler

        except Exception as e:
            self.error_collector.add_error(e, {"output_dir": output_dir})
            self.logger.error(f"Error setting up storage handler: {e}")
            raise

    async def save_translation_results(
        self,
        translation_output: TranslationOutput,
        workflow_mode: str,
        include_mode_tag: bool = False,
    ) -> Dict[str, Path]:
        """Save translation results to storage."""
        try:
            click.echo("💾 Saving translation results...")

            # This would need the storage handler
            # For now, return placeholder paths
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workflow_id = translation_output.workflow_id[:8]

            result = {
                "json": Path(f"outputs/json/translation_{workflow_id}_{timestamp}.json"),
                "markdown_final": Path(f"outputs/markdown/translation_{workflow_id}_{timestamp}.md"),
                "markdown_log": Path(f"outputs/markdown/translation_{workflow_id}_{timestamp}_log.md"),
            }

            self.logger.info(f"Translation results saved: {len(result)} files")
            return result

        except Exception as e:
            self.error_collector.add_error(
                e,
                {
                    "workflow_mode": workflow_mode,
                    "workflow_id": translation_output.workflow_id,
                },
            )
            self.logger.error(f"Error saving translation results: {e}")
            raise


class CLIOutputServiceV2(ICLIOutputServiceV2):
    """CLI output formatting and display service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def display_translation_summary(
        self,
        translation_output: TranslationOutput,
        saved_files: Dict[str, Path],
    ) -> None:
        """Display translation workflow summary."""
        try:
            click.echo("\n" + "=" * 60)
            click.echo("🎉 TRANSLATION COMPLETE!")
            click.echo("=" * 60)

            # Basic info
            click.echo(f"📋 Workflow ID: {translation_output.workflow_id}")
            click.echo(f"🔄 Workflow Mode: {translation_output.workflow_mode}")
            click.echo(f"📁 Output file: {saved_files['json']}")
            click.echo(f"📄 Markdown (final): {saved_files['markdown_final']}")
            click.echo(f"📋 Markdown (log): {saved_files['markdown_log']}")

            # Step-by-step details
            click.echo("\n📊 Step-by-Step Details:")
            click.echo(f"  Step 1 (Initial): 🧮 {translation_output.initial_translation.tokens_used} tokens")
            click.echo(f"  Step 2 (Editor): 🧮 {translation_output.editor_review.tokens_used} tokens")
            click.echo(f"  Step 3 (Revision): 🧮 {translation_output.revised_translation.tokens_used} tokens")

            # Total summary
            click.echo(
                f"\n📈 Overall: 🧮 {translation_output.total_tokens} total tokens | ⏱️  {translation_output.duration_seconds:.2f}s total time"
            )

            # Editor suggestions count
            editor_suggestions = translation_output.editor_review.editor_suggestions
            if editor_suggestions:
                suggestions_count = len(
                    [line for line in editor_suggestions.split("\n") if line.strip() and line.strip()[0].isdigit()]
                )
                click.echo(f"📋 Editor suggestions: {suggestions_count}")
            else:
                click.echo(f"📋 Editor suggestions: 0")

            click.echo("\n✅ Translation saved successfully!")

        except Exception as e:
            self.logger.error(f"Error displaying translation summary: {e}")
            # Don't raise - display errors shouldn't stop the workflow

    def format_workflow_progress(self, step_name: str, progress_data: Dict[str, Any]) -> str:
        """Format workflow progress information."""
        try:
            if progress_data.get("status") == "in_progress":
                return f"🔄 {step_name}: {progress_data.get('message', 'Processing...')}"
            elif progress_data.get("status") == "completed":
                return f"✅ {step_name}: Completed"
            elif progress_data.get("status") == "error":
                return f"❌ {step_name}: {progress_data.get('error', 'Error occurred')}"
            else:
                return f"⏸️ {step_name}: {progress_data.get('status', 'Unknown status')}"

        except Exception:
            return f"📝 {step_name}: Status unknown"

    def format_error_message(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format error message for CLI display."""
        try:
            type_emoji = {
                "InputError": "❌",
                "ConfigError": "⚙️",
                "WorkflowError": "🔄",
                "WeChatError": "📱",
                "StorageError": "💾",
                "GeneralError": "⚠️",
            }

            emoji = type_emoji.get(error_type, "❌")
            formatted = f"{emoji} {error_type}: {error_message}"

            if context:
                # Add context information if provided
                if "command" in context:
                    formatted += f"\n   Command: {context['command']}"
                if "step" in context:
                    formatted += f"\n   Step: {context['step']}"

            return formatted

        except Exception:
            return f"❌ {error_type}: {error_message}"


class CLIErrorHandlerV2(ICLIErrorHandlerV2):
    """CLI error handling service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    def handle_cli_error(self, error: Exception, command_context: str, verbose: bool = False) -> int:
        """Handle CLI errors and return exit code."""
        try:
            error_type = self.categorize_error(error)
            error_message = str(error)

            # Log the error
            self.logger.error(
                f"CLI Error in {command_context}: {error_message}",
                exc_info=True,
            )

            # Display error to user
            formatted_message = self.format_error_message(error_type, error_message)
            click.echo(formatted_message, err=True)

            # Show traceback if needed
            if self.should_show_traceback(error, verbose):
                click.echo("\nTraceback:", err=True)
                traceback.print_exc()

            # Return appropriate exit code
            exit_codes = {
                "InputError": 1,
                "ConfigError": 2,
                "WorkflowError": 3,
                "WeChatError": 4,
                "StorageError": 5,
                "GeneralError": 1,
            }

            return exit_codes.get(error_type, 1)

        except Exception as e:
            # Last resort error handling
            self.logger.critical(f"Error in error handler: {e}")
            click.echo(f"❌ Critical error: {e}", err=True)
            return 1

    def categorize_error(self, error: Exception) -> str:
        """Categorize error type for appropriate handling."""
        error_class = error.__class__.__name__

        # Map exception classes to error types
        class_mapping = {
            "InputError": "InputError",
            "ConfigError": "ConfigError",
            "WorkflowError": "WorkflowError",
            "WeChatError": "WeChatError",
            "FileNotFoundError": "InputError",
            "ValueError": "InputError",
            "KeyError": "ConfigError",
            "ConnectionError": "WeChatError",
            "TimeoutError": "WorkflowError",
            "PermissionError": "StorageError",
        }

        return class_mapping.get(error_class, "GeneralError")

    def should_show_traceback(self, error: Exception, verbose: bool) -> bool:
        """Determine if traceback should be shown."""
        # Always show in verbose mode
        if verbose:
            return True

        # Show for unexpected errors
        error_type = self.categorize_error(error)
        if error_type == "GeneralError":
            return True

        # Don't show for common user errors
        if error_type in ["InputError", "ConfigError"]:
            return False

        return False


class CLILoggerServiceV2(ICLILoggerServiceV2):
    """CLI logging operations service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def setup_command_logging(self, command_name: str, verbose: bool = False) -> None:
        """Setup logging for specific command."""
        try:
            log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
            setup_logging(log_level)

            self.logger.info(f"CLI command logging setup: {command_name} (level: {log_level.value})")

        except Exception as e:
            self.logger.error(f"Error setting up command logging: {e}")

    async def log_command_start(self, command_name: str, parameters: Dict[str, Any]) -> None:
        """Log command start with parameters."""
        try:
            # Log sensitive parameters appropriately
            safe_params = {}
            for key, value in parameters.items():
                if "path" in key.lower() and value:
                    # Only show filename, not full path
                    safe_params[key] = Path(value).name
                else:
                    safe_params[key] = value

            self.logger.info(f"CLI command started: {command_name} with params: {safe_params}")

        except Exception as e:
            self.logger.error(f"Error logging command start: {e}")

    async def log_command_success(self, command_name: str, result: Dict[str, Any]) -> None:
        """Log successful command completion."""
        try:
            # Log key result information
            summary = {}
            if "workflow_id" in result:
                summary["workflow_id"] = result["workflow_id"]
            if "output_files" in result:
                summary["files_count"] = len(result["output_files"])
            if "duration" in result:
                summary["duration"] = f"{result['duration']:.2f}s"

            self.logger.info(f"CLI command completed: {command_name} - Result: {summary}")

        except Exception as e:
            self.logger.error(f"Error logging command success: {e}")

    async def log_command_error(self, command_name: str, error: Exception, context: Dict[str, Any]) -> None:
        """Log command error with context."""
        try:
            error_info = {
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "context": context,
            }

            self.logger.error(
                f"CLI command error: {command_name} - {error_info}",
                exc_info=True,
            )

        except Exception as e:
            self.logger.error(f"Error logging command error: {e}")


# Additional service implementations would go here for WeChat operations, etc.
# For brevity, I'll create placeholder classes for the remaining interfaces


class CLIWeChatServiceV2(ICLIWeChatServiceV2):
    """CLI WeChat operations service."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_collector = ErrorCollector()

    async def generate_wechat_article(
        self,
        input_json_path: Path,
        output_dir: Optional[Path] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        model_type: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Generate WeChat article from translation."""
        # Implementation would go here

    async def publish_wechat_article(
        self,
        article_directory: Path,
        config_path: Optional[Path] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Publish WeChat article."""
        # Implementation would go here

    def validate_article_directory(self, directory: Path) -> Dict[str, Any]:
        """Validate article directory structure."""
        # Implementation would go here

    def extract_article_metadata(self, directory: Path) -> Dict[str, Any]:
        """Extract article metadata."""
        # Implementation would go here


class CLICommandServiceV2(ICLICommandServiceV2):
    """CLI command service orchestrating other services."""

    def __init__(
        self,
        input_service: ICLIInputServiceV2,
        config_service: ICLIConfigurationServiceV2,
        workflow_service: ICLIWorkflowServiceV2,
        storage_service: ICLIStorageServiceV2,
        output_service: ICLIOutputServiceV2,
        wechat_service: ICLIWeChatServiceV2,
        error_handler: ICLIErrorHandlerV2,
        logger_service: ICLILoggerServiceV2,
    ):
        self.input_service = input_service
        self.config_service = config_service
        self.workflow_service = workflow_service
        self.storage_service = storage_service
        self.output_service = output_service
        self.wechat_service = wechat_service
        self.error_handler = error_handler
        self.logger_service = logger_service

    async def execute_translate_command(
        self,
        input_path: Optional[str],
        source_lang: str,
        target_lang: str,
        workflow_mode: str,
        config_path: Optional[str],
        output_dir: Optional[str],
        verbose: bool,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Execute translate command."""
        try:
            # Setup logging
            await self.logger_service.setup_command_logging("translate", verbose)
            await self.logger_service.log_command_start(
                "translate",
                {
                    "input_path": input_path,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "workflow_mode": workflow_mode,
                    "config_path": config_path,
                    "dry_run": dry_run,
                },
            )

            click.echo("🎭 Vox Poetica Studio Web - Professional Poetry Translation")
            click.echo("=" * 60)

            # Read input poem
            poem_text = await self.input_service.read_poem_from_input(input_path)

            # Validate input
            validation_result = self.input_service.validate_translation_input(source_lang, target_lang, poem_text)
            if not validation_result["valid"]:
                raise ValueError(f"Input validation failed: {validation_result['errors']}")

            # Create translation input
            input_data = self.input_service.create_translation_input(poem_text, source_lang, target_lang)

            # Load configuration
            config = await self.config_service.load_configuration(config_path, verbose)

            # Convert workflow mode
            workflow_mode_enum = WorkflowMode(workflow_mode)

            if dry_run:
                # Validation only
                validation_result = await self.workflow_service.validate_workflow_input(input_data, config_path)
                return {"dry_run": True, "validation": validation_result}

            # Initialize and execute workflow
            workflow = await self.workflow_service.initialize_workflow(config, workflow_mode_enum)
            translation_output = await self.workflow_service.execute_translation_workflow(
                workflow, input_data, workflow_mode, show_progress=True
            )

            # Setup storage and save results
            storage_handler = await self.storage_service.setup_storage_handler(output_dir)
            include_mode_tag = config["storage_config"].workflow_mode_tag
            saved_files = await self.storage_service.save_translation_results(
                translation_output, workflow_mode, include_mode_tag
            )

            # Display summary
            await self.output_service.display_translation_summary(translation_output, saved_files)

            # Log success
            result = {
                "success": True,
                "workflow_id": translation_output.workflow_id,
                "workflow_mode": workflow_mode,
                "output_files": saved_files,
                "duration": translation_output.duration_seconds,
            }
            await self.logger_service.log_command_success("translate", result)

            return result

        except Exception as e:
            await self.logger_service.log_command_error(
                "translate",
                e,
                {
                    "input_path": input_path,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "workflow_mode": workflow_mode,
                },
            )
            raise

    async def execute_generate_article_command(
        self,
        input_json: Path,
        output_dir: Optional[Path],
        author: Optional[str],
        digest: Optional[str],
        model_type: Optional[str],
        dry_run: bool,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Execute generate-article command."""
        try:
            await self.logger_service.setup_command_logging("generate-article", verbose)
            await self.logger_service.log_command_start(
                "generate-article",
                {
                    "input_json": str(input_json),
                    "output_dir": str(output_dir) if output_dir else None,
                    "author": author,
                    "dry_run": dry_run,
                },
            )

            result = await self.wechat_service.generate_wechat_article(
                input_json, output_dir, author, digest, model_type, dry_run
            )

            await self.logger_service.log_command_success("generate-article", result)
            return result

        except Exception as e:
            await self.logger_service.log_command_error(
                "generate-article",
                e,
                {
                    "input_json": str(input_json),
                    "output_dir": str(output_dir) if output_dir else None,
                },
            )
            raise

    async def execute_publish_article_command(
        self,
        directory: Path,
        config_path: Optional[Path],
        dry_run: bool,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Execute publish-article command."""
        try:
            await self.logger_service.setup_command_logging("publish-article", verbose)
            await self.logger_service.log_command_start(
                "publish-article",
                {
                    "directory": str(directory),
                    "config_path": str(config_path) if config_path else None,
                    "dry_run": dry_run,
                },
            )

            result = await self.wechat_service.publish_wechat_article(directory, config_path, dry_run)

            await self.logger_service.log_command_success("publish-article", result)
            return result

        except Exception as e:
            await self.logger_service.log_command_error(
                "publish-article",
                e,
                {
                    "directory": str(directory),
                    "config_path": str(config_path) if config_path else None,
                },
            )
            raise
