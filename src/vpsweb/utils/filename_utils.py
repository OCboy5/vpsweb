"""
Filename utilities for VPSWeb output management.

This module provides utilities for generating clean, descriptive filenames
for translation outputs, including sanitization and metadata extraction.
"""

import re
from typing import Any, Dict, Optional


def sanitize_filename_component(component: str, max_length: int = 30) -> str:
    """
    Sanitize a component for use in filenames.

    Args:
        component: The string component to sanitize
        max_length: Maximum length for the component

    Returns:
        Sanitized string safe for filename use
    """
    if not component:
        return "unknown"

    # Remove or replace problematic characters
    sanitized = re.sub(
        r'[<>:"/\\|?*]', "", component
    )  # Remove invalid filename chars
    sanitized = re.sub(
        r"\s+", "_", sanitized
    )  # Replace whitespace with underscores
    sanitized = re.sub(
        r"[^\w\-_]", "", sanitized
    )  # Remove any remaining non-alphanumeric chars except hyphen and underscore

    # Remove leading/trailing underscores and hyphens
    sanitized = sanitized.strip("_-")

    # Ensure it's not empty after sanitization
    if not sanitized:
        return "unknown"

    # Truncate to max_length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_-")

    return sanitized.lower()


def extract_poet_and_title(
    poem_text: str, metadata: Optional[Dict[str, Any]] = None
) -> tuple[str, str]:
    """
    Extract poet and title from poem text or metadata.

    Args:
        poem_text: The original poem text
        metadata: Optional metadata dictionary

    Returns:
        Tuple of (poet_name, title_name)
    """
    # First try to extract from metadata
    if metadata:
        poet = (
            metadata.get("author")
            or metadata.get("poet")
            or metadata.get("poet_name")
        )
        title = (
            metadata.get("title")
            or metadata.get("poem_title")
            or metadata.get("poem_name")
        )

        if poet and title:
            return sanitize_filename_component(
                poet
            ), sanitize_filename_component(title)
        elif poet:
            return sanitize_filename_component(poet), "untitled"
        elif title:
            return "unknown", sanitize_filename_component(title)

    # Try to extract from poem text patterns
    lines = poem_text.strip().split("\n")

    # Look for common patterns: "Title\nAuthor: Name" or "Author\n\nTitle"
    if len(lines) >= 2:
        # Pattern 1: Author: Name on second line
        if (
            "作者" in lines[1]
            or "author" in lines[1].lower()
            or "by" in lines[1].lower()
        ):
            title = lines[0] if lines[0].strip() else "untitled"
            author_line = lines[1]
            # Extract name after common patterns
            author_match = re.search(
                r"(?:作者|author|by)[:：]\s*(.+)", author_line, re.IGNORECASE
            )
            if author_match:
                poet = author_match.group(1).strip()
            else:
                poet = author_line.strip()
            return sanitize_filename_component(
                poet
            ), sanitize_filename_component(title)

        # Pattern 2: First line might be title, second might be author
        elif any(keyword in lines[1] for keyword in ["作者", "author", "by"]):
            title = lines[0] if lines[0].strip() else "untitled"
            poet = lines[1].strip()
            return sanitize_filename_component(
                poet
            ), sanitize_filename_component(title)

    # Fallback: use first line as title, unknown author
    title = lines[0] if lines and lines[0].strip() else "untitled"
    return "unknown", sanitize_filename_component(title)


def generate_translation_filename(
    poet: str,
    title: str,
    source_lang: str,
    target_lang: str,
    timestamp: str,
    workflow_id: str,
    workflow_mode: Optional[str] = None,
    file_format: str = "json",
    is_log: bool = False,
) -> str:
    """
    Generate a descriptive filename for translation outputs.

    Args:
        poet: Sanitized poet name
        title: Sanitized poem title
        source_lang: Source language
        target_lang: Target language
        timestamp: Timestamp string (YYYYMMDD_HHMMSS)
        workflow_id: Workflow ID (will be truncated to last 8 chars)
        workflow_mode: Optional workflow mode
        file_format: File format (json, md)
        is_log: Whether this is a log file (for markdown)

    Returns:
        Generated filename
    """
    # Get hash suffix from workflow_id
    hash_suffix = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

    # Build components
    components = []

    # Add poet and title
    if poet != "unknown":
        components.append(poet)
    components.append(title)

    # Add languages
    components.append(f"{source_lang.lower()}_{target_lang.lower()}")

    # Add workflow mode for JSON files
    if file_format == "json" and workflow_mode:
        components.append(workflow_mode)

    # Add timestamp
    components.append(timestamp)

    # Add hash
    components.append(hash_suffix)

    # Add log suffix for log files (no "translation_" prefix)
    if is_log:
        components.append("log")

    # Join components (no "translation_" prefix)
    filename = f"{'_'.join(components)}.{file_format}"

    return filename


def generate_legacy_filename(
    source_lang: str,
    target_lang: str,
    timestamp: str,
    workflow_id: str,
    workflow_mode: Optional[str] = None,
    file_format: str = "json",
    is_log: bool = False,
) -> str:
    """
    Generate filename using legacy scheme (fallback).

    Args:
        source_lang: Source language
        target_lang: Target language
        timestamp: Timestamp string
        workflow_id: Workflow ID
        workflow_mode: Optional workflow mode
        file_format: File format
        is_log: Whether this is a log file

    Returns:
        Generated filename using legacy scheme
    """
    hash_suffix = workflow_id[-8:] if len(workflow_id) > 8 else workflow_id

    if is_log:
        return f"translation_log_{source_lang.lower()}_{target_lang.lower()}_{timestamp}_{hash_suffix}.{file_format}"
    else:
        if workflow_mode:
            return f"translation_{workflow_mode}_{timestamp}_{hash_suffix}.{file_format}"
        else:
            return f"translation_{timestamp}_{hash_suffix}.{file_format}"
