VPSWeb Poetry Translation Repository — Project Specification Document (PSD)
Version: 0.1 (Draft)
Date: 2025-10-07
Author: You + Assistant
Status: Approved for implementation (Frontend Option 1, DB: SQLite)

Scope and Goals
Build a central repository for poems and translations with:
Classification, search, provenance, and curation for AI and human translations.
Web UI to run Translator→Editor→Translator (TET) workflows and accept human submissions.
Hybrid storage: SQLite for canonical entities; Git-tracked file store for full texts and artifacts.
Traffic: low-volume niche site, simple ops, easy deploy.
Non-goals (v1)

No multi-tenant orgs, no complex OAuth providers.
No heavy search engine (Meilisearch/ES). Use SQLite FTS5 + Python tokenization.
Embedding search optional in v2 (pure-Python cosine similarity acceptable for v1.1).
User Roles and Permissions
Viewer: browse/search published works/translations.
Translator: create/edit drafts, submit for review, view own workflows.
Editor: review/approve human drafts; run/approve TET workflows; publish translations.
Admin: full CRUD for authors/works/users/config; run reindex/ingest/export.
High-level Architecture
Monolith: FastAPI app (sync views, async services) + Jinja2 templates + HTMX + Tailwind CSS.
DB: SQLite (WAL mode) via SQLAlchemy/SQLModel + Alembic migrations.
Background jobs: in-process task queue using FastAPI BackgroundTasks/ThreadPool + a jobs table (no Redis). Single-worker pattern sufficient for low traffic.
Search: SQLite FTS5 with Python pre-tokenization (jieba) for Chinese; unicode61 tokenizer for others.
File store (Git-tracked): content/works/... for long-form artifacts (markdown, JSON logs).
Providers: integrate existing vpsweb workflow (Hybrid/Reasoning/Non-Reasoning), configure via .env/YAML.
Canonical Entities and Provenance
Author
Work (poem)
Text (original text for a work in a language)
Translation (final publishable unit; may come from TET or human)
Workflow (TET session) and WorkflowStep (initial/editor/revision)
Users and Roles
Tags and tag links
Embeddings (optional, v1.1)
IDs, Slugs, and Language Codes
IDs: ULID strings (e.g., 01JF6H6X2A9MZ0K7J8Q4S4ZK6J) using ulid-py.
Slugs: ASCII kebab-case; uniqueness enforced per entity.
Languages: BCP 47 (e.g., en, zh-Hans, zh-Hant).
Storage Layout (Git-tracked artifacts)
content/
authors/{author_slug}/
bio.md (optional)
works/{author_slug}/{work_slug}{workULID}/
original.{lang}.md (or .tei.xml)
meta.yaml
translations/{lang}/
trans{ULID}_{YYYYMMDD-HHMMSS}/
final.md
record.json # canonical serialized translation + minimal workflow excerpt
tet_log.md # human-readable workflow log (if AI/hybrid)
The database is the source of truth for indices/queries; files are canonical artifacts for reproducibility/export.
Database Schema (SQLite + Alembic)
General conventions
Timestamps: ISO 8601 strings in UTC.
JSON fields: TEXT storing compact JSON.
Enable WAL and reasonable pragmas on startup.
Core tables (DDL sketch)

authors
id TEXT PRIMARY KEY,
name TEXT NOT NULL,
slug TEXT NOT NULL UNIQUE,
birth_year INTEGER NULL,
death_year INTEGER NULL,
nationality TEXT NULL,
aliases_json TEXT NULL,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL

works
id TEXT PRIMARY KEY,
author_id TEXT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
title TEXT NOT NULL,
canonical_slug TEXT NOT NULL UNIQUE,
original_language TEXT NOT NULL,
form TEXT NULL,
meter TEXT NULL,
rhyme_scheme TEXT NULL,
first_publication_year INTEGER NULL,
source_url TEXT NULL,
license TEXT NULL,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL

texts # store original or alternate-language canonical texts
id TEXT PRIMARY KEY,
work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
language TEXT NOT NULL,
format TEXT NOT NULL, # plain | markdown | tei
source_path TEXT NULL, # relative path in content/
text_md TEXT NOT NULL,
line_count INTEGER NOT NULL,
char_count INTEGER NOT NULL,
text_hash TEXT NOT NULL, # sha256 of normalized text
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL

users
id TEXT PRIMARY KEY,
name TEXT NOT NULL,
slug TEXT NOT NULL UNIQUE,
email TEXT NOT NULL UNIQUE,
password_hash TEXT NOT NULL,
role TEXT NOT NULL CHECK (role IN ('admin','editor','translator','viewer')),
is_active INTEGER NOT NULL DEFAULT 1,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL

