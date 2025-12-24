vpsweb Central Repository & Local Web UI — Lightweight Strategy (Phase Next)
Version: 0.9 (Draft for PSD generation)
Baseline: strategy_repo_doubao.md (simplified and refined)
Scope: Local personal-use system; future public site considered but out-of-scope now

Why this version

Minimal dependencies, minimal ops, fast to implement.
Single-process Flask app + SQLite. No external services, no message queues.
Hybrid storage: DB for indexing; filesystem for long-form artifacts.
Keeps vpsweb unchanged; integrate via a thin adapter or JSON ingest.
1) Goals (this phase)
Central repository
Store originals, translations (AI + human), and notes/logs.
Basic classification (author, language pair, form/period optional).
No full-text search yet; design to add later.
Local Web UI (Flask + Jinja2 + Bootstrap)
Run vpsweb translation workflow; on success, save into repo.
Browse works and translations.
Input/store human translations; compare AI vs human side-by-side.
Provenance
Keep raw vpsweb outputs (JSON) + short notes in files; minimal summaries in DB.
Non-goals (now)

Public deployment, RBAC, semantic search, advanced analytics.
2) Architecture (monolith, ultra-light)
Backend: Flask (sync), SQLAlchemy, Jinja2, Bootstrap 5
DB: SQLite (WAL). Single file (repo.db). Backups via file copy.
Jobs: Python ThreadPoolExecutor(max_workers=1) for long-running translation calls (keeps UI responsive).
Storage: filesystem folders under repo_root/data for originals, translations, and raw logs.
vpsweb integration:
Option A (simplest): UI triggers vpsweb CLI → waits → ingest resulting JSON.
Option B (slightly nicer): Import vpsweb.TranslationWorkflow and call execute() directly in a background thread, then write artifacts.
Why Flask + SQLite

Zero extra runtime components; portable; ideal for personal use.
Easy to lift to FastAPI/Postgres later if needed.
3) Data model (4 core tables + 2 optional)
Keep it small and practical. Store longer texts in DB (for display), and also write files for provenance.

Tables

poems
id (ULID TEXT PK)
poet_name TEXT
poem_title TEXT
source_language TEXT (BCP 47: en, zh-Hans, zh-Hant)
original_text TEXT
form TEXT NULL (optional classification)
period TEXT NULL (optional classification)
created_at TEXT (ISO) updated_at TEXT (ISO)
translations
id (ULID TEXT PK)
poem_id (FK -> poems.id)
translator_type TEXT CHECK ('ai','human')
translator_info TEXT NULL (e.g., “vpsweb (hybrid)” or “Jane Doe”)
target_language TEXT
translated_text TEXT
license TEXT NULL (default AI: CC-BY-4.0; human: all_rights_reserved)
created_at TEXT (ISO)
raw_path TEXT NULL (path to raw JSON/file folder)
ai_logs (optional, for AI translations)
id (ULID TEXT PK)
translation_id (FK)
model_name TEXT NULL
workflow_mode TEXT NULL
token_usage_json TEXT NULL
cost_info_json TEXT NULL
runtime_seconds REAL NULL
notes TEXT NULL (short free-form note)
created_at TEXT (ISO)
human_notes (optional, for human translations)
id (ULID TEXT PK)
translation_id (FK)
note_text TEXT
created_at TEXT (ISO)
Optional later (not required now):

tags (id, name); poem_tags (poem_id, tag_id)
DDL sketch (SQLite)

SQL

