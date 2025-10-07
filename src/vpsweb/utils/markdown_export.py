"""
Markdown export utilities for VPSWeb translation results.

This module provides utilities to export translation results and logs
to well-formatted markdown files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..models.translation import TranslationOutput


class MarkdownExporter:
    """Exporter for translation results to markdown format."""

    def __init__(self, base_output_dir: str = "outputs"):
        """
        Initialize the markdown exporter.

        Args:
            base_output_dir: Base directory for all outputs
        """
        self.base_output_dir = Path(base_output_dir)
        self.markdown_dir = self.base_output_dir / "markdown"
        self.markdown_dir.mkdir(parents=True, exist_ok=True)

    def generate_filename(
        self,
        source_lang: str,
        target_lang: str,
        timestamp: str,
        workflow_id: str,
        is_log: bool = False,
    ) -> str:
        """
        Generate filename using Option A naming scheme.

        Args:
            source_lang: Source language
            target_lang: Target language
            timestamp: Timestamp string
            workflow_id: Workflow ID (hash)
            is_log: Whether this is a log file

        Returns:
            Generated filename
        """
        # Extract last 8 characters of workflow_id for shorter filename
        hash_suffix = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

        # Format: translation_{source}_{target}_{timestamp}_{hash}.md
        # or: translation_log_{source}_{target}_{timestamp}_{hash}.md
        if is_log:
            return f"translation_log_{source_lang.lower()}_{target_lang.lower()}_{timestamp}_{hash_suffix}.md"
        else:
            return f"translation_{source_lang.lower()}_{target_lang.lower()}_{timestamp}_{hash_suffix}.md"

    def export_final_translation(self, translation_output: TranslationOutput) -> str:
        """
        Export final translation to markdown format.

        Args:
            translation_output: Complete translation output

        Returns:
            Path to created markdown file
        """
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.generate_filename(
            source_lang=translation_output.input.source_lang,
            target_lang=translation_output.input.target_lang,
            timestamp=timestamp,
            workflow_id=translation_output.workflow_id,
            is_log=False,
        )

        file_path = self.markdown_dir / filename

        # Generate markdown content
        content = self._format_final_translation_markdown(translation_output)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def export_full_log(self, translation_output: TranslationOutput) -> str:
        """
        Export full translation log to markdown format.

        Args:
            translation_output: Complete translation output

        Returns:
            Path to created markdown file
        """
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.generate_filename(
            source_lang=translation_output.input.source_lang,
            target_lang=translation_output.input.target_lang,
            timestamp=timestamp,
            workflow_id=translation_output.workflow_id,
            is_log=True,
        )

        file_path = self.markdown_dir / filename

        # Generate markdown content
        content = self._format_full_log_markdown(translation_output)

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def export_both(self, translation_output: TranslationOutput) -> Dict[str, str]:
        """
        Export both final translation and full log.

        Args:
            translation_output: Complete translation output

        Returns:
            Dictionary with file paths
        """
        final_translation_path = self.export_final_translation(translation_output)
        full_log_path = self.export_full_log(translation_output)

        return {"final_translation": final_translation_path, "full_log": full_log_path}

    def _format_final_translation_markdown(
        self, translation_output: TranslationOutput
    ) -> str:
        """
        Format final translation as markdown.

        Args:
            translation_output: Complete translation output

        Returns:
            Formatted markdown content
        """
        content = []

        # Header
        content.append(
            f"# Poetry Translation: {translation_output.input.source_lang} → {translation_output.input.target_lang}"
        )
        content.append("")

        # Separator
        content.append("---")
        content.append("")

        # Original Poem
        content.append("## 📖 Original Poem")
        content.append("")
        content.append(f"**Language:** {translation_output.input.source_lang}")
        content.append("")
        content.append("```")
        content.append(translation_output.input.original_poem)
        content.append("```")
        content.append("")

        # Final Translation
        content.append("## 🎭 Final Translation")
        content.append("")
        content.append(f"**Language:** {translation_output.input.target_lang}")
        content.append("")
        content.append("```")
        content.append(translation_output.revised_translation.revised_translation)
        content.append("```")

        return "\n".join(content)

    def _format_full_log_markdown(self, translation_output: TranslationOutput) -> str:
        """
        Format full translation log as markdown.

        Args:
            translation_output: Complete translation output

        Returns:
            Formatted markdown content
        """
        content = []

        # Header
        content.append(f"# Translation Workflow Log")
        content.append("")

        # Summary
        content.append("## 📊 Summary")
        content.append("")
        content.append(
            f"- **Total Duration:** {translation_output.duration_seconds:.2f} seconds"
        )
        content.append(f"- **Total Tokens:** {translation_output.total_tokens}")
        content.append(
            f"- **Editor Suggestions:** {len(translation_output.editor_review.editor_suggestions)} characters"
        )
        content.append("")

        # Separator
        content.append("---")
        content.append("")

        # Step 1: Initial Translation
        content.append("## 🔄 Step 1: Initial Translation")
        content.append("")
        content.append(
            f"**Model:** {translation_output.initial_translation.model_info}"
        )
        content.append(
            f"**Tokens Used:** {translation_output.initial_translation.tokens_used}"
        )
        content.append(
            f"**Timestamp:** {translation_output.initial_translation.timestamp}"
        )
        content.append("")

        content.append("### 📖 Original Poem")
        content.append("")
        content.append("```")
        content.append(translation_output.input.original_poem)
        content.append("```")
        content.append("")

        content.append("### 🎭 Initial Translation")
        content.append("")
        content.append("```")
        content.append(translation_output.initial_translation.initial_translation)
        content.append("```")
        content.append("")

        content.append("### 📝 Initial Translation Notes")
        content.append("")
        content.append(translation_output.initial_translation.initial_translation_notes)
        content.append("")

        # Step 2: Editor Review
        content.append("---")
        content.append("")
        content.append("## 👁️ Step 2: Editor Review")
        content.append("")
        content.append(f"**Model:** {translation_output.editor_review.model_info}")
        content.append(
            f"**Tokens Used:** {translation_output.editor_review.tokens_used}"
        )
        content.append(f"**Timestamp:** {translation_output.editor_review.timestamp}")
        content.append("")

        content.append("### 🔍 Editor Suggestions")
        content.append("")
        content.append(translation_output.editor_review.editor_suggestions)
        content.append("")

        # Step 3: Final Revision
        content.append("---")
        content.append("")
        content.append("## ✍️ Step 3: Final Revision")
        content.append("")
        content.append(
            f"**Model:** {translation_output.revised_translation.model_info}"
        )
        content.append(
            f"**Tokens Used:** {translation_output.revised_translation.tokens_used}"
        )
        content.append(
            f"**Timestamp:** {translation_output.revised_translation.timestamp}"
        )
        content.append("")

        content.append("### 🎭 Final Translation")
        content.append("")
        content.append("```")
        content.append(translation_output.revised_translation.revised_translation)
        content.append("```")
        content.append("")

        content.append("### 📝 Revision Notes")
        content.append("")
        content.append(translation_output.revised_translation.revised_translation_notes)
        content.append("")

        return "\n".join(content)
