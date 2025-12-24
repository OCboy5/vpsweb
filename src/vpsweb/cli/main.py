"""
Phase 3C: Refactored CLI Module with Service Layer.

This module provides a clean separation of concerns using dependency injection
and the service layer pattern for CLI operations.
"""

import sys
from pathlib import Path

import click

from vpsweb.core.container import DIContainer

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
from .services import (
    CLICommandServiceV2,
    CLIConfigurationServiceV2,
    CLIErrorHandlerV2,
    CLIInputServiceV2,
    CLILoggerServiceV2,
    CLIOutputServiceV2,
    CLIStorageServiceV2,
    CLIWeChatServiceV2,
    CLIWorkflowServiceV2,
)


class CLIApplicationV2:
    """
    Refactored CLI application using dependency injection
    and service layer pattern for clean separation of concerns.
    """

    def __init__(
        self,
        command_service: ICLICommandServiceV2,
        error_handler: ICLIErrorHandlerV2,
        logger_service: ICLILoggerServiceV2,
    ):
        """
        Initialize the CLI application with injected dependencies.

        Args:
            command_service: Service for executing CLI commands
            error_handler: Service for error handling and user messages
            logger_service: Service for logging operations
        """
        self.command_service = command_service
        self.error_handler = error_handler
        self.logger_service = logger_service

    def get_cli_group(self) -> click.Group:
        """Get the configured Click CLI group."""

        @click.group()
        @click.version_option(version="0.3.12", prog_name="vpsweb")
        def cli():
            """Vox Poetica Studio Web - Professional Poetry Translation

            Translate poetry using a collaborative Translator→Editor→Translator workflow
            that produces high-fidelity translations preserving aesthetic beauty and cultural context.
            """

        # Add commands
        cli.add_command(self._translate_command())
        cli.add_command(self._generate_article_command())
        cli.add_command(self._publish_article_command())

        return cli

    def _translate_command(self) -> click.Command:
        """Create the translate command."""

        @click.command()
        @click.option(
            "--input",
            "-i",
            type=click.Path(exists=True),
            help="Input poem file",
        )
        @click.option(
            "--source",
            "-s",
            required=True,
            type=click.Choice(["English", "Chinese", "Polish"]),
            help="Source language",
        )
        @click.option(
            "--target",
            "-t",
            required=True,
            type=click.Choice(["English", "Chinese", "Polish"]),
            help="Target language",
        )
        @click.option(
            "--workflow-mode",
            "-w",
            type=click.Choice(["reasoning", "non_reasoning", "hybrid"]),
            default="hybrid",
            help="Workflow mode: reasoning, non_reasoning, or hybrid (default: hybrid)",
        )
        @click.option(
            "--config",
            "-c",
            type=click.Path(exists=True),
            help="Custom config directory",
        )
        @click.option("--output", "-o", type=click.Path(), help="Output directory")
        @click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
        @click.option("--dry-run", is_flag=True, help="Validate without execution")
        def translate(
            input,
            source,
            target,
            workflow_mode,
            config,
            output,
            verbose,
            dry_run,
        ):
            """Translate a poem using the T-E-T workflow

            Examples:

            \b
            # Translate from file (default hybrid mode)
            vpsweb translate -i poem.txt -s English -t Chinese

            \b
            # Translate with reasoning mode (highest quality)
            vpsweb translate -i poem.txt -s English -t Chinese -w reasoning

            \b
            # Translate with non-reasoning mode (faster, cost-effective)
            vpsweb translate -i poem.txt -s English -t Chinese -w non_reasoning

            \b
            # Translate from stdin
            echo "The fog comes on little cat feet." | vpsweb translate -s English -t Chinese

            \b
            # With custom configuration
            vpsweb translate -i poem.txt -s English -t Chinese -c ./my_config/

            \b
            # Dry run (validation only)
            vpsweb translate -i poem.txt -s English -t Chinese --dry-run
            """
            try:
                # Execute command through service layer
                import asyncio

                result = asyncio.run(
                    self.command_service.execute_translate_command(
                        input_path=input,
                        source_lang=source,
                        target_lang=target,
                        workflow_mode=workflow_mode,
                        config_path=config,
                        output_dir=output,
                        verbose=verbose,
                        dry_run=dry_run,
                    )
                )

                if dry_run:
                    click.echo("\n✅ Dry run completed - configuration and input are valid!")
                return result

            except Exception as e:
                exit_code = self.error_handler.handle_cli_error(error=e, command_context="translate", verbose=verbose)
                sys.exit(exit_code)

        return translate

    def _generate_article_command(self) -> click.Command:
        """Create the generate-article command."""

        @click.command()
        @click.option(
            "--input-json",
            "-j",
            required=True,
            type=click.Path(exists=True, path_type=Path),
            help="Path to translation JSON file",
        )
        @click.option(
            "--output-dir",
            "-o",
            type=click.Path(path_type=Path),
            help="Output directory for generated article",
        )
        @click.option(
            "--author",
            type=str,
            help="Article author name (default: 知韵VoxPoetica)",
        )
        @click.option("--digest", type=str, help="Custom digest (80-120 characters)")
        @click.option(
            "--model-type",
            "-m",
            type=click.Choice(["reasoning", "non_reasoning"]),
            default=None,
            help="Model type for translation notes: reasoning (slower, detailed) or non_reasoning (faster, efficient)",
        )
        @click.option(
            "--dry-run",
            is_flag=True,
            help="Generate article without external API calls",
        )
        @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
        def generate_article(
            input_json,
            output_dir,
            author,
            digest,
            model_type,
            dry_run,
            verbose,
        ):
            """Generate a WeChat article from translation JSON output.

            Creates a WeChat-compatible HTML article with translation notes,
            following the author-approved format and structure.

            Examples:

            \b
            # Generate article from translation JSON
            vpsweb generate-article -j outputs/json/陶渊明_歸園田居_chinese-english_hybrid_20251012_190558_63be1c5a.json

            \b
            # Generate with custom output directory
            vpsweb generate-article -j translation.json -o my_articles/

            \b
            # Generate with custom author
            vpsweb generate-article -j translation.json --author "My Name"

            \b
            # Generate with non-reasoning model (faster)
            vpsweb generate-article -j translation.json -m non_reasoning

            \b
            # Generate with reasoning model (detailed)
            vpsweb generate-article -j translation.json -m reasoning

            \b
            # Dry run to validate without external calls
            vpsweb generate-article -j translation.json --dry-run
            """
            try:
                # Execute command through service layer
                import asyncio

                result = asyncio.run(
                    self.command_service.execute_generate_article_command(
                        input_json=input_json,
                        output_dir=output_dir,
                        author=author,
                        digest=digest,
                        model_type=model_type,
                        dry_run=dry_run,
                        verbose=verbose,
                    )
                )

                # Display results (would be handled by the service)
                click.echo("\n✅ Article generated successfully!")
                click.echo(f"📁 Output directory: {result.get('output_directory', 'N/A')}")
                click.echo(f"📄 Article HTML: {result.get('html_path', 'N/A')}")
                click.echo(f"📋 Metadata: {result.get('metadata_path', 'N/A')}")

                if dry_run:
                    click.echo("\n🔍 Dry run completed - no external API calls made")

                return result

            except Exception as e:
                exit_code = self.error_handler.handle_cli_error(
                    error=e,
                    command_context="generate-article",
                    verbose=verbose,
                )
                sys.exit(exit_code)

        return generate_article

    def _publish_article_command(self) -> click.Command:
        """Create the publish-article command."""

        @click.command()
        @click.option(
            "--directory",
            "-d",
            required=True,
            type=click.Path(exists=True, file_okay=False, path_type=Path),
            help="Directory containing article.html and metadata.json to publish",
        )
        @click.option(
            "--config",
            "-c",
            type=click.Path(exists=True, path_type=Path),
            help="Path to WeChat configuration file",
        )
        @click.option(
            "--dry-run",
            is_flag=True,
            help="Preview API call without sending to WeChat",
        )
        @click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
        def publish_article(directory, config, dry_run, verbose):
            """Publish article from directory containing article.html and metadata.json.

            Uploads the generated article to WeChat Drafts (草稿) folder
            for manual review and publishing.

            Examples:

            \b
            # Publish article from directory
            vpsweb publish-article -d outputs/wechat_articles/slug/

            \b
            # Dry run to preview API call
            vpsweb publish-article -d directory/ --dry-run

            \b
            # Use custom WeChat configuration
            vpsweb publish-article -d directory/ -c custom_wechat.yaml
            """
            try:
                # Execute command through service layer
                import asyncio

                result = asyncio.run(
                    self.command_service.execute_publish_article_command(
                        directory=directory,
                        config_path=config,
                        dry_run=dry_run,
                        verbose=verbose,
                    )
                )

                # Display results (would be handled by the service)
                if dry_run:
                    click.echo("\n✅ Dry run completed - preview generated")
                    if "api_preview" in result:
                        click.echo("📤 API Endpoint: POST /cgi-bin/draft/add")
                        click.echo("📋 Request payload preview available")
                else:
                    click.echo("\n✅ Article published successfully!")
                    click.echo(f"📋 Draft ID: {result.get('draft_id', 'N/A')}")
                    click.echo("📝 Review and publish manually in WeChat Official Account backend")

                return result

            except Exception as e:
                exit_code = self.error_handler.handle_cli_error(
                    error=e, command_context="publish-article", verbose=verbose
                )
                sys.exit(exit_code)

        return publish_article


