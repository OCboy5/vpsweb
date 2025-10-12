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
    ):
        """
        Initialize article generator with configuration.

        Args:
            config: Article generation configuration
            providers_config: Provider configurations for LLM factory (from CompleteConfig.providers)
        """
        self.config = config

        # Initialize LLM services if providers config is available
        if providers_config:
            self.llm_factory = LLMFactory(providers_config)
            self.prompt_service = PromptService()
            logger.info("Article generator initialized with LLM synthesis capabilities")
        else:
            self.llm_factory = None
            self.prompt_service = None
            logger.info(
                "Article generator initialized without LLM synthesis capabilities"
            )

    def generate_from_translation(
        self,
        translation_json_path: str,
        output_dir: Optional[str] = None,
        author: Optional[str] = None,
        digest: Optional[str] = None,
    ) -> ArticleGenerationResult:
        """
        Generate WeChat article from translation JSON file.

        Args:
            translation_json_path: Path to translation JSON file
            output_dir: Output directory for generated files
            author: Article author name
            digest: Custom digest for article

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
                output_dir = f"outputs/wechat_articles/{metadata.slug}"
            else:
                output_dir = Path(output_dir) / metadata.slug

            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate HTML content
            html_content = self._generate_html_content(translation_data, metadata)

            # Create WeChat article
            article = WeChatArticle(
                title=f"【知韵译诗】{metadata.poem_title}（{metadata.poet_name}）",
                content=html_content,
                digest=digest or self._generate_digest(translation_data),
                author=author or metadata.author,
                poem_title=metadata.poem_title,
                poet_name=metadata.poet_name,
                source_lang=metadata.source_lang,
                target_lang=metadata.target_lang,
                translation_workflow_id=metadata.workflow_id,
                translation_json_path=translation_json_path,
            )

            # Save files
            html_path = output_dir / "article.html"
            metadata_path = output_dir / "metadata.json"
            markdown_path = output_dir / "article.md"

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
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)

            # Generate and save markdown preview
            markdown_content = self._generate_markdown_content(
                translation_data, metadata
            )
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Create result
            result = ArticleGenerationResult(
                article=article,
                html_path=str(html_path),
                metadata_path=str(metadata_path),
                markdown_path=str(markdown_path),
                slug=metadata.slug,
                output_directory=str(output_dir),
                status=WeChatArticleStatus.GENERATED,
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

            # Look for author line
            if "作者：" in line:
                # Extract poet name
                poet_name = line.split("作者：")[1].strip()
                continue

            # Look for series index in title
            match = re.search(r"[第其其其]([一二三四五六七八九十]+)", line)
            if match:
                series_index = match.group(1)

            # First non-empty line that's not author is likely the title
            if not poem_title and "作者：" not in line:
                poem_title = line.strip()
                # Remove common prefixes
                poem_title = re.sub(
                    r"^[第其其其][一二三四五六七八九十]+\s*", "", poem_title
                )
                poem_title = poem_title.strip()

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
        if source_lang.lower() in ["chinese", "中文", "zh"]:
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
        self, translation_data: Dict[str, Any], metadata: WeChatArticleMetadata
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
            translation_text = self._extract_translation_text(final_translation)

            # Generate HTML using author-approved template
            html_content = f"""<section style="font-size: 16px; line-height: 1.8; color: #222;">
<h1 style="font-size: 22px; margin: 12px 0;">【知韵译诗】{poem_title}（{poet_name}）</h1>
<small style="color: #666; display: block; margin-bottom: 16px;">作者：施知韵VoxPoeticaStudio</small>
<hr>

<h2 style="font-size: 18px; margin: 16px 0 8px;">原诗</h2>
<div style="font-family: serif; margin: 8px 0; white-space: pre-wrap;">{poem_text}</div>

<h2 style="font-size: 18px; margin: 16px 0 8px;">英译</h2>
<div style="font-family: serif; margin: 8px 0; white-space: pre-wrap;">{translation_text}</div>

<h2 style="font-size: 18px; margin: 16px 0 8px;">译注</h2>
<div style="margin: 8px 0; color: #555;">
{self._generate_translation_notes_section(translation_data, metadata)}
</div>

<hr>
<small style="color: #666; display: block; margin-top: 16px;">
{self.config.copyright_text}
</small>
</section>"""

            return html_content

        except Exception as e:
            raise ArticleGeneratorError(f"Error generating HTML content: {e}")

    def _extract_poem_text(self, original_poem: str) -> str:
        """Extract clean poem text from original poem."""
        lines = original_poem.strip().split("\n")
        poem_lines = []

        for line in lines:
            line = line.strip()
            # Skip author line
            if "作者：" in line:
                continue
            # Skip empty lines
            if not line:
                continue
            # Skip title line if it's the first line
            if line == lines[0].strip() and len(poem_lines) == 0:
                continue
            poem_lines.append(line)

        return "\n".join(poem_lines)

    def _extract_translation_text(self, final_translation: str) -> str:
        """Extract clean translation text."""
        lines = final_translation.strip().split("\n")
        translation_lines = []

        for line in lines:
            line = line.strip()
            # Skip title and author lines
            if "By " in line and any(
                name in line for name in ["Tao Yuanming", "Li Bai", "Du Fu"]
            ):
                continue
            # Skip empty lines
            if not line:
                continue
            translation_lines.append(line)

        return "\n".join(translation_lines)

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

            if len(digest_text) > 110:
                digest_text = digest_text[:107] + "..."

            return digest_text[:120]  # Ensure max length

        except Exception as e:
            logger.warning(f"Error generating digest: {e}")
            return "诗歌翻译作品，展现中英文学之美，传递文化精髓。"

    def _generate_markdown_content(
        self, translation_data: Dict[str, Any], metadata: WeChatArticleMetadata
    ) -> str:
        """Generate markdown preview of the article."""
        congregated = translation_data.get("congregated_output", {})
        original_poem = congregated.get("original_poem", "")
        final_translation = congregated.get("revised_translation", "")

        poem_text = self._extract_poem_text(original_poem)
        translation_text = self._extract_translation_text(final_translation)

        markdown_content = f"""# 【知韵译诗】{metadata.poem_title}（{metadata.poet_name}）