translations
id TEXT PRIMARY KEY,
work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
source_text_id TEXT NULL REFERENCES texts(id) ON DELETE SET NULL,
target_language TEXT NOT NULL,
translator_type TEXT NOT NULL CHECK (translator_type IN ('human','ai','hybrid')),
translator_id TEXT NULL REFERENCES users(id) ON DELETE SET NULL,
source_session_id TEXT NULL, # references workflows(id), deferred creation order
version INTEGER NOT NULL DEFAULT 1,
is_published INTEGER NOT NULL DEFAULT 0,
license TEXT NULL,
text_md TEXT NOT NULL,
text_plain TEXT NOT NULL, # precomputed plain text for display/search
quality_rating REAL NULL,
tags_json TEXT NULL,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL

workflows
id TEXT PRIMARY KEY,
work_id TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
source_text_id TEXT NOT NULL REFERENCES texts(id) ON DELETE CASCADE,
target_language TEXT NOT NULL,
mode TEXT NOT NULL CHECK (mode IN ('reasoning','non_reasoning','hybrid')),
status TEXT NOT NULL CHECK (status IN ('pending','running','failed','completed','cancelled')),
providers_json TEXT NULL, # model/provider info as JSON
started_at TEXT NULL,
completed_at TEXT NULL,
total_tokens INTEGER NULL,
total_cost REAL NULL

workflow_steps
id TEXT PRIMARY KEY,
workflow_id TEXT NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
step_order INTEGER NOT NULL, # 1,2,3
step_type TEXT NOT NULL CHECK (step_type IN ('initial','editor_review','revision')),
model_provider TEXT NULL,
model_name TEXT NULL,
temperature REAL NULL,
tokens_used INTEGER NULL,
duration_sec REAL NULL,
notes_md TEXT NULL,
output_md TEXT NULL,
artifacts_path TEXT NULL, # relative path in content/ (logs, json)
created_at TEXT NOT NULL

tags
id TEXT PRIMARY KEY,
name TEXT NOT NULL,
slug TEXT NOT NULL UNIQUE,
type TEXT NOT NULL CHECK (type IN ('theme','form','era','movement','custom'))

work_tags (work_id, tag_id), translation_tags (translation_id, tag_id)

embeddings (v1.1 optional)
id TEXT PRIMARY KEY,
entity_type TEXT NOT NULL CHECK (entity_type IN ('work','translation','line')),
entity_id TEXT NOT NULL,
model_name TEXT NOT NULL,
dim INTEGER NOT NULL,
vector_json TEXT NOT NULL, # list[float]
created_at TEXT NOT NULL

Search (FTS5) tables

translations_fts (contentless FTS)
CREATE VIRTUAL TABLE translations_fts USING fts5(
translation_id, work_id, author_name, target_language,
title, text_tokenized, tags, tokenize='unicode61'
);

texts_fts
CREATE VIRTUAL TABLE texts_fts USING fts5(
text_id, work_id, author_name, language,
title, text_tokenized, tokenize='unicode61'
);

FTS maintenance

On insert/update/delete of translations and texts:
Pre-tokenize content for Chinese (jieba) and store into FTS tables.
For English/others, pass-through content into text_tokenized (unicode61 will segment).
Implement SQL triggers or handle synchronously in application service (simpler for SQLite):
On DB write, immediately upsert corresponding FTS rows.
SQLite pragmas (on startup)

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
Tokenization and Normalization
normalize_text(text):
Normalize line endings, strip trailing spaces, collapse multiple blank lines, trim BOM.
tokenize_for_fts(text, lang):
If lang startswith 'zh': jieba.cut(text, HMM=True) → ' '.join(tokens)
Else: return text (lowercased)
Note: Store both raw markdown and plain text; FTS uses tokenized plain text.
API Endpoints (REST, JSON; HTML views use same routes via HTMX partials)
Public
GET /authors
GET /authors/{id}
GET /works?author_id=&q=&tag=&page=
GET /works/{id}
GET /works/{id}/translations
GET /translations/{id}
GET /search?q=&lang=&type=work|translation&author=&tag=&form=&page=
GET /health
Auth

GET /login (HTML), POST /login (form)
POST /logout
Admin/Editor/Translator