class CLIFactoryV2:
    """
    Factory for creating the VPSWeb CLI application with all dependencies
    properly configured and injected.
    """

    @staticmethod
    def create_application() -> CLIApplicationV2:
        """
        Create and configure the VPSWeb CLI application.

        Returns:
            Configured CLI application
        """

        # Create DI container
        container = DIContainer()

        # Register core services as singletons
        container.register_singleton(ICLIInputServiceV2, CLIInputServiceV2)
        container.register_singleton(ICLIConfigurationServiceV2, CLIConfigurationServiceV2)
        container.register_singleton(ICLIWorkflowServiceV2, CLIWorkflowServiceV2)
        container.register_singleton(ICLIStorageServiceV2, CLIStorageServiceV2)
        container.register_singleton(ICLIOutputServiceV2, CLIOutputServiceV2)
        container.register_singleton(ICLIWeChatServiceV2, CLIWeChatServiceV2)
        container.register_singleton(ICLIErrorHandlerV2, CLIErrorHandlerV2)
        container.register_singleton(ICLILoggerServiceV2, CLILoggerServiceV2)

        # Resolve core services
        input_service = container.resolve(ICLIInputServiceV2)
        config_service = container.resolve(ICLIConfigurationServiceV2)
        workflow_service = container.resolve(ICLIWorkflowServiceV2)
        storage_service = container.resolve(ICLIStorageServiceV2)
        output_service = container.resolve(ICLIOutputServiceV2)
        wechat_service = container.resolve(ICLIWeChatServiceV2)
        error_handler = container.resolve(ICLIErrorHandlerV2)
        logger_service = container.resolve(ICLILoggerServiceV2)

        # Create command service with all dependencies
        command_service = CLICommandServiceV2(
            input_service=input_service,
            config_service=config_service,
            workflow_service=workflow_service,
            storage_service=storage_service,
            output_service=output_service,
            wechat_service=wechat_service,
            error_handler=error_handler,
            logger_service=logger_service,
        )

        # Create CLI application
        cli_app = CLIApplicationV2(
            command_service=command_service,
            error_handler=error_handler,
            logger_service=logger_service,
        )

        return cli_app


# Convenience function for creating the CLI
def create_cli() -> click.Group:
    """
    Convenience function to create the VPSWeb CLI.

    This is the main entry point that replaces the original CLI pattern.
    """
    cli_app = CLIFactoryV2.create_application()
    return cli_app.get_cli_group()


# For backward compatibility - the original CLI entry point
def main():
    """Main entry point for the CLI application."""
    cli = create_cli()
    cli()


if __name__ == "__main__":
    main()
