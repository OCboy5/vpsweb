Vox Poetica Studio Web: Central Poetry Translation Repository Specification
Executive Summary
This document specifies the requirements and design for enhancing the Vox Poetica Studio Web (vpsweb) with a central poetry translation repository. The repository will enable structured storage, classification, access, and searching of translated poems (potentially scaling to thousands), integrating seamlessly with the existing T-E-T (Translator-Editor-Translator) workflow. Additionally, a Web UI will be developed to run T-E-T workflows interactively, browse/search the repository, and allow uploading/storing human-translated poems.
The system targets a low-network-volume niche website, prioritizing simplicity, low cost, and Python-based tools. SQLite (with sqlite-vec extension) is specified as the primary database for its ease and sufficiency, with a clear migration path to PostgreSQL if needed. This enhancement transforms vpsweb from a translation tool into a comprehensive ecosystem for AI and human poetry translations.
Project Goals:

Centralize storage of AI-generated and human translations.
Enable metadata-based classification and advanced search (keyword + semantic).
Provide a Web UI for workflow execution, repo access, and human contributions.
Ensure scalability to 1,000+ poems with low maintenance.

Version: 1.0 (Initial Specification)
Status: Draft for Implementation
Target Completion: 8-12 weeks (phased rollout)
1. Project Overview
1.1 Background
vpsweb is an AI-powered poetry translation platform using LLM models (e.g., Qwen, DeepSeek) in T-E-T workflows, producing JSON and Markdown outputs with details like original poems, translations, notes, and metadata. Outputs are currently file-based in an "outputs" directory.
To support growth, a central repository is required for:

Organizing translations (AI/human).
Classification (e.g., by poet, language, theme).
Efficient access/search.
Web-based interaction, including human uploads.

1.2 Scope

In-Scope:

DB for storing poems with metadata, tags, and embeddings.
Ingest pipeline from workflows and manual uploads.
Classification (auto + manual).
Search (keyword, filtered, semantic).
Web UI for T-E-T runs, repo browsing/searching, and uploads.
Refactors to vpsweb outputs for richer metadata.


Out-of-Scope (for v1.0):

User authentication beyond basic (e.g., no advanced roles).
Community features (e.g., voting, comments).
Multi-modal support (e.g., audio poems).
High-concurrency optimizations.



1.3 Assumptions and Constraints

Low traffic: <100 daily users; occasional ingests.
Poems primarily public domain; UI disclaimer for copyrights.
Python ecosystem focus; leverage vpsweb's existing code.
Dev mode: Free to refactor outputs (e.g., add tags/embeddings).
Hosting: Local for dev; serverless (Vercel) for prod.
Cost: <$20/mo (free tiers preferred).

2. Requirements
2.1 Functional Requirements

Storage:

Store poems as documents with fields: id (UUID), original_text, source_lang, target_lang, poet, title, translations (JSONB array: {type: 'AI'/'human', text, notes, workflow_mode}), metadata (JSONB: {tags: array, themes: array, era}), embeddings (vector), timestamp.
Support multiple translations per poem (e.g., AI versions, human).


Ingest:

Auto-ingest from T-E-T: Post-workflow, parse JSON, generate tags/embeddings, insert/update.
Manual ingest: Via UI/API for human translations (form: poem text, langs, metadata).


Classification:

Auto: Use LLM (e.g., Grok/Qwen) to extract tags/themes from text (prompt: "Extract 5-10 themes, genres, forms from this poem").
Manual: Editable in UI.
Embeddings: Generate via sentence-transformers (all-MiniLM-L6-v2, multilingual) on original + translation text.


Access and Search:

API: Endpoints for list, get/{id}, search (query, filters: lang/poet/tags, semantic similarity).
Basic: Keyword (FTS5), filtered (SQL WHERE).
Semantic: Vector cosine similarity (>0.7 threshold).


Web UI:

T-E-T Runner: Form (poem input, langs, mode) → Run workflow → Display results (side-by-side view) → Ingest option.
Repo Browser: List with pagination/filters; detailed view (side-by-side original/translation, notes).
Search: Input box + results with snippets.
Upload: Form for human translations + metadata → Ingest.
Progress: Real-time bars for workflows.


Integration:

Hook into workflow.py: After execute(), call ingest.
Outputs Refactor: Add "tags" and "embeddings" to JSON.



2.2 Non-Functional Requirements

