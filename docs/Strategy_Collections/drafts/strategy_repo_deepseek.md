Poetry Translation Repository & Web UI Strategy

1. Repository Architecture Design

1.1 Storage Strategy

Decision: Hybrid JSON-based file storage with SQLite metadata indexing

Primary Storage: Structured JSON files for poems and translations
Metadata Index: SQLite database for fast searching and classification
File Organization:

text
poetry_repository/
├── originals/          # Original poems
├── translations/       # AI and human translations
├── metadata.db         # SQLite database for search
└── workflow_logs/      # Translation process logs
1.2 Data Structure Design

json
{
  "poem_id": "unique_identifier",
  "metadata": {
    "title": "Original Title",
    "author": "Author Name",
    "dynasty": "Tang/Song/etc.",
    "original_language": "classical_chinese",
    "target_language": "english",
    "themes": ["nature", "love", "friendship"],
    "difficulty_level": "easy/medium/hard",
    "creation_date": "2024-01-01",
    "last_modified": "2024-01-01"
  },
  "original_poem": {
    "text": "Original poem text...",
    "structure": "quatrain/regulated_verse/etc.",
    "rhyme_scheme": "AABA"
  },
  "translations": {
    "ai": {
      "vpsweb_v1": {
        "text": "AI translated text...",
        "timestamp": "2024-01-01T10:00:00Z",
        "model_version": "vpsweb-1.0",
        "translation_approach": "literal/poetic/rhymed"
      }
    },
    "human": {
      "translator_john": {
        "text": "Human translated text...",
        "translator_name": "John Smith",
        "translation_style": "creative/literal",
        "notes": "Translation notes...",
        "timestamp": "2024-01-01T11:00:00Z"
      }
    }
  },
  "translation_logs": {
    "ai_workflow": [
      {
        "step": "preprocessing",
        "input": "raw text",
        "output": "processed text",
        "timestamp": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
2. Web UI Architecture

2.1 Framework Selection

Decision: Flask with Jinja2 templates and vanilla JavaScript

Backend: Flask (consistent with current vpsweb architecture)
Frontend: Jinja2 templates + Bootstrap 5 + vanilla JavaScript
Rationale: Lightweight, easy to extend, consistent with existing codebase
2.2 UI Component Structure

text
templates/
├── base.html              # Main template
├── dashboard.html         # Repository overview
├── workflow.html          # Translation workflow
├── poem_view.html         # Individual poem view
├── compare.html           # Comparison interface
├── human_input.html       # Human translation input
└── search.html           # Search interface (future)
3. Integration Strategy with vpsweb

3.1 Required vpsweb Modifications

Current vpsweb changes needed:

python
# New vpsweb module structure
vpsweb/
├── core/
│   ├── translator.py      # Existing translation logic
│   └── repository.py      # NEW: Repository management
├── models/
│   ├── poem.py           # NEW: Poem data model
│   └── translation.py    # NEW: Translation data model
└── web/
    ├── routes.py         # Extended with repository routes
    └── templates/        # Extended UI templates
3.2 API Endpoints Design

python
# New Flask routes
@app.route('/repository')
def repository_overview():
    """Main repository dashboard"""

@app.route('/workflow/translate', methods=['GET', 'POST'])
def translation_workflow():
    """AI translation workflow interface"""

@app.route('/poem/<poem_id>')
def view_poem(poem_id):
    """View individual poem with all translations"""

@app.route('/compare/<poem_id>')
def compare_translations(poem_id):
    """Compare AI vs human translations"""

@app.route('/human/input', methods=['GET', 'POST'])
def input_human_translation():
    """Input human translations"""
4. Implementation Phases

Phase 1: Core Repository Foundation (2-3 weeks)

Implement data models (Poem, Translation, Translator)
Create repository management system
Design and implement basic file storage structure
Build SQLite metadata index
Phase 2: Basic Web UI (3-4 weeks)

Extend Flask application with repository routes
Implement repository dashboard
Create poem viewing interface
Build human translation input form
Phase 3: Workflow Integration (2-3 weeks)

Integrate vpsweb translation workflow with repository
Create translation comparison interface
Implement translation logging system
Phase 4: Enhancement & Polish (2 weeks)

Add classification and tagging system
Implement basic search functionality
UI/UX improvements and testing
5. Key Technical Decisions

5.1 Storage Rationale

JSON files: Human-readable, easy backup, version control friendly
SQLite index: Fast metadata queries, easy to migrate to full DB later
File naming: {poem_id}_{author_slug}_{title_slug}.json
5.2 ID Generation Strategy

python
def generate_poem_id(author, title, dynasty):
    """Generate unique, readable poem IDs"""
    author_slug = slugify(author)[:20]
    title_slug = slugify(title)[:30]
    dynasty_slug = dynasty[:10].lower()
    return f"{dynasty_slug}_{author_slug}_{title_slug}_{hash}"
5.3 Classification System

Themes: Predefined set (nature, love, friendship, travel, etc.)
Difficulty: Based on vocabulary, structure complexity
Style: Classical/modern, regulated verse/free verse
6. Prototype Strategy

6.1 Minimum Viable Prototype

Focus: Basic repository with 10 sample poems

Simple Flask UI with poem listing
Basic translation workflow integration
Manual human translation input
Side-by-side comparison view
6.2 Prototype Implementation Steps

Week 1: Set up data structures with sample data
Week 2: Implement basic Flask UI for browsing
Week 3: Integrate simple translation workflow
Week 4: Add comparison functionality and polish
7. Future-Proofing Considerations

7.1 Scalability Preparations

Database-ready design: Easy migration from SQLite to PostgreSQL
API-first approach: RESTful endpoints for future web/mobile apps
Modular architecture: Easy to add search, user accounts, etc.
7.2 Metadata Extensibility

Flexible schema: JSON structure allows adding new fields
Tagging system: Easy to extend classification
Version control: Track changes to poems and translations
8. Integration Modifications for Current vpsweb

8.1 Required Changes

Refactor translation output to use repository data models
Add repository logging to translation workflow
Extend configuration for repository paths and settings
Update existing routes to use new data structure
8.2 Backward Compatibility

Maintain existing vpsweb functionality during transition
Provide migration scripts for existing translations
Phase-in approach to minimize disruption
9. Success Metrics

9.1 Development Phase

Repository can store 100+ poems with multiple translations
UI responsive and intuitive for poetry scholars
Translation workflow seamless and well-documented
9.2 User Experience

Easy classification and retrieval of poems
Clear comparison between AI and human translations
Efficient workflow for adding new content
This strategy provides a solid foundation for building a comprehensive poetry translation repository while maintaining flexibility for future expansion. The phased approach ensures manageable development with clear milestones and the ability to adjust based on early user feedback.