POST /authors
POST /works
POST /texts
POST /translations (human draft)
PATCH /translations/{id} (update draft)
POST /translations/{id}/publish
POST /workflows (start TET)
GET /workflows/{id}
GET /workflows/{id}/steps
POST /workflows/{id}/finalize → creates Translation linked to workflow
POST /reindex (admin)
POST /ingest (admin) → trigger harvester on outputs/
POST /export-static (admin)
Request/Response examples

POST /workflows
Request:
{
"work_id": "01JF6H...",
"source_text_id": "01JF6H...",
"target_language": "zh-Hans",
"mode": "hybrid"
}
Response:
{ "id": "01JF6H...", "status": "pending" }

POST /translations (human draft)
Request:
{
"work_id": "01JF6H...",
"source_text_id": "01JF6H...",
"target_language": "zh-Hans",
"text_md": "...\n",
"license": "CC-BY-4.0",
"tags": ["semi-classical","defiant"]
}
Response: { "id": "01JF6K...", "is_published": false }

Web UI (Jinja2 + HTMX + Tailwind)
Pages
Home: recent translations, featured works.
Authors: list/detail.
Works: list, filters; work detail with:
Original text (select language)
Published translations list and view (side-by-side: original vs translation)
Metadata, tags, provenance.
Search: keyword + filters (author, language, translator type, tags, form).
TET Console (Editor/Translator):
Start workflow (select work, source text, target lang, mode).
Live progress: Step 1 → 2 → 3 with model info, tokens, durations.
Approve/adjust notes; finalize to publish.
Human Translation Studio (Translator):
Draft editor (Markdown), optional line-by-line side-by-side view.
Save draft, submit for review (Editor approves to publish).
Admin:
CRUD for authors/works/users/tags.
Ingest outputs/, reindex search, export static.
HTMX interaction patterns

hx-get/hx-post for partial updates (e.g., publish button updates translation card).
Long-running tasks: poll /workflows/{id} via hx-trigger="every 2s" until completed.
Validation errors return partials to form targets.
Integration with Existing vpsweb Workflow
Service adapter: app/services/workflow_runner.py
run_tet(work_id, source_text_id, target_language, mode) → creates workflow + steps.
Calls vpsweb.core.workflow.TranslationWorkflow with configured providers.
Writes artifacts:
record.json (raw result)
tet_log.md (pretty)
final.md (from revised_translation)
Updates DB: workflows, workflow_steps, translations (on finalize).
Map fields from sample outputs:
initial_translation, editor_review, revised_translation, tokens, durations.
Ingestion (Harvester) for existing outputs/
scripts/ingest_outputs.py
Process
Walk outputs/translation_*.json and paired markdown/log files.
Normalize author/work by (author name, title, text_hash).
Create or upsert:
Author, Work, Text (original), Workflow, WorkflowSteps.
Translation from revised_translation, mark source_session_id and translator_type='ai'.
Compute text_hash for original (if available in record/json).
Write artifacts into content/works/{author_slug}/{work_slug}{ULID}/translations/{lang}/trans{ULID}_{timestamp}/...
Idempotent upsert: use text_hash and timestamps; skip duplicates.
Log summary to console + DB.
Background Jobs (no external queue)
Job types: run_tet, reindex, ingest, export_static.
jobs table:
id, type, status, payload_json, started_at, completed_at, result_json, error_text.
Dispatcher: ThreadPoolExecutor(max_workers=1-2) to serialize DB writes safely.
API returns job/workflow IDs; UI polls until completion.
Search Strategy (SQLite FTS5)
For translations and texts:
Store tokenized content in FTS tables.
Chinese: jieba tokenization; Others: unicode61; lowercase.
Ranking: use bm25(fts) and display snippets with highlighted matches.
Filters: author, language, translator_type, date range, tags, form.
For zh queries: also tokenize query via jieba before FTS MATCH.
Fallback substring search for edge cases: LIKE '%q%'.
Optional Semantic Search (v1.1)
Embeddings computed by a multilingual model (e.g., bge-m3-small or e5-multilingual-small) offline.
Store vectors in embeddings.vector_json (list[float]).
Similarity computed in Python (NumPy) for low traffic.
API: GET /related?entity=translation&id=... returns top-k neighbors.
Security and Auth
Session-based auth (Signed cookie, itsdangerous) + CSRF token on forms.
Password hashing: passlib (bcrypt).
RBAC by role; decorator or dependency to enforce access.
Rate limiting not required (low traffic); audit logs for admin actions.
Configuration (.env + YAML)
.env
DATABASE_URL="sqlite:///./app.db"
SECRET_KEY="..."
ADMIN_EMAIL, ADMIN_PASSWORD (bootstrap)
CONTENT_ROOT="./content"
PROVIDERS_JSON='{"tongyi": {...}, "deepseek": {...}}'
LOG_LEVEL="INFO"
Optional: config/providers.yaml for model defaults and pricing.
Cost and Token Tracking
Per workflow step: store tokens_used, duration_sec, model info, and computed RMB cost using provider pricing table.
Workflow aggregates: total_tokens, total_cost.
Display in TET Console and workflow pages.
Directory Structure
project-root/
app/
main.py
config.py
dependencies.py
security.py
db/
base.py
models.py # SQLModel definitions
migrations/ # Alembic
init_db.py
routers/
authors.py
works.py
texts.py
translations.py
workflows.py
search.py
admin.py
auth.py
services/
workflow_runner.py
tokenization.py
search_index.py
storage.py # file paths/artifacts
ingest.py
export_static.py
utils.py
templates/
base.html
authors/.html
works/.html
translations/.html
workflows/.html
admin/.html
partials/.html # HTMX fragments
static/
css/
js/
content/ # Git-tracked artifacts (generated + curated)
scripts/
ingest_outputs.py # CLI wrapper around services.ingest
reindex_search.py
export_static.py
alembic.ini
requirements.txt or pyproject.toml
package.json (if Tailwind build used)
.env.example
README.md

