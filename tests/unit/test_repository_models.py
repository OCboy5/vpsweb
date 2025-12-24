"""
Essential Repository Model Tests for VPSWeb v0.7.0

Tests only critical model constraints and relationships.
Excludes framework features, performance tests, and extensive field validation.
"""

import uuid

from sqlalchemy.orm import Session

from src.vpsweb.repository.models import (
    BackgroundBriefingReport,
    HumanNote,
    Poem,
    Translation,
)
from src.vpsweb.repository.schemas import TranslatorType


class TestEssentialModelConstraints:
    """Essential model constraint and relationship tests."""

    def test_poem_model_constraints(self, db_session: Session):
        """Test essential Poem model constraints."""
        # Test valid poem creation
        poem = Poem(
            id=str(uuid.uuid4())[:26],
            poet_name="Carl Sandburg",
            poem_title="Fog",
            source_language="English",
            original_text="The fog comes on little cat feet.",
        )
        db_session.add(poem)
        db_session.commit()

        # Verify poem was created
        retrieved = db_session.get(Poem, poem.id)
        assert retrieved.poet_name == "Carl Sandburg"
        assert retrieved.poem_title == "Fog"

    def test_translation_model_constraints(self, db_session: Session):
        """Test essential Translation model constraints."""
        # Create poem first
        poem = Poem(
            id=str(uuid.uuid4())[:26],
            poet_name="Carl Sandburg",
            poem_title="Fog",
            source_language="English",
            original_text="The fog comes on little cat feet.",
        )
        db_session.add(poem)
        db_session.commit()

        # Test valid translation creation
        translation = Translation(
            id=str(uuid.uuid4())[:26],
            poem_id=poem.id,
            target_language="Chinese",
            translated_text="雾来了\n踏着猫的小脚。",
            translator_type=TranslatorType.AI,
        )
        db_session.add(translation)
        db_session.commit()

        # Verify relationship
        retrieved_translation = db_session.get(Translation, translation.id)
        assert retrieved_translation.poem_id == poem.id
        assert retrieved_translation.poem.poet_name == "Carl Sandburg"

    def test_bbr_poem_relationship(self, db_session: Session):
        """Test BBR-poem relationship."""
        # Create poem
        poem = Poem(
            id=str(uuid.uuid4())[:26],
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        db_session.add(poem)
        db_session.commit()

        # Create BBR
        bbr = BackgroundBriefingReport(
            id=str(uuid.uuid4())[:26],
            poem_id=poem.id,
            content="Test BBR content",
        )
        db_session.add(bbr)
        db_session.commit()

        # Verify relationship
        retrieved_bbr = db_session.get(BackgroundBriefingReport, bbr.id)
        assert retrieved_bbr.poem_id == poem.id
        assert retrieved_bbr.poem.poet_name == "Test Poet"

    def test_human_note_relationship(self, db_session: Session):
        """Test human note relationship with translation."""
        # Create poem and translation
        poem = Poem(
            id=str(uuid.uuid4())[:26],
            poet_name="Test Poet",
            poem_title="Test Poem",
            source_language="English",
            original_text="Test content",
        )
        db_session.add(poem)
        db_session.commit()

        translation = Translation(
            id=str(uuid.uuid4())[:26],
            poem_id=poem.id,
            target_language="Chinese",
            translated_text="测试翻译",
            translator_type=TranslatorType.AI,
        )
        db_session.add(translation)
        db_session.commit()

        # Create human note
        note = HumanNote(
            id=str(uuid.uuid4())[:26],
            translation_id=translation.id,
            note_text="Test human note",
        )
        db_session.add(note)
        db_session.commit()

        # Verify relationship
        retrieved_note = db_session.get(HumanNote, note.id)
        assert retrieved_note.translation_id == translation.id
        assert retrieved_note.translation.translated_text == "测试翻译"
        assert retrieved_note.note_text == "Test human note"
