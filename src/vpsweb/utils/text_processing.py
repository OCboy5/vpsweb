"""
Text processing utilities for VPSWeb.

This module provides utilities for processing poem text,
including line numbering and structural analysis.
"""

def add_line_labels(source_text: str) -> str:
    """Add [L#] labels to effective lines for reliable referencing.

    Args:
        source_text: The poem text to add line labels to

    Returns:
        Text with [L#] labels prefixed to each non-empty line

    Examples:
        >>> add_line_labels("Line 1\\n\\nLine 2")
        '[L1] Line 1\\n\\n[L2] Line 2'
    """
    lines = source_text.split('\n')
    labeled_lines = []
    line_counter = 1

    for line in lines:
        if line.strip():  # Non-empty line
            labeled_line = f"[L{line_counter}] {line}"
            labeled_lines.append(labeled_line)
            line_counter += 1
        else:
            # Preserve empty lines (for stanza breaks)
            labeled_lines.append('')

    return '\n'.join(labeled_lines)


def count_effective_lines(source_text: str) -> int:
    """Count effective (non-empty) lines in poem text.

    Args:
        source_text: The poem text to analyze

    Returns:
        Number of effective (non-empty) lines

    Examples:
        >>> count_effective_lines("Line 1\\n\\nLine 2")
        2
    """
    # 1) Split on '\n'
    raw_lines = source_text.split('\n')
    # 2) Trim each line
    trimmed = [line.strip() for line in raw_lines]
    # 3) Keep only non-empty lines
    non_empty = [line for line in trimmed if line]
    return len(non_empty)