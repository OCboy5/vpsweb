1 — Quick facts from vpsweb (what I used as assumptions)

vpsweb already implements a three-step Translator → Editor → Translator workflow and outputs structured translation artifacts (XML/JSON), with detailed metadata and token/cost tracking. 
GitHub

It is designed as a Python library + CLI and provides a Python API and CLI commands to run translations. 
GitHub

The project already supports multiple workflow modes (Reasoning / Non-Reasoning / Hybrid) and includes WeChat article generation from translation outputs. 
GitHub

It emphasizes modular architecture and YAML-based configuration, which we can reuse for repository integration. 
GitHub

These capabilities let us integrate smoothly: the repository can ingest vpsweb’s JSON/XML outputs and also call into the Python API to run workflows from the UI.

2 — High-level goals for the central repository & Web UI

Ingest vpsweb translation outputs (AI-generated) and store them with rich metadata and provenance.

Accept and store human translations and human edits/notes for the same poems.

Support comparison views (AI vs human, different AI versions, editor notes, token/cost logs).

Local-first: run on a single machine for personal use, but designed to scale to a small public site later.

Searchable and classifiable (search is out-of-scope for phase 1, but design must support adding full-text search & tag filtering later).

Integrate with existing vpsweb CLI/Python API so translation runs can be launched from the Web UI and results auto-ingested.

3 — Recommended tech stack (local-first, production-ready)

Backend: Python (reuse vpsweb package). Use FastAPI for REST endpoints (lightweight, async-friendly, easy to integrate with vpsweb).

Database: start with SQLite + FTS5 for full-text later; store metadata and allow easy local backups. Provide migration scripts to Postgres for future hosting.

Storage of raw outputs: keep raw vpsweb JSON/XML files in a structured filesystem repository (for auditability), plus parse key metadata into the DB.

Frontend: React (CRA or Vite) + Tailwind CSS for quick, modern UI (developer guidelines in your earlier notes favor Tailwind).

Authentication: local-first: optional simple password or OS user; keep auth minimal for phase 1. For future public site: add OAuth or token-based auth.

Search/Index (phase 2): PostgreSQL + tsvector or a document DB (Elasticsearch/Meilisearch) for rich search; initial design should keep fields that enable indexing (title, poet, languages, translator, tags, poem text).

Integration: expose a vpsweb “ingest” / “repo-add” CLI and a FastAPI endpoint so the UI can call POST /api/ingest or run vpsweb locally and have the output pushed to the repository.

Deployment: local: single host run with docker-compose (db + backend + frontend). Production: same with Postgres + reverse proxy.

4 — Data model & metadata (JSON Schema / minimal fields)

Design everything so the raw vpsweb JSON/XML is kept intact and a normalized metadata record is created.

Example canonical JSON metadata (document to store in DB as single row, and keep raw JSON in raw/ folder):

{
  "id": "poet-surname_first-title_20251017_v1",
  "poet": "Wislawa Szymborska",
  "title": "Some Poem Title",
  "source_language": "Polish",
  "original_text": "line1\nline2\n...",
  "translations": [
    {
      "id": "ai_vpsweb_20251017_0234",
      "type": "ai",
      "model": "deepseek-reasoner",
      "workflow_mode": "hybrid",
      "output_text": "translated text...",
      "notes": "translator notes from vpsweb",
      "token_usage": {"prompt_tokens": 1200, "completion_tokens": 800},
      "cost_rmb": 0.XX,
      "raw_output_path": "raw/poet/title/ai_vpsweb_20251017_0234.json",
      "created_at": "2025-10-17T02:34:12Z"
    },
    {
      "id": "human_jli_20251018",
      "type": "human",
      "translator_name": "Jia Li",
      "output_text": "human translation ...",
      "notes": "hand-edited to preserve rhyme",
      "raw_file_path": "human/poet/title/human_jli_20251018.md",
      "created_at": "2025-10-18T14:11:00Z"
    }
  ],
  "tags": ["sonnet","romantic"],
  "provenance": {
    "ingested_by": "vpsweb-cli",
    "ingested_at": "2025-10-17T03:00:00Z",
    "source_repo_commit": "abcdef1234"
  },
  "versions": [
    {"version_id":"v1","created_at":"2025-10-17T03:00:00Z","notes":"first ingest"}
  ],
  "visibility": "private",
  "format": "vpts-json",
  "language_pairs": ["Polish→English", "English→Chinese"]
}


