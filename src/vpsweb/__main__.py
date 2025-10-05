"""
Vox Poetica Studio Web - CLI Entry Point

Professional AI-powered poetry translation using a Translator→Editor→Translator workflow.
"""

import sys
import asyncio
import click
from pathlib import Path
from typing import Optional, Dict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

from .utils.logger import setup_logging, get_logger
from .utils.config_loader import load_config, validate_config_files
from .utils.storage import StorageHandler
from .core.workflow import TranslationWorkflow
from .models.translation import TranslationInput
from .models.config import LogLevel


class CLIError(Exception):
    """Base exception for CLI errors."""
    pass


class ConfigError(CLIError):
    """Raised when configuration loading fails."""
    pass


class InputError(CLIError):
    """Raised when input handling fails."""
    pass


class WorkflowError(CLIError):
    """Raised when workflow execution fails."""
    pass


logger = get_logger(__name__)


def read_poem_from_input(input_path: Optional[str]) -> str:
    """
    Read poem text from file or stdin.

    Args:
        input_path: Path to input file, or None to read from stdin

    Returns:
        Poem text as string

    Raises:
        InputError: If reading fails
    """
    try:
        if input_path:
            # Read from file
            file_path = Path(input_path)
            if not file_path.exists():
                raise InputError(f"Input file not found: {input_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                poem_text = f.read().strip()

            if not poem_text:
                raise InputError(f"Input file is empty: {input_path}")

            click.echo(f"📖 Read poem from file: {input_path}")
            click.echo(f"   Length: {len(poem_text)} characters")

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

            poem_text = '\n'.join(poem_lines).strip()

            if not poem_text:
                raise InputError("No poem text provided via stdin")

            click.echo(f"   Length: {len(poem_text)} characters")

        return poem_text

    except IOError as e:
        raise InputError(f"Error reading input: {e}")
    except Exception as e:
        raise InputError(f"Unexpected error reading input: {e}")


def initialize_system(config_path: Optional[str], verbose: bool) -> tuple:
    """
    Initialize the translation system with configuration.

    Args:
        config_path: Path to custom config directory
        verbose: Whether to enable verbose logging

    Returns:
        Tuple of (complete_config, workflow_config)

    Raises:
        ConfigError: If configuration loading fails
    """
    try:
        click.echo("⚙️  Loading configuration...")

        # Load configuration
        complete_config = load_config(config_path)

        # Setup logging based on configuration
        log_config = complete_config.main.logging
        if verbose:
            log_config.level = LogLevel.DEBUG

        setup_logging(log_config)

        click.echo(f"   Workflow: {complete_config.main.workflow.name} v{complete_config.main.workflow.version}")
        click.echo(f"   Providers: {', '.join(complete_config.providers.providers.keys())}")

        return complete_config, complete_config.main.workflow

    except Exception as e:
        raise ConfigError(f"Failed to initialize system: {e}")


async def execute_translation_workflow(
    workflow: TranslationWorkflow,
    input_data: TranslationInput,
    storage_handler: StorageHandler
) -> tuple:
    """
    Execute the translation workflow and save results.

    Args:
        workflow: Initialized workflow instance
        input_data: Translation input data
        storage_handler: Storage handler for saving results

    Returns:
        Tuple of (translation_output, file_path)

    Raises:
        WorkflowError: If workflow execution fails
    """
    try:
        # Execute workflow
        click.echo("🚀 Starting translation workflow...")
        with click.progressbar(length=100, label='Translating') as bar:
            translation_output = await workflow.execute(input_data, show_progress=True)
            bar.update(100)

        # Save results (both JSON and markdown)
        click.echo("💾 Saving translation results...")
        saved_files = storage_handler.save_translation_with_markdown(translation_output)

        return translation_output, saved_files

    except Exception as e:
        raise WorkflowError(f"Translation workflow failed: {e}")


def display_summary(translation_output, saved_files: Dict[str, Path]) -> None:
    """
    Display a summary of the translation results.

    Args:
        translation_output: The translation output
        saved_files: Dictionary with paths to saved files
    """
    click.echo("\n" + "=" * 60)
    click.echo("🎉 TRANSLATION COMPLETE!")
    click.echo("=" * 60)

    # Basic info
    click.echo(f"📋 Workflow ID: {translation_output.workflow_id}")
    click.echo(f"📁 Output file: {saved_files['json']}")
    click.echo(f"📄 Markdown (final): {saved_files['markdown_final']}")
    click.echo(f"📋 Markdown (log): {saved_files['markdown_log']}")
    click.echo(f"⏱️  Total time: {translation_output.duration_seconds:.2f}s")
    click.echo(f"🧮 Total tokens: {translation_output.total_tokens}")

    # Translation preview
    initial = translation_output.initial_translation.initial_translation
    revised = translation_output.revised_translation.revised_translation

    click.echo("\n📝 TRANSLATION PREVIEW:")
    click.echo("-" * 40)
    click.echo("Initial Translation:")
    click.echo(f"  {initial[:100]}{'...' if len(initial) > 100 else ''}")
    click.echo("\nRevised Translation:")
    click.echo(f"  {revised[:100]}{'...' if len(revised) > 100 else ''}")

    # Editor suggestions count
    editor_suggestions = translation_output.editor_review.editor_suggestions
    suggestions_count = len([line for line in editor_suggestions.split('\n') if line.strip().startswith(('1.', '2.', '3.', '4.', '5.'))])
    click.echo(f"\n📋 Editor suggestions: {suggestions_count}")

    click.echo("\n✅ Translation saved successfully!")


def validate_input_only(input_data: TranslationInput, config_path: Optional[str]) -> None:
    """
    Validate input and configuration without executing workflow.

    Args:
        input_data: Translation input to validate
        config_path: Path to configuration for validation

    Raises:
        ConfigError: If validation fails
    """
    try:
        click.echo("🔍 Validating configuration and input...")

        # Validate configuration
        validate_config_files(config_path)

        # Validate input (already done by Pydantic)
        click.echo(f"✅ Input validation passed")
        click.echo(f"   Source: {input_data.source_lang}")
        click.echo(f"   Target: {input_data.target_lang}")
        click.echo(f"   Poem length: {len(input_data.original_poem)} characters")

        click.echo("\n✅ Dry run completed - configuration and input are valid!")

    except Exception as e:
        raise ConfigError(f"Validation failed: {e}")


@click.group()
@click.version_option(version="0.1.1", prog_name="vpsweb")
def cli():
    """Vox Poetica Studio Web - Professional Poetry Translation

    Translate poetry using a collaborative Translator→Editor→Translator workflow
    that produces high-fidelity translations preserving aesthetic beauty and cultural context.
    """
    pass


@cli.command()
@click.option('--input', '-i', type=click.Path(exists=True), help='Input poem file')
@click.option('--source', '-s', required=True, type=click.Choice(['English', 'Chinese', 'Polish']),
              help='Source language')
@click.option('--target', '-t', required=True, type=click.Choice(['English', 'Chinese', 'Polish']),
              help='Target language')
@click.option('--config', '-c', type=click.Path(exists=True), help='Custom config directory')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
@click.option('--dry-run', is_flag=True, help='Validate without execution')
def translate(input, source, target, config, output, verbose, dry_run):
    """Translate a poem using the T-E-T workflow

    Examples:

    \b
    # Translate from file
    vpsweb translate -i poem.txt -s English -t Chinese

    # Translate from stdin
    echo "The fog comes on little cat feet." | vpsweb translate -s English -t Chinese

    # With custom configuration
    vpsweb translate -i poem.txt -s English -t Chinese -c ./my_config/

    # Dry run (validation only)
    vpsweb translate -i poem.txt -s English -t Chinese --dry-run
    """
    try:
        click.echo("🎭 Vox Poetica Studio Web - Professional Poetry Translation")
        click.echo("=" * 60)

        # Read input poem
        poem_text = read_poem_from_input(input)

        # Create translation input
        input_data = TranslationInput(
            original_poem=poem_text,
            source_lang=source,
            target_lang=target
        )

        # Initialize system
        complete_config, workflow_config = initialize_system(config, verbose)

        # Setup storage
        output_dir = output or complete_config.main.storage.output_dir
        storage_handler = StorageHandler(output_dir)

        if dry_run:
            # Dry run mode - validate only
            validate_input_only(input_data, config)
            return

        # Create and execute workflow
        workflow = TranslationWorkflow(workflow_config, complete_config.providers)

        # Execute async workflow
        translation_output, file_path = asyncio.run(
            execute_translation_workflow(workflow, input_data, storage_handler)
        )

        # Display summary
        display_summary(translation_output, file_path)

    except InputError as e:
        click.echo(f"❌ Input error: {e}", err=True)
        sys.exit(1)
    except ConfigError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except WorkflowError as e:
        click.echo(f"❌ Translation error: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n\n⏹️  Translation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()