Tailwind + UI

Option A (no Node): Use Tailwind CDN for v1 (acceptable for low traffic).
Option B (recommended): Tailwind CLI build:
npm run dev: tailwind -i static/css/input.css -o static/css/app.css --watch
npm run build: tailwind -i static/css/input.css -o static/css/app.css --minify
Minimal components: Side-by-side view, form controls, badges, tables.
Implementation Milestones
Phase 0: Foundation (1–2 weeks)
Set up FastAPI app, SQLModel, Alembic, auth, roles.
Define schema and migrations.
Implement storage paths + ULID/slug utilities.
Enable SQLite WAL + pragmas.
Phase 1: Core Repository (1–2 weeks)

CRUD: Authors, Works, Texts.
Public views: author/work/translation pages, side-by-side view.
Search: FTS5 + tokenization pipeline (jieba).
Admin UI for tags; publish/unpublish translations.
Phase 2: TET Workflow + Ingestion (2–3 weeks)

Integrate vpsweb workflow_runner with providers.
TET Console with live progress, tokens, cost, finalize to publish.
Ingest existing outputs/ (JSON + markdown) into DB + content/ tree.
Phase 3: Human Translation Studio (1–2 weeks)

Draft editor, save/submit for review, version bumps, publish flow.
Diffs (basic markdown diff), quality rating, provenance block.
Phase 4: Polish (1–2 weeks)

Static export of published content for CDN.
Pagination, breadcrumbs, breadcrumbs, 404s, error pages.
Tests and CI (pytest + coverage), linting.
Testing Plan
Unit tests:
Slug/ULID, text normalization, tokenization (zh/en).
FTS upsert, search queries, filters.
Workflow mapping from vpsweb outputs to DB models.
Integration tests:
Ingest pipeline on sample files (provided in your outputs).
Run a TET workflow (mock providers) and finalize translation.
Auth + RBAC route protections.
UI tests:
HTMX flows (publish, search, start workflow, polling).
Data integrity:
Uniqueness (slugs), foreign key constraints, cascade deletes.
Performance:
Search under small dataset (1k translations) < 200ms.
Acceptance Criteria (v1)
Can ingest provided outputs into DB + content/ with idempotency.
Can browse by author/work; view original and translations side-by-side.
Full-text search works for English and Chinese with filters.
Can start a TET workflow, track steps, finalize, and publish a translation; artifacts are saved.
Human translator can create/edit a draft and submit; editor can publish.
Provenance: translation shows translator_type, source_session_id (if any), license, timestamps, tags.
All write actions logged; admin can export static site.
Pydantic/SQLModel Sketch
from typing import Optional, Literal
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
class Author(SQLModel, table=True):
id: str = Field(primary_key=True)
name: str
slug: str
birth_year: Optional[int] = None
death_year: Optional[int] = None
nationality: Optional[str] = None
aliases_json: Optional[str] = None
created_at: str
updated_at: str

class Work(SQLModel, table=True):
id: str = Field(primary_key=True)
title: str
author_id: str = Field(foreign_key="author.id")
canonical_slug: str
original_language: str
form: Optional[str] = None
meter: Optional[str] = None
rhyme_scheme: Optional[str] = None
first_publication_year: Optional[int] = None
source_url: Optional[str] = None
license: Optional[str] = None
created_at: str
updated_at: str

