"""
Vox Poetica Studio Web - CLI Entry Point

Professional AI-powered poetry translation using a Translator→Editor→Translator workflow.
"""

import sys
import asyncio
import click
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

from .utils.logger import setup_logging, get_logger
from .utils.config_loader import (
    load_config,
    validate_config_files,
    load_wechat_config,
    validate_wechat_setup,
)
from .utils.storage import StorageHandler
from .utils.article_generator import ArticleGenerator
from .utils.translation_notes_synthesizer import TranslationNotesSynthesizer
from .core.workflow import TranslationWorkflow
from .models.translation import TranslationInput
from .models.config import LogLevel, WorkflowMode


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


class WeChatError(CLIError):
    """Raised when WeChat operations fail."""

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

            with open(file_path, "r", encoding="utf-8") as f:
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

            poem_text = "\n".join(poem_lines).strip()

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

        click.echo(
            f"   Workflow: {complete_config.main.workflow.name} v{complete_config.main.workflow.version}"
        )
        click.echo(
            f"   Providers: {', '.join(complete_config.providers.providers.keys())}"
        )

        return complete_config, complete_config.main.workflow

    except Exception as e:
        raise ConfigError(f"Failed to initialize system: {e}")


async def execute_translation_workflow(
    workflow: TranslationWorkflow,
    input_data: TranslationInput,
    storage_handler: StorageHandler,
    workflow_mode: str = None,
    include_mode_tag: bool = False,
) -> tuple:
    """
    Execute the translation workflow and save results.

    Args:
        workflow: Initialized workflow instance
        input_data: Translation input data
        storage_handler: Storage handler for saving results
        workflow_mode: Workflow mode used for translation
        include_mode_tag: Whether to include workflow mode in filename

    Returns:
        Tuple of (translation_output, saved_files)

    Raises:
        WorkflowError: If workflow execution fails
    """
    try:
        # Execute workflow
        click.echo(f"🚀 Starting translation workflow ({workflow_mode} mode)...")

        # Display original poem
        click.echo(
            f"\n📄 Original Poem ({input_data.source_lang} → {input_data.target_lang}):"
        )
        click.echo("-" * 30)
        # Show poem with proper formatting, limiting length for display
        poem = input_data.original_poem
        if len(poem) > 200:
            poem = poem[:200] + "..."
        click.echo(poem)
        click.echo("-" * 30)
        click.echo()  # Add spacing

        translation_output = await workflow.execute(input_data, show_progress=True)

        # Save results (both JSON and markdown)
        click.echo("💾 Saving translation results...")
        saved_files = storage_handler.save_translation_with_markdown(
            translation_output, workflow_mode, include_mode_tag
        )

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
    click.echo(f"🔄 Workflow Mode: {translation_output.workflow_mode}")
    click.echo(f"📁 Output file: {saved_files['json']}")
    click.echo(f"📄 Markdown (final): {saved_files['markdown_final']}")
    click.echo(f"📋 Markdown (log): {saved_files['markdown_log']}")

    # Step-by-step details
    click.echo("\n📊 Step-by-Step Details:")

    # Format duration and cost for display
    def format_duration(duration):
        if duration is None:
            return "N/A"
        return f"{duration:.2f}s"

    def format_cost(cost):
        if cost is None:
            return "N/A"
        return f"¥{cost:.6f}"

    click.echo(
        f"  Step 1 (Initial): 🧮 {translation_output.initial_translation.tokens_used} tokens | ⏱️  {format_duration(getattr(translation_output.initial_translation, 'duration', None))} | 💰 {format_cost(getattr(translation_output.initial_translation, 'cost', None))}"
    )
    click.echo(
        f"  Step 2 (Editor): 🧮 {translation_output.editor_review.tokens_used} tokens | ⏱️  {format_duration(getattr(translation_output.editor_review, 'duration', None))} | 💰 {format_cost(getattr(translation_output.editor_review, 'cost', None))}"
    )
    click.echo(
        f"  Step 3 (Revision): 🧮 {translation_output.revised_translation.tokens_used} tokens | ⏱️  {format_duration(getattr(translation_output.revised_translation, 'duration', None))} | 💰 {format_cost(getattr(translation_output.revised_translation, 'cost', None))}"
    )

    # Total summary
    click.echo(
        f"\n📈 Overall: 🧮 {translation_output.total_tokens} total tokens | ⏱️  {translation_output.duration_seconds:.2f}s total time | 💰 {format_cost(translation_output.total_cost)} total cost"
    )

    # Editor suggestions count (improved counting)
    editor_suggestions = translation_output.editor_review.editor_suggestions
    if editor_suggestions:
        # Count lines that start with numbers (1., 2., 3., etc.)
        suggestions_count = len(
            [
                line
                for line in editor_suggestions.split("\n")
                if line.strip() and line.strip()[0].isdigit()
            ]
        )
        click.echo(f"📋 Editor suggestions: {suggestions_count}")
    else:
        click.echo(f"📋 Editor suggestions: 0")

    click.echo("\n✅ Translation saved successfully!")