*作者：施知韵VoxPoeticaStudio*

---

## 原诗

```
{poem_text}
```

## 英译

```
{translation_text}
```

## 译注

<!-- Translation notes will be generated here by LLM -->
翻译笔记将通过LLM生成并插入此处...

---

*{self.config.copyright_text}*
"""

        return markdown_content

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

            # Run async synthesis in sync context using asyncio.run
            return asyncio.run(
                self._synthesize_translation_notes_async(translation_data, metadata)
            )

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
            editor_assessment = congregated.get("editor_assessment", "")
            translation_suggestions = congregated.get("translation_suggestions", "")

            # Determine workflow mode for prompt selection
            workflow_mode = getattr(metadata, "workflow_mode", "hybrid") or "hybrid"

            # Create input for LLM (similar to existing workflow)
            # Extract data from the proper structure
            initial_translation_data = translation_data.get("initial_translation", {})
            editor_review_data = translation_data.get("editor_review", {})
            revised_translation_data = translation_data.get("revised_translation", {})

            synthesis_input = {
                "original_poem": original_poem,
                "final_translation": final_translation,
                "revised_translation_notes": revised_translation_data.get(
                    "revised_translation_notes", ""
                ),
                "editor_suggestions": editor_review_data.get("editor_suggestions", ""),
                "initial_translation_notes": initial_translation_data.get(
                    "initial_translation_notes", ""
                ),
                "poet_name": metadata.poet_name,
                "poem_title": metadata.poem_title,
            }

            # Select appropriate prompt template
            if workflow_mode == "reasoning":
                prompt_template = "wechat_article_notes_reasoning"
            else:
                prompt_template = "wechat_article_notes_nonreasoning"

            # Render prompt template using PromptService
            system_prompt, user_prompt = self.prompt_service.render_prompt(
                prompt_template, synthesis_input
            )
            # WeChat translation notes uses user prompt only
            formatted_prompt = user_prompt

            # Select LLM provider (prefer reasoning models for synthesis)
            provider_name = "deepseek"  # Use deepseek for Chinese translation notes

            # Get provider from factory
            provider = self.llm_factory.get_provider(provider_name)
            if not provider:
                raise ArticleGeneratorError(
                    f"LLM provider '{provider_name}' not available"
                )

            # Get model name from provider configuration
            provider_config = self.llm_factory.providers_config.providers[provider_name]
            model_name = provider_config.default_model or provider_config.models[0]

            # Generate response using LLM
            logger.info(
                f"Synthesizing translation notes using {provider_name} with model {model_name}"
            )
            response = await provider.generate(
                messages=[{"role": "user", "content": formatted_prompt}],
                model=model_name,
                temperature=0.7,
                max_tokens=2048,
            )

            # Parse XML response using existing XML parser
            from .xml_parser import WeChatXMLParser

            xml_parser = WeChatXMLParser()

            try:
                notes_data = xml_parser.parse_wechat_response(response.content)
                translation_notes = notes_data.get("wechat_translation_notes", {})

                # Format HTML output
                digest = translation_notes.get("digest", "")
                notes = translation_notes.get("notes", [])

                html_parts = []
                if digest:
                    html_parts.append(f"<p><strong>摘要：</strong>{digest}</p>")

                if notes:
                    html_parts.append("<ul>")
                    for note in notes:
                        html_parts.append(f"<li>{note}</li>")
                    html_parts.append("</ul>")

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
                    html_parts = []
                    if digest:
                        html_parts.append(f"<p><strong>摘要：</strong>{digest}</p>")

                    if notes:
                        html_parts.append("<ul>")
                        for note in notes:
                            html_parts.append(f"<li>{note}</li>")
                        html_parts.append("</ul>")

                    if html_parts:
                        return "\n".join(html_parts)
                    else:
                        return f"<p><em>翻译笔记：</em><br>{content}</p>"

                except Exception as fallback_error:
                    logger.error(f"Fallback parsing also failed: {fallback_error}")
                    return f"<p><em>翻译笔记：</em><br>{response.content}</p>"

        except Exception as e:
            logger.error(f"Translation notes synthesis failed: {e}")
            return f"<p><em>翻译笔记生成失败：{str(e)}</em></p>"