Minimum required DB columns / fields (for fast listing & search later):

id (unique)

poet_name

title

source_lang

languages (list)

primary_ai_translation_id

human_translation_count

created_at

updated_at

tags

raw_path

summary (short prose used in list views)

visibility

5 — File & naming conventions (recommendation)

vpsweb README suggests “poet-first naming” — keep that convention for clarity.

Repository file layout (suggested):

/vpsrepo/
  raw/                          # raw vpsweb outputs (JSON/XML)
    poet_surname_first/
      title_slug/
        ai_vpsweb_20251017_0234.json
        ai_vpsweb_20251018_0412.json
        vpts_output.xml
  human/                        # human translations & notes
    poet_surname_first/
      title_slug/
        human_jli_20251018.md
  db/
    repo.sqlite                  # main metadata DB (SQLite)
  exports/
    wechat/
  backups/
  config.yml                    # repo-level config (naming scheme, backup schedule)


Filename format
{poet_surname}_{poet_given}_{title_slug}_{sourceLang}-{targetLang}_{YYYYmmddTHHMMSS}_{kind}_{vN}.{json|md|xml}

Example: szymborska_wislawa_the-mirrors_PL-EN_20251017T023412_ai_v1.json

6 — Repository DB design & indexing plan (local-first)

Start with SQLite and a single translations table. Add an ft virtual table using FTS5 for full-text indexing of original_text and translations later.

Core tables:

poems (id, poet, title, original_text, source_lang, created_at)

translations (id, poem_id, type, translator, model, output_text, notes, token_usage_json, raw_path, created_at)

tags and poem_tags

ingest_logs (audit trail)

Indexing:

Index on (poet, title) and created_at.

Add FTS5 virtual table for original_text + output_text (for later search).

Backups:

Periodically dump SQLite to backups/ and also keep zipped copies of the raw/ folder.

7 — Web UI — features & screens (phase 1)

Design minimal, focused UI to deliver core functionality now:

A. Dashboard

Recent ingests, recent edits, quick-run translation button (select poem file or paste original), repo size.

B. Poem list / catalog

Sort by poet / date / tags. Show small summary, languages available, human vs AI counts.

C. Poem detail / compare view

Left column: original (with line numbers).

Middle: AI translation(s) (able to select which AI run/version).

Right: human translation(s).

Inline toggle to show notes, token/cost info, and raw JSON.

A side-by-side diff mode (line-by-line) for comparison.

D. Run translation

Form to trigger vpsweb workflow (choose workflow mode, model overrides, extra prompts).

Option: “save-to-repo automatically” / “preview only”.

E. Upload human translation

Simple editor to paste or upload a file and add translator metadata (name, date, notes). Commits a new translation record and stores raw file.

F. Versioning & history

Show previous versions of translations and allow revert & snapshot.

G. Admin

Settings for naming scheme, backups, API keys (if required for cloud models), tokens/costs display, and export to WeChat.

8 — API endpoints (example FastAPI surface)

POST /api/ingest — accept vpsweb JSON or XML; validate and create DB record.

GET /api/poems — list (with filters).

GET /api/poems/{id} — poem + translations.

POST /api/poems/{id}/translations — add human translation.

POST /api/translate — trigger vpsweb translation (server-side call to Python API).

POST /api/export/wechat/{poem_id} — produce WeChat article HTML (reuse vpsweb template).

Design the API so that the frontend is thin: the heavy lifting is vpsweb + DB.

9 — Prototype strategy — concrete steps to build local MVP

Make the prototype minimal but end-to-end.

Phase P0 — prep

Fork/clone vpsweb locally; set up environment & confirm vpsweb CLI & API work. Follow README steps. 
GitHub

