#!/usr/bin/env python3
"""
Demo script for VPSWeb Repository Service Layer v0.3.1

Demonstrates the usage of the repository service layer with sample data.
"""

import sys
import os
from pathlib import Path

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

# Change to repository directory for proper package imports
os.chdir(Path(__file__).parent)

from database import create_session, init_db
from service import create_repository_service
from schemas import (
    PoemCreate, TranslationCreate, AILogCreate, HumanNoteCreate,
    TranslatorType, WorkflowMode
)


def demo_repository_service():
    """Demonstrate repository service functionality"""
    print("🎭 VPSWeb Repository Service Layer Demo v0.3.1")
    print("=" * 50)

    # Initialize database
    print("\n📊 Initializing database...")
    init_db()
    session = create_session()
    service = create_repository_service(session)
    print("✓ Database initialized")

    # Create sample poems
    print("\n📝 Creating sample poems...")
    poem1_data = PoemCreate(
        poet_name="陶渊明",
        poem_title="歸園田居·其一",
        source_language="zh",
        original_text="少無適俗韻，性本愛丘山。誤落塵網中，一去三十年。羈鳥戀舊林，池魚思故淵。開荒南野際，守拙歸園田。方宅十餘畝，草屋八九間。榆柳蔭後簷，桃李羅堂前。曖曖遠人村，依依墟里煙。狗吠深巷中，雞鳴桑樹顛。戶庭無塵雜，虛室有餘閒。久在樊籠裡，復得返自然。",
        metadata_json='{"dynasty": "東晉", "theme": "田園", "form": "五言詩"}'
    )

    poem2_data = PoemCreate(
        poet_name="李白",
        poem_title="靜夜思",
        source_language="zh",
        original_text="床前明月光，疑是地上霜。舉頭望明月，低頭思故鄉。",
        metadata_json='{"dynasty": "唐", "theme": "思鄉", "form": "五言絕句"}'
    )

    poem1 = service.create_poem(poem1_data)
    poem2 = service.create_poem(poem2_data)
    print(f"✓ Created poems: {poem1.poem_title}, {poem2.poem_title}")

    # Create translations
    print("\n🌍 Creating translations...")
    trans1_data = TranslationCreate(
        poem_id=poem1.id,
        translator_type=TranslatorType.AI,
        translator_info="gpt-4",
        target_language="en",
        translated_text="From youth I had no taste for common ways, my nature was to love hills and mountains. By mistake I fell into the worldly net, and for thirty years was gone. A caged bird longs for its old forest, a pond fish thinks of its former deep. I open wasteland at the southern wilds, keeping my simplicity and returning to garden and field. A homestead of ten-plus acres, thatched cottage of eight or nine rooms. Elms and willows shade the back eaves, peach and plum are arrayed before the hall. Faintly visible distant villages, lingering smoke from deserted courtyards. A dog barks in the deep lane, a rooster crows atop the mulberry tree. Courtyard and gate have no dust or clutter, the empty room has ample leisure. Long having been in a cage, I return again to nature.",
        quality_rating=4
    )

    trans2_data = TranslationCreate(
        poem_id=poem2.id,
        translator_type=TranslatorType.HUMAN,
        translator_info="David Hinton",
        target_language="en",
        translated_text="A splash of white on the floor before my bed—moonlight? Frost? I lift my head to gaze at the bright moon, then lower it, thinking of home.",
        quality_rating=5
    )

    trans1 = service.create_translation(trans1_data)
    trans2 = service.create_translation(trans2_data)
    print(f"✓ Created translations: AI ({trans1.translator_type}), Human ({trans2.translator_type})")

    # Create AI logs
    print("\n🤖 Creating AI logs...")
    ai_log1_data = AILogCreate(
        translation_id=trans1.id,
        model_name="gpt-4",
        workflow_mode=WorkflowMode.REASONING,
        runtime_seconds=45.2,
        token_usage_json='{"prompt_tokens": 850, "completion_tokens": 320, "total_tokens": 1170}',
        cost_info_json='{"total_cost": 0.041, "currency": "USD"}',
        notes="Translation completed with good poetic quality. Captured the pastoral essence effectively."
    )

    ai_log1 = service.create_ai_log(ai_log1_data)
    print(f"✓ Created AI log: {ai_log1.model_name} ({ai_log1.workflow_mode})")

    # Create human notes
    print("\n👤 Creating human notes...")
    note1_data = HumanNoteCreate(
        translation_id=trans2.id,
        note_text="Excellent translation that maintains the concise beauty of the original. The word choices 'splash' and 'frost' create effective imagery. The questioning form 'moonlight? Frost?' captures the contemplative mood perfectly."
    )

    note1 = service.create_human_note(note1_data)
    print(f"✓ Created human note for translation by {trans2.translator_info}")

    # Display dashboard
    print("\n📊 Dashboard Overview:")
    dashboard = service.get_dashboard_data()
    stats = dashboard["stats"]
    print(f"  • Total poems: {stats['total_poems']}")
    print(f"  • Total translations: {stats['total_translations']}")
    print(f"  • AI translations: {stats['ai_translations']}")
    print(f"  • Human translations: {stats['human_translations']}")
    print(f"  • Languages: {', '.join(stats['languages'])}")

    # Display poems with translations
    print("\n📚 Poems and Translations:")
    for poem in dashboard["recent_poems"]:
        print(f"\n📖 {poem.poem_title} by {poem.poet_name} ({poem.source_language})")
        translations = service.get_poem_translations(poem.id)
        for trans in translations:
            print(f"  🌐 {trans.translator_type.title()} translation to {trans.target_language}")
            if trans.translator_info:
                print(f"     By: {trans.translator_info}")
            if trans.quality_rating:
                print(f"     Quality: {'⭐' * trans.quality_rating}")
            # Show preview
            preview = trans.translated_text[:100] + "..." if len(trans.translated_text) > 100 else trans.translated_text
            print(f"     Preview: {preview}")

            # Show additional details
            details = service.get_translation_with_details(trans.id)
            if details["ai_logs"]:
                for ai_log in details["ai_logs"]:
                    print(f"     🤖 AI: {ai_log.model_name} ({ai_log.runtime_seconds}s)")
            if details["human_notes"]:
                for note in details["human_notes"]:
                    note_preview = note.note_text[:80] + "..." if len(note.note_text) > 80 else note.note_text
                    print(f"     👤 Note: {note_preview}")

    # Test search functionality
    print("\n🔍 Testing Search:")
    search_results = service.search_poems("自然")
    print(f"  Found {len(search_results)} poems matching '自然'")
    for result in search_results:
        print(f"    • {result.poem_title} - {result.poet_name}")

    # Test statistics
    print("\n📈 Detailed Statistics:")
    detailed_stats = service.get_repository_stats()
    print(f"  • Latest translation: {detailed_stats.latest_translation}")
    print(f"  • Languages represented: {len(detailed_stats.languages)}")

    # Test pagination
    print("\n📄 Testing Pagination:")
    paginated = service.get_poems_paginated(page=1, page_size=1)
    print(f"  Page {paginated['pagination']['current_page']} of {paginated['pagination']['total_pages']}")
    print(f"  Showing {len(paginated['poems'])} of {paginated['pagination']['total_items']} poems")

    # Cleanup
    session.close()
    print("\n✅ Demo completed successfully! All functionality working as expected.")
    print("\n🎯 Key Features Demonstrated:")
    print("  • Poem creation and management")
    print("  • Translation creation (AI and Human)")
    print("  • AI logging with performance metrics")
    print("  • Human annotation system")
    print("  • Dashboard with statistics")
    print("  • Search functionality")
    print("  • Pagination support")
    print("  • Comprehensive data relationships")


if __name__ == "__main__":
    demo_repository_service()