class Text(SQLModel, table=True):
id: str = Field(primary_key=True)
work_id: str = Field(foreign_key="work.id")
language: str
format: str
source_path: Optional[str] = None
text_md: str
line_count: int
char_count: int
text_hash: str
created_at: str
updated_at: str

class Translation(SQLModel, table=True):
id: str = Field(primary_key=True)
work_id: str = Field(foreign_key="work.id")
source_text_id: Optional[str] = Field(default=None, foreign_key="text.id")
target_language: str
translator_type: Literal["human", "ai", "hybrid"]
translator_id: Optional[str] = Field(default=None, foreign_key="user.id")
source_session_id: Optional[str] = None
version: int = 1
is_published: bool = False
license: Optional[str] = None
text_md: str
text_plain: str
quality_rating: Optional[float] = None
tags_json: Optional[str] = None
created_at: str
updated_at: str

Key Algorithms and Utilities
text_hash: sha256 of normalized text_md (strip markup if desired).
slugify: ASCII kebab-case; dedupe with numeric suffix if conflict.
language utils: validate BCP 47; normalize zh-Hans/zh-Hant.
tokenizer: jieba for zh; lowercase for others; configurable stopword removal (optional).
FTS upsert: replace into translations_fts/texts_fts on each write.
Error Handling and Observability
Structured logs (JSON optional) with request_id; rotating file logs.
Exception handlers returning user-friendly HTML/JSON.
Detailed job/workflow logs (status, durations) persisted.
4xx/5xx templates.
Licensing and Attribution
Default license for AI outputs: CC-BY-4.0 (configurable).
Human submissions require explicit license selection at submission.
Provenance block on translation pages includes translator_type, user (if any), workflow id, and model info snapshot.
Static Export (optional v1)
scripts/export_static.py renders published works/translations to HTML files under public_site/.
Includes sitemap.xml and RSS for newly published translations.
Open Questions (decide during implementation)
Do we include line-level alignment UI in v1 or v1.1?
Tailwind build: CDN-only or CLI (recommended)?
Minimal markdown extensions (code highlighting not required).
Initial Tasks for Claude Code
Bootstrap FastAPI app with Jinja2, HTMX, Tailwind (CDN).
Implement DB models and Alembic migrations.
Auth and RBAC middleware.
CRUD for authors/works/texts (HTML + JSON).
Search service with FTS5 + jieba pre-tokenization; indexer on write.
Public views (author/work/translation) with side-by-side rendering.
TET workflow_runner service stub that logs fake steps (replace with vpsweb integration in step 2).
Ingestion script against sample outputs provided.
Admin actions (publish/unpublish, reindex).
Sample Config (.env)
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=CHANGE_ME
CONTENT_ROOT=./content
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme
PROVIDERS_JSON={"tongyi":{"api_key_env":"TONGYI_API_KEY","base_url":"https://dashscope.aliyuncs.com/compatible-mode/v1"},"deepseek":{"api_key_env":"DEEPSEEK_API_KEY","base_url":"https://api.deepseek.com/v1"}}
LOG_LEVEL=INFO

Mapping Example from Provided Output

Work: "First Fig" (en), author "Edna St. Vincent Millay"
Text: original English from the JSON (if stored) or create from source file; compute text_hash
Workflow: mode=hybrid; providers_json as per JSON; steps: initial/editor/revision with tokens/durations
Translation: revised_translation.text_md, target_language=zh-Hans, translator_type='ai', is_published=true
Artifacts: write final.md, record.json, tet_log.md to content tree
Appendix A: Minimal SQL for FTS tables
CREATE VIRTUAL TABLE translations_fts USING fts5(
translation_id, work_id, author_name, target_language,
title, text_tokenized, tags, tokenize='unicode61'
);

CREATE VIRTUAL TABLE texts_fts USING fts5(
text_id, work_id, author_name, language,
title, text_tokenized, tokenize='unicode61'
);

Appendix B: Example HTMX Snippet (Publish Button)
<button hx-post="/translations/{{ t.id }}/publish" hx-target="#translation-{{ t.id }}" hx-swap="outerHTML" class="btn btn-primary">
Publish
</button>

Appendix C: Example Tokenization
def tokenize_for_fts(text: str, lang: str) -> str:
import re
t = text.replace('\r\n', '\n').strip().lower()
if lang.startswith('zh'):
import jieba
return ' '.join(jieba.cut(t, HMM=True))
return t