def validate_input_only(
    input_data: TranslationInput, config_path: Optional[str]
) -> None:
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
@click.version_option(version="0.2.2", prog_name="vpsweb")
def cli():
    """Vox Poetica Studio Web - Professional Poetry Translation

    Translate poetry using a collaborative Translator→Editor→Translator workflow
    that produces high-fidelity translations preserving aesthetic beauty and cultural context.
    """
    pass


@cli.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input poem file")
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
    "--config", "-c", type=click.Path(exists=True), help="Custom config directory"
)
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
@click.option("--dry-run", is_flag=True, help="Validate without execution")
def translate(input, source, target, workflow_mode, config, output, verbose, dry_run):
    """Translate a poem using the T-E-T workflow

    Examples:

    \b
    # Translate from file (default hybrid mode)
    vpsweb translate -i poem.txt -s English -t Chinese

    # Translate with reasoning mode (highest quality)
    vpsweb translate -i poem.txt -s English -t Chinese -w reasoning

    # Translate with non-reasoning mode (faster, cost-effective)
    vpsweb translate -i poem.txt -s English -t Chinese -w non_reasoning

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
            original_poem=poem_text, source_lang=source, target_lang=target
        )

        # Initialize system
        complete_config, workflow_config = initialize_system(config, verbose)

        # Convert workflow mode string to enum
        workflow_mode_enum = WorkflowMode(workflow_mode)

        # Setup storage
        output_dir = output or complete_config.main.storage.output_dir
        storage_handler = StorageHandler(output_dir)

        if dry_run:
            # Dry run mode - validate only
            validate_input_only(input_data, config)
            return

        # Create and execute workflow with specified mode
        workflow = TranslationWorkflow(
            workflow_config, complete_config.providers, workflow_mode_enum
        )

        # Get storage settings
        include_mode_tag = complete_config.main.storage.workflow_mode_tag

        # Execute async workflow
        translation_output, saved_files = asyncio.run(
            execute_translation_workflow(
                workflow, input_data, storage_handler, workflow_mode, include_mode_tag
            )
        )

        # Display summary
        display_summary(translation_output, saved_files)

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


@cli.command()
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
    "--author", type=str, help="Article author name (default: 施知韵VoxPoetica)"
)
@click.option("--digest", type=str, help="Custom digest (80-120 characters)")
@click.option(
    "--dry-run", is_flag=True, help="Generate article without external API calls"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def generate_article(input_json, output_dir, author, digest, dry_run, verbose):
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
    # Dry run to validate without external calls
    vpsweb generate-article -j translation.json --dry-run
    """
    try:
        # Setup logging
        if verbose:
            setup_logging(LogLevel.DEBUG)
        else:
            setup_logging(LogLevel.INFO)

        logger = get_logger(__name__)
        click.echo("🚀 Generating WeChat article from translation JSON...")

        # Validate input file
        if not input_json.exists():
            raise InputError(f"Translation JSON file not found: {input_json}")

        if not input_json.suffix == ".json":
            raise InputError(f"Input file must be a JSON file: {input_json}")

        # Load WeChat configuration
        try:
            wechat_config = load_wechat_config()
            click.echo("✅ WeChat configuration loaded successfully")
        except Exception as e:
            raise ConfigError(f"Failed to load WeChat configuration: {e}")

        # Load complete configuration for LLM providers
        complete_config = load_config()

        # Initialize article generator
        from .utils.config_loader import load_article_generation_config

        article_gen_config = load_article_generation_config()
        article_generator = ArticleGenerator(
            article_gen_config, providers_config=complete_config.providers
        )

        # Generate article
        click.echo(f"📝 Processing translation file: {input_json.name}")

        result = article_generator.generate_from_translation(
            translation_json_path=str(input_json),
            output_dir=str(output_dir) if output_dir else None,
            author=author,
            digest=digest,
        )

        # Display results
        click.echo("\n✅ Article generated successfully!")
        click.echo(f"📁 Output directory: {result.output_directory}")
        click.echo(f"📄 Article HTML: {result.html_path}")
        click.echo(f"📋 Metadata: {result.metadata_path}")

        if result.markdown_path:
            click.echo(f"📝 Markdown: {result.markdown_path}")

        click.echo(f"🏷️  Article slug: {result.slug}")
        click.echo(f"📰 Article title: {result.article.title}")
        click.echo(f"📝 Digest: {result.article.digest}")

        # Next steps suggestion
        click.echo("\n🎯 Next steps:")
        click.echo(f"   Publish with: vpsweb publish-article -a {result.metadata_path}")

    except InputError as e:
        click.echo(f"❌ Input error: {e}", err=True)
        sys.exit(1)
    except ConfigError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except WeChatError as e:
        click.echo(f"❌ WeChat operation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option(
    "--article",
    "-a",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to article metadata file (metadata.json)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to WeChat configuration file",
)
@click.option(
    "--dry-run", is_flag=True, help="Preview API call without sending to WeChat"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def publish_article(article, config, dry_run, verbose):
    """Publish generated article to WeChat Official Account drafts.

    Uploads the generated article to WeChat Drafts (草稿) folder
    for manual review and publishing.

    Examples:

    \b
    # Publish article to WeChat drafts
    vpsweb publish-article -a outputs/wechat_articles/slug/metadata.json

    \b
    # Dry run to preview API call
    vpsweb publish-article -a metadata.json --dry-run

    \b
    # Use custom WeChat configuration
    vpsweb publish-article -a metadata.json -c custom_wechat.yaml
    """
    try:
        # For dry run, we don't need async
        if dry_run:
            # Setup logging
            if verbose:
                setup_logging(LogLevel.DEBUG)
            else:
                setup_logging(LogLevel.INFO)

            logger = get_logger(__name__)
            click.echo("🚀 Publishing article to WeChat Official Account...")

            # Validate article metadata file
            if not article.exists():
                raise InputError(f"Article metadata file not found: {article}")

            if article.name != "metadata.json":
                click.echo("⚠️  Warning: Expected metadata.json file")

            # Load article metadata
            import json

            with open(article, "r", encoding="utf-8") as f:
                article_metadata = json.load(f)

            # Load article HTML
            html_path = article.parent / "article.html"
            if not html_path.exists():
                raise InputError(f"Article HTML file not found: {html_path}")

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Create WeChat article
            from .models.wechat import WeChatArticle

            wechat_article = WeChatArticle(
                title=article_metadata.get("title", ""),
                content=html_content,
                digest=article_metadata.get("digest", ""),
                author=article_metadata.get("author", "施知韵VoxPoetica"),
                poem_title=article_metadata.get("poem_title", ""),
                poet_name=article_metadata.get("poet_name", ""),
                source_lang=article_metadata.get("source_lang", ""),
                target_lang=article_metadata.get("target_lang", ""),
                translation_workflow_id=article_metadata.get("workflow_id", ""),
                translation_json_path=article_metadata.get("source_json_path", ""),
            )

            click.echo("\n🔍 DRY RUN MODE - Previewing API call:")
            click.echo("📤 API Endpoint: POST /cgi-bin/draft/add")
            click.echo("📋 Request payload:")

            api_payload = {"articles": [wechat_article.to_wechat_api_dict()]}

            import json

            click.echo(json.dumps(api_payload, indent=2, ensure_ascii=False))
            click.echo("\n✅ Dry run completed - No API calls made")
            return

        # For actual publishing, run async function
        asyncio.run(_publish_article_async(article, config, verbose))

    except InputError as e:
        click.echo(f"❌ Input error: {e}", err=True)
        sys.exit(1)
    except ConfigError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except WeChatError as e:
        click.echo(f"❌ WeChat operation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


async def _publish_article_async(article, config, verbose):
    """Async implementation for publishing article to WeChat."""
    try:
        # Setup logging
        if verbose:
            setup_logging(LogLevel.DEBUG)
        else:
            setup_logging(LogLevel.INFO)

        logger = get_logger(__name__)
        click.echo("🚀 Publishing article to WeChat Official Account...")

        # Validate article metadata file
        if not article.exists():
            raise InputError(f"Article metadata file not found: {article}")

        if article.name != "metadata.json":
            click.echo("⚠️  Warning: Expected metadata.json file")

        # Load WeChat configuration
        try:
            if config:
                wechat_config = load_wechat_config(config.parent)
            else:
                wechat_config = load_wechat_config()

            # Validate configuration
            validate_wechat_setup()
            click.echo("✅ WeChat configuration validated successfully")

        except Exception as e:
            raise ConfigError(f"Failed to load WeChat configuration: {e}")

        # Load article metadata
        import json

        with open(article, "r", encoding="utf-8") as f:
            article_metadata = json.load(f)

        # Load article HTML
        html_path = article.parent / "article.html"
        if not html_path.exists():
            raise InputError(f"Article HTML file not found: {html_path}")

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Create WeChat article
        from .models.wechat import WeChatArticle

        wechat_article = WeChatArticle(
            title=article_metadata.get("title", ""),
            content=html_content,
            digest=article_metadata.get("digest", ""),
            author=article_metadata.get("author", "施知韵VoxPoetica"),
            poem_title=article_metadata.get("poem_title", ""),
            poet_name=article_metadata.get("poet_name", ""),
            source_lang=article_metadata.get("source_lang", ""),
            target_lang=article_metadata.get("target_lang", ""),
            translation_workflow_id=article_metadata.get("workflow_id", ""),
            translation_json_path=article_metadata.get("source_json_path", ""),
        )

        # Initialize WeChat client
        from .services.wechat import WeChatClient

        wechat_client = WeChatClient(wechat_config)

        # Test connection
        click.echo("🔗 Testing WeChat API connection...")
        if not await wechat_client.test_connection():
            raise WeChatError("WeChat API connection test failed")

        # Create draft
        click.echo("📤 Creating draft in WeChat Official Account...")
        draft_response = await wechat_client.create_draft(wechat_article)

        if draft_response.media_id:
            click.echo(f"✅ Article published to drafts successfully!")
            click.echo(f"📋 Draft ID: {draft_response.media_id}")
            click.echo(
                "📝 Review and publish manually in WeChat Official Account backend"
            )

            # Save publish result
            publish_result = {
                "success": True,
                "draft_id": draft_response.media_id,
                "article_path": str(article),
                "metadata_path": str(article),
                "published_at": (
                    draft_response.created_at.isoformat()
                    if draft_response.created_at
                    else None
                ),
                "created_at": datetime.now().isoformat(),
            }

            publish_result_path = article.parent / "publish_result.json"
            with open(publish_result_path, "w", encoding="utf-8") as f:
                json.dump(publish_result, f, indent=2, ensure_ascii=False)

            click.echo(f"💾 Publish result saved: {publish_result_path}")
        else:
            raise WeChatError("Failed to get draft ID from WeChat API")

    except InputError as e:
        raise  # Re-raise to be caught by outer function
    except ConfigError as e:
        raise  # Re-raise to be caught by outer function
    except WeChatError as e:
        raise  # Re-raise to be caught by outer function
    except Exception as e:
        raise  # Re-raise to be caught by outer function


if __name__ == "__main__":
    cli()
