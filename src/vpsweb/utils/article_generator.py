"""
Article generation utility for Vox Poetica Studio Web.

This module handles conversion from translation JSON to WeChat-compatible HTML articles,
including metadata extraction, HTML rendering, and file management.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging
import asyncio
import shutil

from jinja2 import Environment, FileSystemLoader

from ..models.wechat import (
    WeChatArticle,
    WeChatArticleMetadata,
    ArticleGenerationResult,
    ArticleGenerationConfig,
    WeChatArticleStatus,
)
from ..models.translation import TranslationOutput
from ..services.llm.factory import LLMFactory
from ..services.prompts import PromptService
from .logger import get_logger
from ..services.config import get_config_facade, ConfigFacade

logger = get_logger(__name__)


class ArticleGeneratorError(Exception):
    """Exception raised for article generation errors."""

    pass


class ArticleGenerator:
    """
    Generates WeChat articles from translation JSON outputs.

    Handles metadata extraction, HTML rendering with author-approved templates,
    and file management for WeChat article generation workflow.
    """

    def __init__(
        self,
        config: ArticleGenerationConfig,
        providers_config: Optional[Dict[str, Any]] = None,
        wechat_llm_config: Optional[Dict[str, Any]] = None,
        system_config: Optional[Dict[str, Any]] = None,
        config_facade: Optional[ConfigFacade] = None,
    ):
        """
        Initialize article generator with configuration.

        Args:
            config: Article generation configuration
            providers_config: Legacy Provider configurations for LLM factory (deprecated, use config_facade instead)
            wechat_llm_config: WeChat LLM configuration for translation notes (deprecated, use config_facade instead)
            system_config: System configuration with default values and paths (deprecated, use config_facade instead)
            config_facade: New ConfigFacade instance for configuration access
        """
        self.config = config

        # Support both legacy and ConfigFacade patterns
        if config_facade is not None:
            self._config_facade = config_facade
            self._using_facade = True
            # Get WeChat configurations from ConfigFacade (new task template structure)
            try:
                # Try to get reasoning model config for WeChat notes
                self.wechat_llm_config = config_facade.get_wechat_task_config("reasoning")
            except (ValueError, RuntimeError):
                # Fallback to legacy method
                self.wechat_llm_config = config_facade.models.get_wechat_translation_notes_config()
            # Use providers from legacy config for compatibility
            actual_providers_config = providers_config
        else:
            # Try to get from global ConfigFacade
            try:
                self._config_facade = get_config_facade()
                self._using_facade = True
                try:
                    # Try to get reasoning model config for WeChat notes
                    self.wechat_llm_config = self._config_facade.get_wechat_task_config("reasoning")
                except (ValueError, RuntimeError):
                    # Fallback to legacy method
                    self.wechat_llm_config = self._config_facade.models.get_wechat_translation_notes_config()
                actual_providers_config = providers_config
                logger.info("ArticleGenerator using global ConfigFacade with task templates")
            except RuntimeError:
                # Fallback to legacy pattern
                self._using_facade = False
                self._config_facade = None
                self.wechat_llm_config = wechat_llm_config
                actual_providers_config = providers_config
                logger.info("ArticleGenerator using legacy configuration pattern")

        self.system_config = system_config or {}

        # Initialize HTML template system
        self._init_template_system()

        # Initialize LLM services if providers config is available
        if actual_providers_config:
            self.llm_factory = LLMFactory(actual_providers_config)
            self.prompt_service = PromptService()
            self.llm_metrics = None  # Store metrics from last LLM call
            self._cached_translation_notes = (
                None  # Cache translation notes to avoid duplicate calls
            )
            logger.info("Article generator initialized with LLM synthesis capabilities")
        else:
            self.llm_factory = None
            self.prompt_service = None
            self.llm_metrics = None
            self._cached_translation_notes = None
            logger.info(
                "Article generator initialized without LLM synthesis capabilities"
            )

    def _init_template_system(self) -> None:
        """Initialize the Jinja2 template system for HTML rendering."""
        try:
            # Get the template directory path
            current_dir = Path(__file__).parent.parent.parent.parent
            template_dir = current_dir / "config" / "html_templates" / "wechat_articles"

            if not template_dir.exists():
                raise ArticleGeneratorError(
                    f"Template directory not found: {template_dir}"
                )

            # Initialize Jinja2 environment
            self.template_env = Environment(
                loader=FileSystemLoader(str(template_dir)), autoescape=True
            )

            # Test loading the default template
            default_template = self.config.article_template or "default"
            self.template_env.get_template(f"{default_template}.html")

            logger.info(
                f"HTML template system initialized with template directory: {template_dir}"
            )

            # Validate default cover image availability
            self._validate_default_cover_image(current_dir)

        except Exception as e:
            raise ArticleGeneratorError(f"Failed to initialize template system: {e}")

    def _validate_default_cover_image(self, project_root: Path) -> None:
        """
        Validate that the default cover image file exists and is accessible.

        Args:
            project_root: Path to the project root directory

        Raises:
            ArticleGeneratorError: If default cover image validation fails
        """
        try:
            default_cover_path = project_root / self.config.default_cover_image_path

            if not default_cover_path.exists():
                logger.warning(
                    f"⚠️ Default cover image not found at: {default_cover_path}"
                )
                logger.warning(
                    "💡 To fix: Place a cover image at the configured path or update the path in config/wechat.yaml"
                )
                return  # Don't raise error, just warn since fallback to None is handled

            # Check if it's a valid image file (basic validation)
            if not default_cover_path.is_file():
                logger.warning(
                    f"⚠️ Default cover path exists but is not a file: {default_cover_path}"
                )
                return

            # Check file size (should be reasonable for an image)
            file_size = default_cover_path.stat().st_size
            if file_size == 0:
                logger.warning(f"⚠️ Default cover image is empty: {default_cover_path}")
                return

            logger.info(
                f"✅ Default cover image validated: {default_cover_path} ({file_size} bytes)"
            )

        except Exception as e:
            logger.warning(f"⚠️ Error validating default cover image: {e}")
            # Don't raise error since the system can work without a default cover image

    def generate_from_translation(
        self,
        translation_json_path: str,
        output_dir: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        dry_run: bool = False,
    ) -> ArticleGenerationResult:
        """
        Generate WeChat article from translation JSON file.

        Args:
            translation_json_path: Path to translation JSON file
            output_dir: Output directory for generated files
            author: Article author name
            digest: Custom digest for article
            dry_run: Generate article without external API calls

        Returns:
            ArticleGenerationResult with generated article information

        Raises:
            ArticleGeneratorError: If generation fails
        """
        try:
            # Load translation JSON
            translation_data = self._load_translation_json(translation_json_path)

            # Extract metadata
            metadata = self._extract_metadata(translation_data, translation_json_path)

            # Determine output directory and slug
            if output_dir is None:
                # Get default wechat articles directory from config
                wechat_articles_dir = self.system_config.get("storage", {}).get(
                    "wechat_articles_dir", "outputs/wechat_articles"
                )
                output_dir = f"{wechat_articles_dir}/{metadata.slug}"
            else:
                output_dir = Path(output_dir) / metadata.slug

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Handle cover image fallback logic
            cover_image_abs_path = self._handle_cover_image_fallback(output_dir)

            # Pre-generate translation notes to get the LLM digest
            llm_digest = None
            if self.config.include_translation_notes and not dry_run:
                # This will trigger the LLM call and populate self.llm_metrics with digest
                translation_notes_section = self._generate_translation_notes_section(
                    translation_data, metadata
                )

                if self.llm_metrics and "digest" in self.llm_metrics:
                    llm_digest = self.llm_metrics["digest"]
                    logger.info(
                        f"✅ LLM-generated digest extracted: {llm_digest[:50]}..."
                    )
                else:
                    logger.warning(
                        f"⚠️ LLM metrics available but no digest found: {type(self.llm_metrics)}"
                    )
                    if self.llm_metrics:
                        logger.warning(
                            f"⚠️ Available keys in llm_metrics: {list(self.llm_metrics.keys())}"
                        )
            elif self.config.include_translation_notes and dry_run:
                # Create mock LLM metrics for dry-run testing
                self.llm_metrics = {
                    "tokens_used": 1500,
                    "prompt_tokens": 800,
                    "completion_tokens": 700,
                    "duration": 3.5,
                    "cost": 0.025,
                    "provider": "mock_provider",
                    "model": "mock_model",
                    "model_type": "non_reasoning",
                    "digest": "This is a mock digest for dry-run testing. It provides a concise overview of the poem translation and analysis.",
                }
                llm_digest = self.llm_metrics["digest"]

                # Create mock translation notes for dry-run with inline styling for bullet points
                mock_translation_notes = """
                <div class="translation-notes">
                    <h3>译注解析 (Dry Run Mode)</h3>
                    <p><strong>主题赏析：</strong>这首诗描绘了诗人回归自然田园后，探访荒废故居时的所见所感。通过对昔日居民遗迹的观察，表达了人生无常、世事变迁的主题。</p>

                    <p><strong>翻译难点：</strong></p>
                    <div style="padding-left: 10px;">
                        <p style="margin: 0 0 8px 0; color: #444444; font-size: 15px; line-height: 1.5;">•&nbsp;&nbsp;<em>久去山澤遊</em> - "Long gone from hills and marshes"：处理时间跨度和空间转换</p>
                        <p style="margin: 0 0 8px 0; color: #444444; font-size: 15px; line-height: 1.5;">•&nbsp;&nbsp;<em>浪莽林野娛</em> - "delight in roaming wilds of wood and field"：传达自然之乐</p>
                        <p style="margin: 0 0 8px 0; color: #444444; font-size: 15px; line-height: 1.5;">•&nbsp;&nbsp;<em>井竈有遺處</em> - "Well and stove leave traces"：意象的具体化处理</p>
                    </div>

                    <p><strong>文化内涵：</strong>诗中体现了中国传统文人"物是人非"的感慨，以及对生命轮回、归于虚无的哲学思考。翻译时需保持这种深沉的文化底蕴。</p>
                </div>
                """
                self._cached_translation_notes = mock_translation_notes

            # Generate HTML content (pass cached translation notes to avoid duplicate LLM calls)
            html_content = self._generate_html_content(
                translation_data,
                metadata,
                self._cached_translation_notes,
                cover_image_abs_path,
            )

            # Determine final digest (prioritize LLM-generated)
            final_digest = (
                llm_digest or digest or self._generate_digest(translation_data)
            )

            # Create WeChat article with LLM digest if available
            article = WeChatArticle(
                title=f"【知韵译诗】{metadata.poem_title}（{metadata.poet_name}）",
                content=html_content,
                digest=final_digest,
                author=author or metadata.author,
                poem_title=metadata.poem_title,
                poet_name=metadata.poet_name,
                source_lang=metadata.source_lang,
                target_lang=metadata.target_lang,
                translation_workflow_id=metadata.workflow_id,
                translation_json_path=translation_json_path,
            )

            # Store cover image information for WeChat API usage
            if cover_image_abs_path:
                article.cover_image_path = cover_image_abs_path
                article.show_cover_pic = True  # Enable cover picture display

            # Save files
            html_path = output_dir / "article.html"
            metadata_path = output_dir / "metadata.json"

            # Save HTML
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Save metadata
            metadata_dict = {
                "title": article.title,
                "slug": metadata.slug,
                "author": article.author,
                "digest": article.digest,
                "source_json_path": translation_json_path,
                "created_at": metadata.created_at.isoformat(),
                "poem_title": metadata.poem_title,
                "poet_name": metadata.poet_name,
                "source_lang": metadata.source_lang,
                "target_lang": metadata.target_lang,
                "workflow_id": metadata.workflow_id,
                "cover_image": (
                    Path(cover_image_abs_path).name if cover_image_abs_path else None
                ),  # Store only filename for reference
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)

            # Create result
            result = ArticleGenerationResult(
                article=article,
                html_path=str(html_path),
                metadata_path=str(metadata_path),
                slug=metadata.slug,
                output_directory=str(output_dir),
                status=WeChatArticleStatus.GENERATED,
                llm_metrics=self.llm_metrics,
            )

            logger.info(f"Article generated successfully: {result.slug}")
            return result

        except Exception as e:
            logger.error(f"Article generation failed: {e}")
            raise ArticleGeneratorError(f"Failed to generate article: {e}")

    def _load_translation_json(self, json_path: str) -> Dict[str, Any]:
        """Load and validate translation JSON file."""
        json_path = Path(json_path)
        if not json_path.exists():
            raise ArticleGeneratorError(f"Translation JSON file not found: {json_path}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise ArticleGeneratorError(f"Invalid JSON in file {json_path}: {e}")
        except Exception as e:
            raise ArticleGeneratorError(
                f"Error loading translation JSON {json_path}: {e}"
            )

    def _handle_cover_image_fallback(self, output_dir: Path) -> Optional[str]:
        """
        Handle cover image fallback logic.

        1. First check if local cover image exists in the output directory (using configured filename)
        2. If not, reference the default cover image from configured path without copying
        3. Return the appropriate cover image path for upload

        Args:
            output_dir: Path to the output directory for the article

        Returns:
            Absolute path to the cover image file for upload, or None if no image available
        """
        try:
            # Get local cover image filename from configuration
            local_cover_filename = self.config.default_local_cover_image_name

            # Local cover image path in the article directory
            local_cover_path = output_dir / local_cover_filename

            # Default cover image path from configuration
            project_root = Path(__file__).parent.parent.parent.parent
            default_cover_path = project_root / self.config.default_cover_image_path

            if local_cover_path.exists():
                # Local cover image exists, use it
                logger.info(f"✅ Using local cover image: {local_cover_path}")
                return str(local_cover_path)
            elif default_cover_path.exists():
                # Fallback to default cover image without copying (storage efficient)
                logger.info(f"📸 Using default cover image: {default_cover_path}")
                return str(default_cover_path)
            else:
                # No cover image available
                logger.warning(
                    f"⚠️ No cover image available (neither local nor default found at {default_cover_path})"
                )
                return None

        except Exception as e:
            logger.error(f"❌ Error handling cover image fallback: {e}")
            return None

    def _extract_metadata(
        self, translation_data: Dict[str, Any], json_path: str
    ) -> WeChatArticleMetadata:
        """Extract metadata from translation data."""
        try:
            # Get basic workflow information
            workflow_id = translation_data.get("workflow_id", "")
            input_data = translation_data.get("input", {})
            source_lang = input_data.get("source_lang", "")
            target_lang = input_data.get("target_lang", "")

            # Extract poem and poet information
            original_poem = input_data.get("original_poem", "")
            poem_title, poet_name, series_index = self._parse_poem_header(original_poem)

            # Generate slug
            slug = self._generate_slug(poet_name, poem_title, source_lang)

            # Get workflow mode if available
            workflow_mode = None
            if "full_log" in translation_data:
                # Extract workflow mode from full_log
                full_log = translation_data["full_log"]
                if "HYBRID MODE" in full_log:
                    workflow_mode = "hybrid"
                elif "REASONING MODE" in full_log:
                    workflow_mode = "reasoning"
                elif "NON_REASONING MODE" in full_log:
                    workflow_mode = "non_reasoning"

            metadata = WeChatArticleMetadata(
                poem_title=poem_title,
                poet_name=poet_name,
                series_index=series_index,
                source_lang=source_lang,
                target_lang=target_lang,
                workflow_id=workflow_id,
                workflow_mode=workflow_mode,
                source_json_path=str(json_path),
                slug=slug,
            )

            return metadata

        except Exception as e:
            raise ArticleGeneratorError(f"Error extracting metadata: {e}")

    def _parse_poem_header(self, original_poem: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse poem header to extract title, poet, and series index.

        Args:
            original_poem: Original poem text

        Returns:
            Tuple of (poem_title, poet_name, series_index)
        """
        lines = original_poem.strip().split("\n")

        poem_title = ""
        poet_name = ""
        series_index = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Look for author line with Chinese prefix
            if "作者：" in line:
                # Extract poet name
                poet_name = line.split("作者：")[1].strip()
                continue

            # Look for series index in title
            match = re.search(r"[第其其其]([一二三四五六七八九十]+)", line)
            if match:
                series_index = match.group(1)

            # First non-empty line is likely the title
            if not poem_title:
                poem_title = line.strip()
                # Remove common prefixes
                poem_title = re.sub(
                    r"^[第其其其][一二三四五六七八九十]+\s*", "", poem_title
                )
                poem_title = poem_title.strip()
                continue

            # Second non-empty line (after title) is likely the poet name if no Chinese prefix found
            if not poet_name and i == 1:
                poet_name = line.strip()
                continue

        # Fallback values if parsing failed
        if not poem_title:
            poem_title = "无题"
        if not poet_name:
            poet_name = "佚名"

        return poem_title, poet_name, series_index

    def _generate_slug(
        self, poet_name: str, poem_title: str, source_lang: str = ""
    ) -> str:
        """Generate URL-friendly slug in format: poetname-poemtitle-YYYYMMDD."""
        # Generate date
        date_str = datetime.now().strftime("%Y%m%d")

        # If source language is Chinese, use Chinese characters directly
        if source_lang.lower() in ["chinese", "中文", "zh", "zh-cn", "zh_cn"]:
            # Clean Chinese characters (remove special characters but keep Chinese text)
            poet_clean = re.sub(r"[^\u4e00-\u9fff\w]", "", poet_name)
            title_clean = re.sub(r"[^\u4e00-\u9fff\w]", "", poem_title)
        else:
            # Transliterate to basic ASCII for non-Chinese languages
            poet_ascii = self._transliterate_to_ascii(poet_name)
            title_ascii = self._transliterate_to_ascii(poem_title)

            # Clean and combine
            poet_clean = re.sub(r"[^a-zA-Z0-9]", "", poet_ascii.lower())
            title_clean = re.sub(r"[^a-zA-Z0-9]", "", title_ascii.lower())

        # Combine parts
        if poet_clean and title_clean:
            slug = f"{poet_clean}-{title_clean}-{date_str}"
        elif poet_clean:
            slug = f"{poet_clean}-poem-{date_str}"
        else:
            slug = f"poem-{date_str}"

        return slug

    def _transliterate_to_ascii(self, text: str) -> str:
        """
        Transliterate Chinese text to basic ASCII.

        Simple transliteration for common characters and patterns.
        In a production environment, this could use a proper transliteration library.
        """
        # Basic transliteration map for common poets/titles
        transliterations = {
            "陶渊明": "taoyuanming",
            "李白": "libai",
            "杜甫": "dufu",
            "苏轼": "sushi",
            "王维": "wangwei",
            "白居易": "baijuyi",
            "歸園田居": "guiyuantianju",
            "静夜思": "jingyesi",
            "春望": "chunwang",
            "将进酒": "jiangjinjiu",
            "水调歌头": "shuidiaogotou",
        }

        # Try exact match first
        if text in transliterations:
            return transliterations[text]

        # Try partial matches
        for chinese, ascii_equiv in transliterations.items():
            if chinese in text:
                text = text.replace(chinese, ascii_equiv)

        # Remove remaining non-ASCII characters
        return re.sub(r"[^\x00-\x7F]", "", text)

    def _generate_html_content(
        self,
        translation_data: Dict[str, Any],
        metadata: WeChatArticleMetadata,
        cached_translation_notes: Optional[str] = None,
        cover_image_path: Optional[str] = None,
    ) -> str:
        """Generate WeChat-compatible HTML content."""
        try:
            # Extract poem content
            congregated = translation_data.get("congregated_output", {})
            original_poem = congregated.get("original_poem", "")
            final_translation = congregated.get("revised_translation", "")

            # Parse poem sections
            poem_title, poet_name, series_index = (
                metadata.poem_title,
                metadata.poet_name,
                metadata.series_index,
            )
            poem_text = self._extract_poem_text(original_poem)
            target_lang_title, target_lang_poet, translation_text = (
                self._extract_translation_text(final_translation)
            )

            # If no target poet was found in translation text, try to get it from translation data metadata
            if not target_lang_poet:
                # Try to get translated poet name from translation data metadata
                translation_metadata = translation_data.get("metadata", {})
                target_lang_poet = translation_metadata.get(
                    "refined_translated_poet_name"
                ) or translation_metadata.get("translated_poet_name")

            # Create bilingual title and poet name variables
            source_lang = metadata.source_lang.lower()
            target_lang = metadata.target_lang.lower()

            # Determine language-appropriate display
            if source_lang in ["chinese", "中文", "zh", "zh-cn", "zh_cn"]:
                source_title = poem_title
                # Clean up poet name by removing any existing prefixes
                if poet_name.startswith("作者："):
                    source_poet = poet_name[3:]  # Remove "作者：" prefix
                else:
                    source_poet = poet_name
                source_author_prefix = "作者："
            else:
                source_title = poem_title
                # Clean up poet name by removing any existing prefixes
                if poet_name.startswith("By "):
                    source_poet = poet_name[3:]  # Remove "By " prefix
                else:
                    source_poet = poet_name
                source_author_prefix = "By "

            if target_lang in ["english", "en", "英文"]:
                # Use extracted target language title and poet (for English format)
                target_title = target_lang_title if target_lang_title else poem_title
                # Clean up poet name by removing any existing prefixes
                extracted_poet = target_lang_poet if target_lang_poet else poet_name
                if extracted_poet.startswith("By "):
                    target_poet = extracted_poet[3:]  # Remove "By " prefix
                else:
                    target_poet = extracted_poet
                target_author_prefix = "By "
            elif target_lang in ["chinese", "中文", "zh", "zh-cn", "zh_cn"]:
                # For Chinese target languages
                target_title = target_lang_title if target_lang_title else poem_title
                # Clean up poet name by removing any existing prefixes
                extracted_poet = target_lang_poet if target_lang_poet else poet_name
                if extracted_poet.startswith("作者："):
                    target_poet = extracted_poet[3:]  # Remove "作者：" prefix
                else:
                    target_poet = extracted_poet
                target_author_prefix = "作者："
            else:
                # For other target languages, use the extracted title and translated poet name if available
                target_title = target_lang_title if target_lang_title else poem_title
                target_poet = target_lang_poet if target_lang_poet else poet_name
                target_author_prefix = (
                    "作者："  # Default to Chinese prefix for other languages
                )

            # Prepare template variables
            # Use cached translation notes if available to avoid duplicate LLM calls
            if cached_translation_notes is not None:
                translation_notes_section = cached_translation_notes
            elif self._cached_translation_notes is not None:
                translation_notes_section = self._cached_translation_notes
            else:
                translation_notes_section = self._generate_translation_notes_section(
                    translation_data, metadata
                )

            template_vars = {
                "poem_title": poem_title,
                "poet_name": poet_name,
                "poem_text": poem_text,
                "translation_text": translation_text,
                "translation_notes_section": translation_notes_section,
                "copyright_text": self.config.copyright_text,
                # Bilingual variables
                "source_title": source_title,
                "source_poet": source_poet,
                "source_author_prefix": source_author_prefix,
                "target_title": target_title,
                "target_poet": target_poet,
                "target_author_prefix": target_author_prefix,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }

            # Load and render template
            template_name = self.config.article_template or "default"
            template = self.template_env.get_template(f"{template_name}.html")
            html_content = template.render(**template_vars)

            return html_content

        except Exception as e:
            raise ArticleGeneratorError(f"Error generating HTML content: {e}")

    def _extract_poem_text(self, original_poem: str) -> str:
        """Extract clean poem text from original poem."""
        lines = original_poem.strip().split("\n")
        poem_lines = []

        for i, line in enumerate(lines):
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip title line if it's the first line
            if i == 0:
                continue
            # Skip author line (second line) - could be "作者：Name" or just "Name"
            if i == 1:
                continue
            poem_lines.append(line)

        return "\n".join(poem_lines)

    def _extract_translation_text(self, final_translation: str) -> tuple[str, str, str]:
        """Extract target language title, poet name, and clean translation text.

        Returns:
            Tuple of (target_lang_title, target_lang_poet_name, clean_translation_text)
        """
        lines = final_translation.strip().split("\n")
        translation_lines = []
        target_lang_title = ""
        target_lang_poet = ""

        for i, line in enumerate(lines):
            line = line.strip()

            # Extract target language title from first non-empty line
            if i == 0 and line:
                target_lang_title = line
                continue

            # Extract target language poet name from second line (after title)
            # This could be "By Poet Name" or just "Poet Name" depending on formatting
            if i == 1 and line:
                target_lang_poet = line
                continue

            # Skip translation lines that happen to start with "By " but are not poet attribution
            if (
                line.startswith("By ") and len(line.split()) > 3
            ):  # Likely "By error I fell..." type of line
                # This is a translation line, not poet attribution, so treat it as translation content
                translation_lines.append(line)
                continue

            # Skip empty lines
            if not line:
                continue

            # Add to translation text
            translation_lines.append(line)

        clean_translation = "\n".join(translation_lines)
        return target_lang_title, target_lang_poet, clean_translation

    def _generate_digest(self, translation_data: Dict[str, Any]) -> str:
        """Generate automatic digest from translation data."""
        try:
            congregated = translation_data.get("congregated_output", {})
            final_translation = congregated.get("revised_translation", "")

            # Extract first few lines of translation
            lines = final_translation.strip().split("\n")[:4]
            digest_lines = [
                line.strip() for line in lines if line.strip() and "By " not in line
            ]

            digest_text = " ".join(digest_lines)

            # Clean and limit length
            digest_text = re.sub(r"\s+", " ", digest_text)

            # Ensure digest fits within 115 characters (with safety buffer for 120 limit)
            if len(digest_text) > 115:
                # Truncate to fit within 115 characters
                digest_text = digest_text[:112] + "..."

            return digest_text

        except Exception as e:
            logger.warning(f"Error generating digest: {e}")
            # Get default digest from system config
            default_digest = self.system_config.get("system", {}).get(
                "default_digest", "诗歌翻译作品，展现中英文学之美，传递文化精髓。"
            )
            return default_digest

    def _generate_translation_notes_section(
        self, translation_data: Dict[str, Any], metadata: WeChatArticleMetadata
    ) -> str:
        """
        Generate translation notes section using LLM synthesis.

        Args:
            translation_data: Translation workflow data
            metadata: Article metadata

        Returns:
            HTML-formatted translation notes
        """
        # If no LLM services available, return placeholder
        if not self.llm_factory or not self.prompt_service:
            return "<!-- Translation notes synthesis not available --><em>翻译笔记 synthesis 功能未配置</em>"

        try:
            # Check if translation notes synthesis is disabled
            if not self.config.include_translation_notes:
                return "<!-- Translation notes disabled --><em>翻译笔记功能已禁用</em>"

            # Use cached result if available
            if self._cached_translation_notes is not None:
                # If we have cached notes but no metrics, extract metrics from cache
                if self.llm_metrics is None:
                    logger.debug(
                        "Found cached notes but no metrics - need to regenerate"
                    )
                    # Clear cache to force regeneration and get metrics
                    self._cached_translation_notes = None
                else:
                    return self._cached_translation_notes

            # Run async synthesis in sync context using asyncio.run
            result = asyncio.run(
                self._synthesize_translation_notes_async(translation_data, metadata)
            )

            # Cache the result
            self._cached_translation_notes = result
            return result

        except Exception as e:
            logger.error(f"Failed to synthesize translation notes: {e}")
            return f"<!-- Translation notes synthesis failed: {e} --><em>翻译笔记生成失败</em>"

    async def _synthesize_translation_notes_async(
        self, translation_data: Dict[str, Any], metadata: WeChatArticleMetadata
    ) -> str:
        """
        Asynchronously synthesize translation notes using LLM.

        Follows the same pattern as the existing translation workflow.
        """
        try:
            # Extract data for synthesis
            congregated = translation_data.get("congregated_output", {})
            original_poem = congregated.get("original_poem", "")
            final_translation = congregated.get("revised_translation", "")

            # Extract notes from congregated output where they actually exist
            initial_translation_notes = congregated.get("initial_translation_notes", "")
            editor_suggestions = congregated.get("editor_suggestions", "")
            revised_translation_notes = congregated.get("revised_translation_notes", "")

            synthesis_input = {
                "original_poem": original_poem,
                "revised_translation": final_translation,
                "revised_translation_notes": revised_translation_notes,
                "editor_suggestions": editor_suggestions,
                "initial_translation_notes": initial_translation_notes,
                "poet_name": metadata.poet_name,
                "poem_title": metadata.poem_title,
            }

            # Get model configuration based on model_type
            model_type = getattr(self.config, "model_type", "reasoning")
            logger.info(
                f"Using model type: {model_type} for translation notes synthesis"
            )

            # Use WeChat LLM configuration if available, otherwise fallback to hardcoded values
            if (
                self.wechat_llm_config
                and "models" in self.wechat_llm_config
                and model_type in self.wechat_llm_config["models"]
            ):
                model_config = self.wechat_llm_config["models"][model_type]
                prompt_template = model_config.get(
                    "prompt_template", f"wechat_article_notes_{model_type}"
                )
                default_provider = model_config.get(
                    "provider",
                    "tongyi" if model_type == "non_reasoning" else "deepseek",
                )
                default_model = model_config.get(
                    "model",
                    (
                        "qwen-plus-latest"
                        if model_type == "non_reasoning"
                        else "deepseek-reasoner"
                    ),
                )
                default_temp = model_config.get(
                    "temperature", 0.3 if model_type == "non_reasoning" else 0.1
                )
                default_max_tokens = model_config.get("max_tokens", 8192)
            else:
                # Fallback to hardcoded values
                if model_type == "reasoning":
                    prompt_template = "wechat_article_notes_reasoning"
                    default_provider = "deepseek"
                    default_model = "deepseek-reasoner"
                    default_temp = 0.1
                    default_max_tokens = 8192
                else:  # non_reasoning
                    prompt_template = "wechat_article_notes_nonreasoning"
                    default_provider = "tongyi"
                    default_model = "qwen-plus-latest"
                    default_temp = 0.3
                    default_max_tokens = 8192

            # Fall back to legacy prompt_template if available
            prompt_template = getattr(self.config, "prompt_template", prompt_template)

            # Render prompt template using PromptService
            system_prompt, user_prompt = self.prompt_service.render_prompt(
                prompt_template, synthesis_input
            )
            # WeChat translation notes uses user prompt only
            formatted_prompt = user_prompt

            # Get provider and model from configuration or defaults
            provider_name = default_provider
            model_name = default_model
            temperature = default_temp
            max_tokens = default_max_tokens

            # Try to get provider from factory
            provider = self.llm_factory.get_provider(provider_name)
            if not provider:
                # Fallback to any available provider
                logger.warning(
                    f"Provider {provider_name} not available, trying fallback"
                )
                for available_provider in self.llm_factory.providers_config.providers:
                    provider = self.llm_factory.get_provider(available_provider)
                    if provider:
                        provider_name = available_provider
                        provider_config = self.llm_factory.providers_config.providers[
                            available_provider
                        ]
                        model_name = (
                            provider_config.default_model or provider_config.models[0]
                        )
                        break

                if not provider:
                    raise ArticleGeneratorError("No LLM providers available")

            # Generate response using LLM
            import time

            start_time = time.time()

            logger.info(
                f"Synthesizing translation notes using {provider_name} with model {model_name} (type: {model_type})"
            )
            response = await provider.generate(
                messages=[{"role": "user", "content": formatted_prompt}],
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            end_time = time.time()
            duration = end_time - start_time

            # Calculate cost using the same method as workflow
            cost = self._calculate_step_cost(
                provider_name,
                model_name,
                response.prompt_tokens,
                response.completion_tokens,
            )

            # Parse XML response using existing XML parser
            from .xml_parser import WeChatXMLParser

            xml_parser = WeChatXMLParser()

            try:
                translation_notes = xml_parser.parse_translation_notes(response.content)

                # Extract digest and notes from TranslationNotes object
                digest = translation_notes.digest
                notes = translation_notes.notes

                # Store metrics for display
                metrics = {
                    "tokens_used": response.tokens_used,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "duration": duration,
                    "cost": cost,
                    "provider": provider_name,
                    "model": model_name,
                    "model_type": model_type,
                    "digest": digest,  # Add LLM-generated digest
                }

                # Store metrics for access by the main generation method
                self.llm_metrics = metrics

                # Format HTML output
                import html

                html_parts = []
                if digest:
                    # Unescape HTML entities
                    clean_digest = html.unescape(digest)
                    html_parts.append(
                        f'<p style="margin: 0 0 0px 0;"><strong>摘要：</strong>{clean_digest}</p>'
                    )

                if notes:
                    html_parts.append('<div style="padding-left: 10px;">')
                    for note in notes:
                        # Unescape HTML entities in notes
                        clean_note = html.unescape(note)
                        html_parts.append(
                            f'<p style="margin: 0 0 8px 0; color: #444444; font-size: 15px; line-height: 1.5;">•&nbsp;&nbsp;{clean_note}</p>'
                        )
                    html_parts.append("</div>")

                return (
                    "\n".join(html_parts)
                    if html_parts
                    else "<p><em>翻译笔记生成完成，但内容为空</em></p>"
                )

            except Exception as parse_error:
                logger.warning(f"Failed to parse XML response: {parse_error}")
                # Try manual extraction as fallback
                try:
                    import re

                    content = response.content

                    # Extract digest
                    digest_match = re.search(
                        r"digest:\s*(.+?)(?=\nnotes:|$)", content, re.DOTALL
                    )
                    digest = digest_match.group(1).strip() if digest_match else ""

                    # Extract notes
                    notes_match = re.search(
                        r"notes:\s*(.+?)(?=</wechat_translation_notes>|$)",
                        content,
                        re.DOTALL,
                    )
                    notes_text = notes_match.group(1).strip() if notes_match else ""

                    # Parse bullet points
                    notes = []
                    for line in notes_text.split("\n"):
                        line = line.strip()
                        if line.startswith("•") or line.startswith("-"):
                            notes.append(line[1:].strip())

                    # Format HTML output
                    import html

                    html_parts = []
                    if digest:
                        # Unescape HTML entities
                        clean_digest = html.unescape(digest)
                        html_parts.append(
                            f"<p><strong>摘要：</strong>{clean_digest}</p>"
                        )

                    if notes:
                        html_parts.append('<div style="padding-left: 10px;">')
                        for note in notes:
                            # Unescape HTML entities in notes
                            clean_note = html.unescape(note)
                            html_parts.append(
                                f'<p style="margin: 0 0 8px 0; color: #444444; font-size: 15px; line-height: 1.5;">•&nbsp;&nbsp;{clean_note}</p>'
                            )
                        html_parts.append("</div>")

                    if html_parts:
                        # Ensure digest meets length requirements (80-115 characters with safety buffer)
                        if len(digest) < 80:
                            # Pad with a concise suffix
                            suffix = " 展现诗歌翻译的艺术与哲学深度。"
                            digest = digest + suffix
                        elif len(digest) > 115:
                            # Truncate to fit within 115 characters (with safety buffer for 120 limit)
                            digest = digest[:112] + "..."

                        # Store metrics for display in fallback path too
                        metrics = {
                            "tokens_used": response.tokens_used,
                            "prompt_tokens": response.prompt_tokens,
                            "completion_tokens": response.completion_tokens,
                            "duration": duration,
                            "cost": cost,
                            "provider": provider_name,
                            "model": model_name,
                            "model_type": model_type,
                            "digest": digest,  # Add LLM-generated digest
                        }
                        self.llm_metrics = metrics

                        return "\n".join(html_parts)
                    else:
                        return f"<p><em>翻译笔记：</em><br>{content}</p>"

                except Exception as fallback_error:
                    logger.error(f"Fallback parsing also failed: {fallback_error}")
                    return f"<p><em>翻译笔记：</em><br>{response.content}</p>"

        except Exception as e:
            logger.error(f"Translation notes synthesis failed: {e}")
            return f"<p><em>翻译笔记生成失败：{str(e)}</em></p>"

    def _calculate_step_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> Optional[float]:
        """Calculate cost for a single step using the same method as workflow."""
        try:
            # Get pricing from configuration
            if self.llm_factory and hasattr(self.llm_factory, "providers_config"):
                providers_config = self.llm_factory.providers_config

                if hasattr(providers_config, "pricing") and providers_config.pricing:
                    pricing = providers_config.pricing

                    # Get pricing for this provider and model
                    if provider in pricing and model in pricing[provider]:
                        model_pricing = pricing[provider][model]
                        # Pricing is RMB per 1K tokens
                        input_cost = (input_tokens / 1000) * model_pricing.get(
                            "input", 0
                        )
                        output_cost = (output_tokens / 1000) * model_pricing.get(
                            "output", 0
                        )
                        return input_cost + output_cost

            logger.warning(
                f"Failed to calculate cost for {provider}/{model}: No pricing info available"
            )
            return None

        except Exception as e:
            logger.warning(f"Failed to calculate cost for {provider}/{model}: {e}")
