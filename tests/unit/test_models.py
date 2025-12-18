"""
Unit tests for the translation models.

These tests verify the Pydantic models that define the data structures
used throughout the VPSWeb translation system.
"""

import pytest
from pydantic import ValidationError

from src.vpsweb.models.translation import (EditorReview, InitialTranslation,
                                           Language, RevisedTranslation,
                                           TranslationInput)


class TestTranslationInput:
    """Test the TranslationInput model."""

    def test_valid_translation_input(self):
        """Test creating a valid TranslationInput."""
        input_data = TranslationInput(
            original_poem="The fog comes on little cat feet.",
            source_lang=Language.ENGLISH,
            target_lang=Language.CHINESE,
        )
        assert input_data.original_poem == "The fog comes on little cat feet."
        assert input_data.source_lang == Language.ENGLISH
        assert input_data.target_lang == Language.CHINESE

    def test_language_validation_business_rules(self):
        """Test language enum validation for business rules."""
        # Test that same language translation fails (if business rule)
        with pytest.raises(ValidationError):
            TranslationInput(
                original_poem="Test poem",
                source_lang=Language.ENGLISH,
                target_lang=Language.ENGLISH,  # Same language should fail
            )

    def test_empty_poem_validation(self):
        """Test validation for empty poem content."""
        with pytest.raises(ValidationError):
            TranslationInput(
                original_poem="",  # Empty should fail
                source_lang=Language.ENGLISH,
                target_lang=Language.CHINESE,
            )

    def test_whitespace_only_poem(self):
        """Test validation for whitespace-only poem content."""
        with pytest.raises(ValidationError):
            TranslationInput(
                original_poem="   \n\t  ",  # Whitespace only should fail
                source_lang=Language.ENGLISH,
                target_lang=Language.CHINESE,
            )


class TestInitialTranslation:
    """Test the InitialTranslation model."""

    def test_valid_initial_translation(self):
        """Test creating a valid InitialTranslation."""
        translation = InitialTranslation(
            initial_translation="雾来了\n踏着猫的小脚。",
            initial_translation_notes="Captures the gentle, stealthy imagery.",
            translated_poem_title="Fog",
            translated_poet_name="Carl Sandburg",
            model_info={"provider": "openai", "model": "gpt-3.5-turbo"},
            tokens_used=150,
        )
        assert translation.initial_translation == "雾来了\n踏着猫的小脚。"
        assert translation.tokens_used == 150

    def test_minimal_initial_translation(self):
        """Test creating InitialTranslation with minimal fields."""
        translation = InitialTranslation(
            initial_translation="Test translation",
            translated_poem_title="Test Title",
        )
        assert translation.initial_translation == "Test translation"
        assert translation.translated_poem_title == "Test Title"


class TestEditorReview:
    """Test the EditorReview model."""

    def test_valid_editor_review(self):
        """Test creating a valid EditorReview."""
        review = EditorReview(
            editor_suggestions="1. Add more imagery\n2. Improve rhythm",
            editor_notes="Good start but needs refinement",
            edited_translation="雾来了\n踏着猫的小脚。",
            translated_poem_title="Fog",
            translated_poet_name="Carl Sandburg",
            model_info={"provider": "openai", "model": "gpt-3.5-turbo"},
            tokens_used=100,
        )
        assert len(review.editor_suggestions) > 0
        assert review.tokens_used == 100

    def test_empty_editor_suggestions(self):
        """Test EditorReview with empty suggestions."""
        review = EditorReview(
            editor_suggestions="",
            translated_poem_title="Test",
        )
        assert review.editor_suggestions == ""


class TestRevisedTranslation:
    """Test the RevisedTranslation model."""

    def test_valid_revised_translation(self):
        """Test creating a valid RevisedTranslation."""
        revised = RevisedTranslation(
            revised_translation="雾来了\n踏着猫的小脚。\n\n修改版",
            revision_notes="Improved rhythm and imagery",
            translated_poem_title="Fog (Revised)",
            translated_poet_name="Carl Sandburg",
            model_info={"provider": "openai", "model": "gpt-3.5-turbo"},
            tokens_used=200,
        )
        assert len(revised.revised_translation) > 0
