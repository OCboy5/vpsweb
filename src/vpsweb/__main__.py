"""
Vox Poetica Studio Web - CLI Entry Point

Professional AI-powered poetry translation using a Translator→Editor→Translator workflow.
"""

import sys
import os
import asyncio
import json
import click
from pathlib import Path
from typing import Optional, Dict, Any
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
    load_wechat_complete_config,
    validate_wechat_setup,
    load_model_registry_config,
    load_task_templates_config,
    load_config,
    validate_config_files,
)
from .services.config import initialize_config_facade, get_config_facade
from .utils.storage import StorageHandler
from .utils.article_generator import ArticleGenerator
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

        # Initialize ConfigFacade for centralized configuration access
        config_facade = initialize_config_facade(complete_config)

        # Setup logging based on configuration
        log_config = complete_config.main.logging
        if verbose:
            log_config.level = LogLevel.DEBUG

        setup_logging(log_config)

        # Display configuration summary using ConfigFacade
        workflow_info = config_facade.get_workflow_info()
        click.echo(f"   Workflow: {workflow_info['name']} v{workflow_info['version']}")
        click.echo(f"   Providers: {', '.join(config_facade.get_provider_names())}")

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
@click.version_option(version="0.5.5", prog_name="vpsweb")
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

        # Create and execute workflow with specified mode using ConfigFacade
        config_facade = get_config_facade()
        workflow = TranslationWorkflow(config_facade=config_facade)

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
    "--author", type=str, help="Article author name (default: 知韵VoxPoetica)"
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
    "--dry-run", is_flag=True, help="Generate article without external API calls"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def generate_article(
    input_json, output_dir, author, digest, model_type, dry_run, verbose
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
            wechat_config = load_wechat_complete_config()
            # Also load raw YAML data for LLM configuration display
            from .utils.config_loader import load_yaml_file

            wechat_yaml_path = Path("config/wechat.yaml")
            wechat_raw_config = load_yaml_file(wechat_yaml_path)
            click.echo("✅ WeChat configuration loaded successfully")
        except Exception as e:
            raise ConfigError(f"Failed to load WeChat configuration: {e}")

        # Initialize ConfigFacade for LLM providers
        complete_config = load_config()
        config_facade = initialize_config_facade(complete_config)

        # Initialize article generator

        # Get article generation config from complete config, fallback to raw YAML
        article_gen_config = wechat_config.get("article_generation")
        if not article_gen_config:
            article_gen_config = wechat_raw_config.get("article_generation")
            click.echo("⚠️  Using raw YAML config for article generation")

        if not article_gen_config:
            raise ConfigError("Failed to load article generation configuration")

        # Override model_type if specified via CLI
        if model_type:
            article_gen_config.model_type = model_type
            # Also update the prompt template to match the model type
            if model_type == "reasoning":
                article_gen_config.prompt_template = "wechat_article_notes_reasoning"
            else:  # non_reasoning
                article_gen_config.prompt_template = "wechat_article_notes_nonreasoning"
            click.echo(f"   🎯 Using Model Type: {model_type} (CLI override)")
        else:
            click.echo(
                f"   🎯 Using Model Type: {article_gen_config.model_type} (from config)"
            )

        article_generator = ArticleGenerator(
            config=article_gen_config, config_facade=config_facade
        )

        # Display important configuration items
        click.echo("\n📋 Article Generation Configuration:")
        click.echo(f"   📄 HTML Template: {article_gen_config.article_template}")
        click.echo(f"   🤖 LLM Prompt Template: {article_gen_config.prompt_template}")
        click.echo(
            f"   📝 Include Translation Notes: {article_gen_config.include_translation_notes}"
        )

        # Display LLM provider information for translation notes synthesis
        if article_gen_config.include_translation_notes:
            if (
                hasattr(article_generator, "llm_factory")
                and article_generator.llm_factory
            ):
                # LLM is configured and available - use hardcoded WeChat config for now
                model_type = article_gen_config.model_type

                # Use WeChat LLM configuration based on model_type
                if model_type == "reasoning":
                    llm_provider = "deepseek"
                    llm_model = "deepseek-reasoner"
                else:  # non_reasoning
                    llm_provider = "tongyi"
                    llm_model = "qwen-plus-latest"

                click.echo(f"   🧠 LLM Provider (Notes): {llm_provider}")
                click.echo(f"   🎯 LLM Model (Notes): {llm_model}")
            else:
                click.echo(
                    f"   ⚠️  LLM Not Available: Translation notes synthesis disabled"
                )
        else:
            click.echo(f"   ⚠️  Translation Notes: DISABLED in configuration")

        click.echo("")  # Add spacing before next section

        # Generate article
        click.echo(f"📝 Processing translation file: {input_json.name}")

        result = article_generator.generate_from_translation(
            translation_json_path=str(input_json),
            output_dir=str(output_dir) if output_dir else None,
            author=author,
            digest=digest,
            dry_run=dry_run,
        )

        # Display results
        click.echo("\n✅ Article generated successfully!")
        click.echo(f"📁 Output directory: {result.output_directory}")
        click.echo(f"📄 Article HTML: {result.html_path}")
        click.echo(f"📋 Metadata: {result.metadata_path}")

        click.echo(f"🏷️  Article slug: {result.slug}")
        click.echo(f"📰 Article title: {result.article.title}")

        # Show digest info
        digest_content = result.article.digest
        click.echo(f"📝 Digest: {digest_content}")

        # Display LLM metrics if available
        if result.llm_metrics and article_gen_config.include_translation_notes:
            metrics = result.llm_metrics

            # Format duration and cost for display
            def format_duration(duration):
                if duration is None:
                    return "N/A"
                if duration < 60:
                    return f"{duration:.2f}s"
                else:
                    minutes = int(duration // 60)
                    seconds = duration % 60
                    return f"{minutes}m {seconds:.1f}s"

            def format_cost(cost):
                if cost is None:
                    return "N/A"
                return f"¥{cost:.6f}"

            click.echo("\n📊 LLM Translation Notes Metrics:")
            click.echo(f"   🧮 Tokens Used: {metrics.get('tokens_used', 'N/A')}")
            click.echo(f"      ⬇️ Prompt: {metrics.get('prompt_tokens', 'N/A')}")
            click.echo(f"      ⬆️ Completion: {metrics.get('completion_tokens', 'N/A')}")
            click.echo(f"   ⏱️  Time Spent: {format_duration(metrics.get('duration'))}")
            click.echo(f"   💰 Cost: {format_cost(metrics.get('cost'))}")
            click.echo(
                f"   🤖 Model: {metrics.get('provider', 'N/A')}/{metrics.get('model', 'N/A')} ({metrics.get('model_type', 'N/A')})"
            )

        # Next steps suggestion
        click.echo("\n🎯 Next steps:")
        click.echo(
            f"   Publish with: vpsweb publish-article -d {result.output_directory}"
        )

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
    "--dry-run", is_flag=True, help="Preview API call without sending to WeChat"
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
        # For dry run, we don't need async
        if dry_run:
            # Setup logging
            if verbose:
                setup_logging(LogLevel.DEBUG)
            else:
                setup_logging(LogLevel.INFO)

            logger = get_logger(__name__)
            click.echo("🚀 Publishing article to WeChat Official Account...")

            # Validate article directory
            validation_result = validate_article_directory(directory)
            if not validation_result["valid"]:
                error_msg = "Directory validation failed:\n" + "\n".join(
                    f"  • {error}" for error in validation_result["errors"]
                )
                raise InputError(error_msg)

            click.echo(f"✅ Directory validated: {directory}")

            # Extract metadata
            metadata_result = extract_metadata(directory)
            if not metadata_result["valid"]:
                error_msg = "Metadata extraction failed:\n" + "\n".join(
                    f"  • {error}" for error in metadata_result["errors"]
                )
                raise InputError(error_msg)

            article_metadata = metadata_result["metadata"]
            click.echo("✅ Metadata extracted successfully")

            # Load article HTML
            html_path = validation_result["files"]["html_path"]
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            if not html_content.strip():
                raise InputError("article.html is empty or contains only whitespace")

            click.echo("✅ Article HTML loaded successfully")

            # Show cover image detection in verbose mode
            if verbose:
                cover_images = validation_result["files"].get("cover_images")
                if cover_images:
                    preferred_cover = validation_result["files"]["preferred_cover"]
                    click.echo(
                        f"📸 Found {len(cover_images)} cover image(s), would use: {preferred_cover.name}"
                    )
                else:
                    click.echo("📷 No cover images found")

            # Create WeChat article
            from .models.wechat import WeChatArticle

            wechat_article = WeChatArticle(
                title=article_metadata.get("title", ""),
                content=html_content,
                digest=article_metadata.get("digest", ""),
                author=article_metadata.get("author", "知韵VoxPoetica"),
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
        asyncio.run(_publish_article_async(directory, config, verbose))

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


def validate_article_directory(directory: Path) -> Dict[str, Any]:
    """
    Validate article directory contains required files.

    Args:
        directory: Path to article directory

    Returns:
        Dict with validation results:
        {
            "valid": bool,
            "errors": List[str],
            "files": {
                "html_path": Path,
                "metadata_path": Path
            }
        }
    """
    errors = []
    files = {}

    # Check if directory is actually a directory
    if not directory.is_dir():
        errors.append(f"Path is not a directory: {directory}")
        return {"valid": False, "errors": errors, "files": {}}

    # Check for required files
    html_path = directory / "article.html"
    metadata_path = directory / "metadata.json"

    if not html_path.exists():
        errors.append(f"Missing required file: article.html")
    else:
        files["html_path"] = html_path

    if not metadata_path.exists():
        errors.append(f"Missing required file: metadata.json")
    else:
        files["metadata_path"] = metadata_path

    # Check if files are readable and not empty
    if html_path.exists():
        if html_path.stat().st_size == 0:
            errors.append("article.html is empty")
        if not os.access(html_path, os.R_OK):
            errors.append("article.html is not readable")

    if metadata_path.exists():
        if metadata_path.stat().st_size == 0:
            errors.append("metadata.json is empty")
        if not os.access(metadata_path, os.R_OK):
            errors.append("metadata.json is not readable")

    # Check for optional cover images
    cover_image_patterns = [
        "cover_image_big.jpg",
        "cover_image_big.png",
        "cover_image_big.jpeg",
        "cover_image_small.jpg",
        "cover_image_small.png",
        "cover_image_small.jpeg",
        "cover.jpg",
        "cover.png",
        "cover.jpeg",
    ]

    cover_images = []
    for pattern in cover_image_patterns:
        cover_path = directory / pattern
        if cover_path.exists() and cover_path.stat().st_size > 0:
            cover_images.append(cover_path)

    if cover_images:
        files["cover_images"] = cover_images
        # Prefer big images, fallback to small if no big images
        big_images = [img for img in cover_images if "big" in img.name.lower()]
        files["preferred_cover"] = big_images[0] if big_images else cover_images[0]

    return {"valid": len(errors) == 0, "errors": errors, "files": files}


def extract_metadata(directory: Path) -> Dict[str, Any]:
    """
    Extract metadata from metadata.json file.

    Args:
        directory: Path to article directory

    Returns:
        Dict with extraction results:
        {
            "valid": bool,
            "errors": List[str],
            "metadata": Dict
        }
    """
    errors = []
    metadata = {}

    try:
        metadata_path = directory / "metadata.json"

        with open(metadata_path, "r", encoding="utf-8") as f:
            raw_metadata = json.load(f)

        # Validate required fields
        if "title" not in raw_metadata:
            errors.append("Missing required field: title")
        else:
            if not raw_metadata["title"].strip():
                errors.append("Field 'title' cannot be empty")
            metadata["title"] = raw_metadata["title"]

        if "digest" not in raw_metadata:
            errors.append("Missing required field: digest")
        else:
            if not raw_metadata["digest"].strip():
                errors.append("Field 'digest' cannot be empty")
            metadata["digest"] = raw_metadata["digest"]

        # Extract optional fields with defaults
        metadata["author"] = raw_metadata.get("author", "知韵VoxPoetica")
        metadata["poem_title"] = raw_metadata.get("poem_title", "")
        metadata["poet_name"] = raw_metadata.get("poet_name", "")
        metadata["source_lang"] = raw_metadata.get("source_lang", "")
        metadata["target_lang"] = raw_metadata.get("target_lang", "")
        metadata["source_json_path"] = raw_metadata.get("source_json_path", "")
        metadata["workflow_id"] = raw_metadata.get("workflow_id", "")
        metadata["created_at"] = raw_metadata.get("created_at", "")

        # Store all other fields as extra metadata
        for key, value in raw_metadata.items():
            if key not in metadata:
                metadata[key] = value

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in metadata.json: {e}")
    except Exception as e:
        errors.append(f"Error reading metadata.json: {e}")

    return {"valid": len(errors) == 0, "errors": errors, "metadata": metadata}


async def _publish_article_async(directory, config, verbose):
    """Async implementation for publishing article from directory to WeChat."""
    try:
        # Setup logging
        if verbose:
            setup_logging(LogLevel.DEBUG)
        else:
            setup_logging(LogLevel.INFO)

        logger = get_logger(__name__)
        click.echo("🚀 Publishing article to WeChat Official Account...")

        # Validate article directory
        validation_result = validate_article_directory(directory)
        if not validation_result["valid"]:
            error_msg = "Directory validation failed:\n" + "\n".join(
                f"  • {error}" for error in validation_result["errors"]
            )
            raise InputError(error_msg)

        click.echo(f"✅ Directory validated: {directory}")

        # Extract metadata
        metadata_result = extract_metadata(directory)
        if not metadata_result["valid"]:
            error_msg = "Metadata extraction failed:\n" + "\n".join(
                f"  • {error}" for error in metadata_result["errors"]
            )
            raise InputError(error_msg)

        article_metadata = metadata_result["metadata"]
        click.echo("✅ Metadata extracted successfully")

        # Load article HTML
        html_path = validation_result["files"]["html_path"]
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        if not html_content.strip():
            raise InputError("article.html is empty or contains only whitespace")

        click.echo("✅ Article HTML loaded successfully")

        # Load WeChat configuration
        try:
            if config:
                wechat_config = load_wechat_complete_config(config.parent)
            else:
                wechat_config = load_wechat_complete_config()

            # Validate configuration
            validate_wechat_setup()
            click.echo("✅ WeChat configuration validated successfully")

        except Exception as e:
            raise ConfigError(f"Failed to load WeChat configuration: {e}")

        # Create WeChat article
        from .models.wechat import WeChatArticle

        wechat_article = WeChatArticle(
            title=article_metadata.get("title", ""),
            content=html_content,
            digest=article_metadata.get("digest", ""),
            author=article_metadata.get("author", "知韵VoxPoetica"),
            poem_title=article_metadata.get("poem_title", ""),
            poet_name=article_metadata.get("poet_name", ""),
            source_lang=article_metadata.get("source_lang", ""),
            target_lang=article_metadata.get("target_lang", ""),
            translation_workflow_id=article_metadata.get("workflow_id", ""),
            translation_json_path=article_metadata.get("source_json_path", ""),
        )

        # Add cover image information if available
        cover_image_name = article_metadata.get("cover_image")
        if cover_image_name:
            cover_image_path = directory / cover_image_name
            if cover_image_path.exists():
                wechat_article.cover_image_path = str(cover_image_path)
                wechat_article.show_cover_pic = True
                click.echo(f"📸 Cover image found: {cover_image_name}")
            else:
                click.echo(f"⚠️ Cover image specified but not found: {cover_image_path}")

        # Initialize WeChat client
        from .services.wechat import WeChatClient
        from .models.wechat import WeChatConfig

        # Extract WeChat API config from the complete config and convert to WeChatConfig object
        wechat_api_config_dict = wechat_config.get("wechat")
        wechat_api_config = WeChatConfig(**wechat_api_config_dict)
        wechat_client = WeChatClient(wechat_api_config)

        # Test connection
        click.echo("🔗 Testing WeChat API connection...")
        if not await wechat_client.test_connection():
            raise WeChatError("WeChat API connection test failed")

        # Handle cover image upload if present
        thumb_media_id = None
        show_cover_pic = False

        # Priority 1: Use cover image from metadata (configured path)
        if wechat_article.cover_image_path and wechat_article.show_cover_pic:
            try:
                click.echo(
                    f"📸 Uploading cover image from metadata: {Path(wechat_article.cover_image_path).name}"
                )
                thumb_media_id = await wechat_client.upload_thumb_image(
                    wechat_article.cover_image_path
                )
                show_cover_pic = True
                click.echo(
                    f"✅ Cover image uploaded successfully (Media ID: {thumb_media_id})"
                )

                # Update WeChat article with cover image info
                wechat_article.thumb_media_id = thumb_media_id
                wechat_article.show_cover_pic = show_cover_pic

            except Exception as e:
                click.echo(
                    f"⚠️  Warning: Failed to upload cover image from metadata: {e}"
                )

        # Priority 2: Fallback to file detection in directory (legacy method)
        elif not wechat_article.cover_image_path:
            cover_images = validation_result["files"].get("cover_images")
            if cover_images and verbose:
                click.echo(
                    f"📸 Found {len(cover_images)} cover image(s) via file detection"
                )

            if cover_images:
                preferred_cover = validation_result["files"]["preferred_cover"]
                try:
                    click.echo(
                        f"📸 Uploading cover image via file detection: {preferred_cover.name}"
                    )
                    thumb_media_id = await wechat_client.upload_thumb_image(
                        str(preferred_cover)
                    )
                    show_cover_pic = True
                    click.echo(
                        f"✅ Cover image uploaded successfully (Media ID: {thumb_media_id})"
                    )

                    # Update WeChat article with cover image info
                    wechat_article.thumb_media_id = thumb_media_id
                    wechat_article.show_cover_pic = show_cover_pic

                except Exception as e:
                    click.echo(f"⚠️  Warning: Failed to upload cover image: {e}")
        else:
            click.echo("📝 No cover image configured")
            click.echo("📝 Proceeding without cover image...")
            if verbose:
                import traceback

                traceback.print_exc()

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
                "article_path": str(validation_result["files"]["html_path"]),
                "metadata_path": str(validation_result["files"]["metadata_path"]),
                "directory": str(directory),
                "published_at": (
                    draft_response.created_at.isoformat()
                    if draft_response.created_at
                    else None
                ),
                "created_at": datetime.now().isoformat(),
            }

            publish_result_path = directory / "publish_result.json"
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
