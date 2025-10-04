#!/usr/bin/env python3
"""
Vox Poetica Studio Web - Basic Usage Example

This example demonstrates how to use the vpsweb translation system programmatically.
"""

import asyncio
from pathlib import Path
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.utils.config_loader import load_config


async def basic_translation_example():
    """Example of basic translation workflow"""

    # Load configuration
    config = load_config("config/default.yaml")

    # Create translation input
    poem_text = """The fog comes
on little cat feet.

It sits looking
over harbor and city
on silent haunches
and then moves on."""

    translation_input = TranslationInput(
        original_poem=poem_text,
        source_lang="English",
        target_lang="Chinese"
    )

    # Initialize workflow
    workflow = TranslationWorkflow(config)

    # Execute translation
    print("Starting translation workflow...")
    result = await workflow.execute(translation_input)

    # Display results
    print(f"Translation completed in {result.duration_seconds:.2f} seconds")
    print(f"Total tokens used: {result.total_tokens}")
    print(f"Final translation:\n{result.revised_translation.translation}")


if __name__ == "__main__":
    # Note: This is a placeholder example. The actual implementation
    # will be completed when the core components are ready.
    print("VPSWeb Basic Usage Example")
    print("Note: Full implementation pending core component development")