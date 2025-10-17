Draft Strategy for vpsweb Poetry Translation Repository & Web UI
1. Executive Summary

The goal is to build a local, personal-use system consisting of:
A central repository for storing translated poems (AI and human-generated), metadata, and translation logs/notes.
A Web UI to manage translation workflows (AI and human), store outputs in the repository, and access/explore stored content.
This strategy prioritizes simplicity, scalability for thousands of entries, and seamless integration with the existing vpsweb AI translation system. Future expansion to a public niche website is accounted for in the design but not implemented in this phase.
2. Repository Design

2.1 Storage Solution: SQLite Database

Rationale:
Local, serverless, and self-contained (no separate server required for personal use).
Supports relational data (critical for linking poems, translations, and logs).
Handles thousands of entries efficiently (sufficient for initial scale).
Built-in full-text search (via FTS5 extension) for future search functionality.
Easy migration to PostgreSQL/MySQL if scaling to public use later.
Alternative Evaluated:
File-based storage (JSON/YAML directories): Simpler but poor querying, hard to enforce relationships, and inefficient for large datasets.
MongoDB: Overkill for local use; relational structure of poems/translations fits SQL better.
2.2 Data Schema

The repository will use 4 core tables to enforce relationships and enable classification:
Table	Purpose	Key Fields
poems	Store original poem metadata (single source of truth for original text)	poem_id (PK), original_text, original_lang (e.g., "zh"), target_lang (e.g., "en"), author, genre (e.g., "sonnet"), source (e.g., "Tang Dynasty"), added_date
translations	Link translations (AI/human) to their original poem	translation_id (PK), poem_id (FK), translator_type ("AI"/"human"), translator_info (e.g., "GPT-4" or "Jane Doe"), translated_text, translation_date
ai_logs	Store AI translation details (specific to AI workflows)	log_id (PK), translation_id (FK), model_params (JSON, e.g., temperature), prompt_template, runtime_seconds, errors (if any)
human_notes	Store human translator annotations (specific to human workflows)	note_id (PK), translation_id (FK), note_text (e.g., "Preserved rhyme scheme"), last_edited
Relationships:
One poem → many translations (1:M between poems and translations).
One translation → one AI log (if AI) or many human notes (if human).
2.3 Classification & Organization

To enable easy access, the repository will support classification by:
Language pair (original_lang + target_lang, e.g., "zh→en").
Genre (genre, e.g., "haiku", "ode").
Author (author).
Translator type (translator_type: "AI" vs. "human").
3. Web UI Design

3.1 Tech Stack

Backend: Flask (Python)
Rationale: Lightweight, easy to integrate with Python-based vpsweb (assuming vpsweb uses Python), and supports SQLite via SQLAlchemy ORM.
Alternative: FastAPI (more modern but overkill for local use; Flask is simpler for prototyping).
Frontend: HTML5 + Jinja2 (templating) + Bootstrap 5
Rationale: No need for complex SPAs (single-page apps) for local use; Bootstrap ensures responsiveness with minimal effort.
3.2 Core UI Workflows

The Web UI will include 5 key pages to cover all user needs:
1. Dashboard
Overview of repository stats: total poems, AI vs. human translations, top languages/genres.
Quick links to other workflows (e.g., "New AI Translation", "Add Human Translation").
2. AI Translation Workflow
Input: Original poem text, metadata (author, genre, languages).
Integration with vpsweb: A button to trigger vpsweb’s AI translation pipeline (see §4 for integration details).
Preview: Displays AI-translated text and logs (model params, runtime) before saving.
Save: Commits the original poem, translation, and logs to the repository.
3. Human Translation Input
Input: Original poem text (or link to existing poem in repo) + human-translated text + metadata (translator name, notes).
Save: Commits the translation and notes to the repository (links to existing poems entry if original text matches).
4. Repository Browser
Filters: Language pair, genre, author, translator type (dropdowns/checkboxes).
Display: List of poems matching filters, with expandable sections showing:
Original text.
All translations (AI and human) side-by-side.
AI logs or human notes (toggleable).
5. Poem Detail Page
Focused view of a single poem: original text, all translations, and associated logs/notes.
Action buttons: "Add Another Translation" (AI/human).
4. Integration with vpsweb

4.1 Required Modifications to vpsweb

To streamline integration with the repository and Web UI:
Expose a Translation Function: Modify vpsweb to export a Python function (e.g., translate_poem(original_text, source_lang, target_lang, model_params)) that returns:
translated_text (str).
logs (dict with model name, params, runtime, errors).
Decouple Storage: Remove any existing file-based storage in vpsweb; instead, let the Web UI handle saving to the repository.
4.2 Workflow Integration

User inputs poem details in the Web UI’s "AI Translation" page.
UI calls vpsweb’s translate_poem() function with the input.
vpsweb returns translated text and logs.
UI displays results to the user for review.
On user confirmation, UI writes:
A new entry to poems (if original text is new).
A new entry to translations (linked to poem_id).
A new entry to ai_logs (linked to translation_id).
5. Prototype Strategy

5.1 Phase 1: Minimal Viable Repository (1–2 weeks)

Set up SQLite database with the 4 tables (using SQLAlchemy migrations).
Create basic CRUD (Create/Read/Update/Delete) functions for the repository (e.g., add_poem(), get_translations_for_poem()).
5.2 Phase 2: Web UI Skeleton (1 week)

Build Flask backend routes for the 5 core pages.
Create frontend templates with Bootstrap for layout (no styling polish yet).
5.3 Phase 3: vpsweb Integration (1 week)

Modify vpsweb to expose the translate_poem() function.
Connect the "AI Translation Workflow" page to call this function and save results to the repository.
5.4 Phase 4: Human Translation & Browser (1 week)

Implement "Human Translation Input" page to save human translations/notes.
Add filtering and display logic to the "Repository Browser".
5.5 Testing Criteria

10 sample poems (5 with AI translations, 5 with human translations) are stored correctly.
Users can filter poems by language pair and genre.
AI translations trigger vpsweb correctly and save logs.
6. Future Considerations (For Public Expansion)

Database Migration: Switch to PostgreSQL for better concurrency and scalability.
Authentication: Add user accounts (via Flask-Login) to restrict access.
Search: Enable full-text search using SQLite FTS5 (or PostgreSQL tsvector) for poem text/metadata.
API Layer: Expose a REST API for programmatic access (e.g., for third-party tools).
This strategy balances simplicity for local use with extensibility, ensuring the system can grow from a personal tool to a public niche platform.