Phase P1 — repository & ingestion
2. Create vpsrepo repository folder (structure above).
3. Implement vpsweb repo-ingest CLI or small script:

Input: path to vpsweb JSON/XML output.

Action: validate, move raw file into raw/poet/title/, create DB entry in SQLite.

Build a basic FastAPI backend that can call that ingest script and serve GET /api/poems.

Phase P2 — UI & integration
5. Create a minimal React UI with three pages: Dashboard, Poem list, Poem detail/compare.
6. Add “Run Translation” button in UI that POSTs to POST /api/translate and shows live progress from vpsweb (use WebSocket or polling). vpsweb already has progress displays; adapt its logging to stream to the frontend. 
GitHub

7. Add “Upload human translation” form and hook it to POST /api/poems/{id}/translations.

Phase P3 — polishing
8. Add diff view, token/cost display per translation (get token info from vpsweb output). 
GitHub

9. Add backups and a simple admin page to configure naming scheme & visibility.
10. Add tests and a docker-compose.yml (backend + frontend + sqlite persistent volume).

Phase P4 — optional
11. Replace SQLite with Postgres + add full-text search using Postgres tsvector or Meilisearch.
12. Add user auth & role (viewer/editor/admin).
13. Add export & WeChat publishing support using vpsweb’s existing WeChat generation. 
GitHub

10 — Changes I recommend in vpsweb to ease integration

You don’t need to rewrite vpsweb; make small changes so the repo can be ingested consistently.

Add an explicit “export manifest” for each translation output (e.g., manifest.json alongside the raw JSON/XML) that contains top-level metadata (poet, title, source/target languages, workflow_mode, models used, token counts, output file name). This makes ingestion trivial.

Add a --save-to-repo flag to the CLI that calls a local hook: either run the ingest script or call POST /api/ingest.

Provide a programmatic Python function vpsweb.export_for_repo(output_path, repo_config) that returns normalized metadata and raw path. (Expose in the Python API.) 
GitHub

Standardize file naming option in config (so vpsweb can write files in the exact naming scheme used by the repo).

Add a small “progress/event” emitter (log lines or socket events) that the FastAPI UI can subscribe to when a translation runs (so the UI can display real-time progress). vpsweb already has real-time progress displays — convert them to logs/events consumable by the UI. 
GitHub

These are small refactors and preserve existing features.

11 — Security, backups, privacy

Keep API keys out of the repo: store in a local .env (vpsweb already uses .env.example). Backups should not include API keys. 
GitHub

For local-first, simple password-protected UI is fine; when going public, require HTTPS, rate limiting, and stronger auth.

Provide export & delete flows to comply with privacy (if a human translator asks to remove their translation).

12 — Testing & QA

Unit tests for ingest parsing (simulate different vpsweb JSON versions).

Integration tests for POST /api/ingest and POST /api/translate (mock vpsweb API).

UI end-to-end tests for the compare view.

13 — Example: ingest flow (end-to-end)

User runs vpsweb translate --input poem.txt --output raw/poet/title/ai_...json --save-to-repo

vpsweb writes raw JSON + manifest.json and either calls local POST /api/ingest or moves files to vpsrepo/raw/....

Backend parses manifest, creates poems row if absent, creates translations row, stores raw path.

Frontend shows the new poem in the catalog; user can open compare view and upload a human translation.

14 — Migration & scaling plan

Local → Public: migrate DB from SQLite to Postgres; move raw files to object storage (S3) and keep metadata in Postgres. Enable a full-text search service (Meilisearch / Elastic) for fast lookup.

Performance: shard / cache frequent queries, and cache raw output retrieval.

Data model keep: always keep raw outputs immutable; new edits create new translation entries (versioning).

15 — Deliverables you can use directly (what I’ll produce next if you want)

A PSD-style document built from the above, expanded with UML diagrams and API spec (OpenAPI) + DB schema SQL.

A small prototype repo with: FastAPI backend, SQLite DB schema, a React UI scaffold, and an ingest script that accepts vpsweb JSON.
Tell me which of the two you want first and I’ll produce the PSD or start scaffolding the prototype (backend + ingest script + sample frontend).