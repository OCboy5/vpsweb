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
    lines = source_text.split("\n")
    labeled_lines = []
    line_counter = 1

    for line in lines:
        if line.strip():  # Non-empty line
            labeled_line = f"[L{line_counter}] {line}"
            labeled_lines.append(labeled_line)
            line_counter += 1
        else:
            # Preserve empty lines (for stanza breaks)
            labeled_lines.append("")

    return "\n".join(labeled_lines)


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
    raw_lines = source_text.split("\n")
    # 2) Trim each line
    trimmed = [line.strip() for line in raw_lines]
    # 3) Keep only non-empty lines
    non_empty = [line for line in trimmed if line]
    return len(non_empty)


def detect_stanza_structure(source_text: str) -> str:
    """Analyze poem text to determine stanza structure.

    Detects stanza breaks based on empty lines. Only treats completely empty
    lines (after stripping) as stanza breaks, ignoring indentation and whitespace.

    Args:
        source_text: The poem text to analyze

    Returns:
        Stanza structure description in format like:
        - "2 stanzas of 9+9" (two stanzas of 9 lines each)
        - "3 stanzas of 4+4+5" (three stanzas of specified lengths)
        - "continuous" (no stanza breaks detected)

    Examples:
        >>> detect_stanza_structure("Line 1\\nLine 2\\n\\nLine 3\\nLine 4")
        '2 stanzas of 2+2'
        >>> detect_stanza_structure("Single stanza poem")
        'continuous'
    """
    lines = source_text.split("\n")
    stanza_lengths = []
    current_stanza_length = 0

    for line in lines:
        # Check if this is a completely empty line (after stripping)
        if line.strip():
            # Non-empty line - part of current stanza
            current_stanza_length += 1
        else:
            # Empty line - stanza break
            if current_stanza_length > 0:
                stanza_lengths.append(current_stanza_length)
                current_stanza_length = 0
            # Skip consecutive empty lines - don't add empty stanzas

    # Add the last stanza if there are remaining lines
    if current_stanza_length > 0:
        stanza_lengths.append(current_stanza_length)

    # Determine result format
    if len(stanza_lengths) <= 1:
        return "continuous"
    else:
        stanza_counts = "+".join(map(str, stanza_lengths))
        return f"{len(stanza_lengths)} stanzas of {stanza_counts}"