Performance: <1s for searches; handle 1k+ poems.
Scalability: Design for 10k poems; easy migration to PostgreSQL.
Security: Basic auth for uploads; validate inputs; no sensitive data.
Usability: Intuitive UI; mobile-responsive.
Reliability: Backups (file copies for SQLite); error handling.
Cost: Free/low (SQLite free; Vercel free tier).
Accessibility: Basic WCAG (alt text for images if added later).

2.3 Technical Stack

DB: SQLite (with sqlite-vec extension for vectors).
Backend: Python (extend vpsweb); FastAPI for API.
Embeddings: sentence-transformers (offline).
UI: Streamlit (MVP); migrate to FastAPI + React if needed.
Ingest/Search: SQLAlchemy for ORM; sqlite3 for direct access.
Hosting: Local/Docker dev; Vercel prod.
Tools: Poetry for deps; Pytest for tests; Black/Flake8 for code quality.

3. Design and Architecture
3.1 System Architecture

Components:

Ingest Layer: utils/ingest.py – Parse JSON/MD, LLM tag generation, embed text, DB insert.
DB Layer: poems.db (SQLite file); schema as above.
API Layer: app.py (FastAPI) – Endpoints for ingest/search/get.
UI Layer: ui.py (Streamlit) – Forms, displays, calls API/workflow.
Workflow Integration: core/workflow.py – Add post-execute ingest call.


Data Flow:

Workflow runs → JSON output → Ingest (tags/embed) → DB.
UI T-E-T: Input → Run workflow → Display → Ingest.
UI Upload: Form → API ingest.
Search: Query → API (SQL + vector) → UI results.



3.2 Database Schema
sql-- Enable extensions (load sqlite-vec in code)
CREATE TABLE poems (
    id TEXT PRIMARY KEY,  -- UUID as string
    original_text TEXT NOT NULL,
    source_lang TEXT NOT NULL,
    target_lang TEXT,  -- NULL if original only
    poet TEXT,
    title TEXT,
    era TEXT,
    translations TEXT,  -- JSON array
    metadata TEXT,      -- JSON {tags: [], themes: []}
    embeddings BLOB,    -- Vector as binary (or use sqlite-vec virtual table)
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Virtual table for vectors (via sqlite-vec)
CREATE VIRTUAL TABLE poem_vectors USING vec0(
    poem_id TEXT PRIMARY KEY,
    embedding FLOAT[384]  -- Dim from all-MiniLM-L6-v2
);
-- Indexes
CREATE INDEX idx_poet ON poems(poet);
CREATE INDEX idx_tags ON poems(metadata);  -- If using JSON functions
3.3 Key Interfaces

API Endpoints (FastAPI):

POST /ingest: Body (poem data) → Insert/update.
GET /poems: Params (page, limit) → Paginated list.
GET /poems/{id}: → Detailed poem.
GET /search: Params (query, filters, semantic=true) → Results.


UI Pages (Streamlit):

Home: T-E-T form + run button.
Browse: Filters + list.
Search: Query input + results.
Upload: Human translation form.



4. Implementation Plan
4.1 Phases

Phase 1: Design and Prototype (1-2 Weeks):

Refactor outputs: Add tags/embeddings generation in workflow.
Setup DB: SQLite schema; test ingest script.
Basic CLI search/ingest tools.


Phase 2: Core Repository (2-4 Weeks):

API development.
Advanced search (keyword + semantic).
Workflow integration hook.


Phase 3: Web UI (4-6 Weeks):

Streamlit MVP: Forms, views, integration.
Testing: Ingest 50+ samples; UI usability.


Phase 4: Scaling/Polish:

Backups, monitoring.
Deploy to Vercel.
Human review for tags.



4.2 Testing and Quality Assurance

Unit/Integration Tests: Cover ingest, search, API (Pytest; 80% coverage).
Data Validation: Schema checks; embedding accuracy.
Performance: Benchmark searches (<1s for 1k poems).
Usability: Manual testing of UI flows.
Edge Cases: Long poems, multi-langs, invalid inputs.

4.3 Risks and Mitigations

Risk: Search Performance: Mitigate with indexes; fallback to keyword if vectors slow.
Risk: Data Loss: Mitigate with file backups (e.g., Git for DB file).
Risk: Inaccurate Tags: Mitigate with editable UI; prompt refinements.
Risk: Cost Overruns: Monitor; stay on free tiers.

5. Deliverables

Updated vpsweb repo with /repository/ folder (DB, scripts).
API documentation (Swagger via FastAPI).
UI prototype (Streamlit app).
Sample data (ingested outputs).
Migration guide to PostgreSQL.

6. Approval and Next Steps

Approval: Review and sign off.
Implementation: Feed to Claude Code for coding.
Timeline: Start Phase 1 upon approval.