CREATE TABLE poems (
  id TEXT PRIMARY KEY,
  poet_name TEXT NOT NULL,
  poem_title TEXT NOT NULL,
  source_language TEXT NOT NULL,
  original_text TEXT NOT NULL,
  form TEXT,
  period TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE translations (
  id TEXT PRIMARY KEY,
  poem_id TEXT NOT NULL REFERENCES poems(id) ON DELETE CASCADE,
  translator_type TEXT NOT NULL CHECK (translator_type IN ('ai','human')),
  translator_info TEXT,
  target_language TEXT NOT NULL,
  translated_text TEXT NOT NULL,
  license TEXT,
  raw_path TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE ai_logs (
  id TEXT PRIMARY KEY,
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  model_name TEXT,
  workflow_mode TEXT,
  token_usage_json TEXT,
  cost_info_json TEXT,
  runtime_seconds REAL,
  notes TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE human_notes (
  id TEXT PRIMARY KEY,
  translation_id TEXT NOT NULL REFERENCES translations(id) ON DELETE CASCADE,
  note_text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
Metadata standard (light)

Record only the essentials in DB; any extra DH metadata (Dublin Core/TEI-ready fields) can be added later.
Use BCP 47 language codes; keep form/period simple free-text now.
4) Filesystem layout (simple and stable)
repo_root/

repo.db
data/
poems/{poem_id}/
original.md
meta.json # minimal poem metadata snapshot
translations/{translation_id}/
final.md # translated text as markdown
notes.md # brief bullet notes (AI summary or human note)
raw.json # exact vpsweb output JSON (for AI) or uploaded .md for human
preview.txt (optional)
backups/ # zipped db + data folder backups
.env # local config
Notes

We deliberately avoid deep nested author/title trees to keep it simple.
DB is the index; files are the provenance. Paths are recorded in translations.raw_path.
5) Web UI (Flask + Jinja2 + Bootstrap)
Pages

Dashboard
Counts (poems, translations; AI vs human)
Recent items; Quick actions (New AI translation, Add human translation)
Poems
List (poet, title, language, created date) with filters (poet, lang)
Detail: show original text; list translations (table: type, target, date, byline)
Compare view: Original vs selected translation (AI or human) side-by-side
New AI translation
Form: poet, title, source_language, target_language, original_text
Mode selection (hybrid/reasoning/non_reasoning); model override optional
Submit → background thread runs vpsweb; UI shows “processing…”; refresh to see result
Add human translation
Choose existing poem (by title) or create new
Paste translation text; translator name; license; optional note
Save → creates translation + human_notes (if provided)
Translation detail
Show text; provenance; download raw.json (if AI)
If AI: show summary metrics (tokens, cost, model, mode)
UI choices

Server-rendered templates; minimal custom JS.
Bootstrap tables and forms; no SPA or HTMX required (can add later if desired).
6) Integration with vpsweb (two simple paths)
Path A — CLI + ingest (zero code change to vpsweb)

Flask calls a small Python function that:
Writes a temporary input file
Runs subprocess: vpsweb translate ... --output temp.json
On success, calls ingest_json(temp.json) to store in repo (DB + files)
Pros: minimal coupling; uses vpsweb as-is.
Cons: Needs subprocess and temp files; slightly slower.
Path B — Python API call (slightly tighter integration)

Import TranslationWorkflow and call execute() inside a background thread
Upon return, receive the result object dict; write raw.json and artifacts; store in DB
Pros: cleaner; no subprocess; faster iteration
Cons: Slightly more coupling; still simple in practice.
Either path works locally. Start with A; upgrade to B when convenient.

Ingestion mapping (AI)

poem: poet_name, poem_title, source_language, original_text
translation: translator_type="ai", target_language, translated_text = revised_translation.revised_translation
raw_path → write outputs JSON to data/translations/{translation_id}/raw.json
ai_logs: model_name, workflow_mode, token_usage_json, cost_info_json, runtime_seconds (read from JSON)
Human ingestion

translation: translator_type="human", translator_info=byline
raw_path → copy uploaded .md (or generate from pasted text)
human_notes → note_text if provided
7) Minimal classification (now) and search (later)
Now

Filters on list views (poet_name, source_language, target_language, translator_type).
Optional “form” and “period” fields for manual tagging.
Later (not in this phase)

SQLite FTS5 tables for poems.original_text and translations.translated_text.
jieba-based tokenization for zh; standard unicode61 otherwise.
8) Prototype plan (fast track)
Week 1

Initialize Flask app + SQLite (SQLAlchemy models + simple migration script)
Implement DB schema and filesystem helpers (ULID, paths)
Build pages: Dashboard, Poems list/detail, Compare view
Implement “Add human translation” flow (DB + files)
Week 2

Implement AI translation:
Start with Path A (CLI + ingest); background thread wrapper
Build “New AI translation” form and job status page
Implement translation detail page with provenance and raw.json link
Add backup script (zip db + data)
Optional polish (1–2 days extra)

Basic text diff (line-by-line) in compare view
Simple import script for existing outputs/*.json (batch ingest)
9) Config & Ops (local-only)
.env
REPO_ROOT=./repo_root
DATABASE_URL=sqlite:///repo_root/repo.db
VPSWEB_BIN=vpsweb # path to CLI (for Path A)
LOG_LEVEL=INFO
Backups
scripts/backup.py → zip repo.db + data/
No auth (local use). If desired later: single password in .env.
10) Acceptance criteria (this phase)
Create poem and add human translation via UI; stored in DB + files.
Run AI translation via UI; result saved; raw vpsweb JSON captured.
View poem detail with original and list of translations.
Side-by-side compare original vs a selected translation.
Provenance visible for AI translations (model, mode, token/cost summary).
Backup script produces a restorable archive.
11) Future-proof hooks (without heavy design now)
Table columns (form, period) present for later classification.
raw_path recorded so external tools can process artifacts.
Optional ai_logs/human_notes allow richer UI later without schema change.
Clear upgrade path:
Flask → FastAPI (if needed)
SQLite → Postgres
Server-render HTML → add HTMX or a small SPA as requirements grow
Add FTS5 + semantic search later without breaking existing data
12) Minimal changes suggested to vpsweb (optional, not required)
Ensure TranslationWorkflow.execute returns a consistent dict structure (already appears to).
Include model_name, workflow_mode, tokens, durations, and total_cost in top-level fields for easier ingestion.
Provide a CLI flag --output <json> to save a single canonical JSON (if not already).
That’s it—no refactor needed to start.
13) Risks & mitigations
Title/author parsing variations → UI allows manual edit before save.
Long-running translations block UI → run in background thread; show a “processing” page with manual refresh.
Duplicate poems → simple dedup rule: (poet_name + poem_title + hash of normalized original_text).
Windows path quirks → normalize paths; use os.path.join everywhere.
14) Deliverables from this strategy
A concise PSD with:
Exact DB schema and file path contracts
Flask routes map + templates outline
vpsweb integration flow (CLI Path A first)
Ingest functions (AI and human)
Backup/restore recipe
A minimal prototype repo structure scaffold