# vpsweb WeChat Article Generation & Publishing — Project Specification Document (PSD)

Author: 施知韵VoxPoetica
Date: 2025-10-12
Status: Approved specification

## 1. Overview

Extend vpsweb to:
- Generate a WeChat Official Account (微信公众号) article from previous vpsweb translate JSON output.
- Publish the generated article to the WeChat Official Account Drafts (草稿) for manual review and later publishing.

Command additions:
- vpsweb generate-article
- vpsweb publish-article

Key decisions:
- Cover image requirement is dropped (no thumb_media_id usage).
- Credentials stored in config/wechat.yaml.
- Digest length default 80–120 chars.
- Slug format: poetname-poemtitle-YYYYMMDD.

## 2. Goals and Non-goals

Goals:
- Professional, readable, elegant WeChat-friendly HTML article.
- Sections: Title, Original Poem, Final Translation, Translation Notes (concise), Disclaimer.
- Robust metadata extraction (poem_title, poet_name, series index).
- Reliable WeChat Draft creation via official API.
- Dry-run capability for both commands.

Non-goals:
- No cover image handling (thumb_media_id not used).
- No auto-scheduling; we only provide guidance (user can schedule externally).
- No login flows or web UI in this phase.

## 3. Input Artifacts

Primary source: outputs/*.json from vpsweb translate.
Prefer congregated_output fields when available:
- original_poem (includes title, author line, and text)
- revised_translation (final translation)
- revised_translation_notes / initial_translation_notes
- editor_suggestions
- workflow_id, workflow_mode, metrics

## 4. Output Artifacts

On generate-article:
- outputs/wechat/articles/{slug}/article.html
- outputs/wechat/articles/{slug}/metadata.json
  - title
  - slug
  - author (default: 施知韵VoxPoetica)
  - digest (80–120 chars, auto-generated if not provided)
  - source_json_path
  - created_at (ISO8601)

On publish-article:
- outputs/wechat/articles/{slug}/publish_result.json
  - draft_id (if returned)
  - request payload (sanitized)
  - response status and message
  - timestamp

## 5. Title and Slug

Title format:
- 【知韵译诗】{poem_title}（{poet_name}）

Slug format:
- poetname-poemtitle-YYYYMMDD
- Normalization rules:
  - Lowercase ASCII; remove punctuation; spaces -> hyphens; Chinese kept as-is for display, but slug normalized using pinyin or safe ASCII transliteration if needed. If transliteration unavailable, keep ASCII-only fallback with hash suffix.

## 6. Article Structure and HTML Design

WeChat-compatible HTML principles:
- Minimal inline CSS; no external styles/scripts.
- Semantic structure; readable typography; preserved line breaks for poetry.

HTML sections:
- H1: Title
- Small: author line “作者：施知韵VoxPoeticaStudio”
- HR
- H2: 原诗
  - Poem displayed with <pre> or <div style="white-space:pre-wrap"> to preserve line breaks.
- H2: 英译
  - Final translation (revised_translation)
- H2: 译注
  - Concise bullet list (3–6 bullets) summarizing key decisions:
    - Corrections (e.g., 桑麻 -> mulberry and hemp)
    - Lexical choices (白日 -> by day; 虛室 -> empty room metaphor)
    - Rhythm/meter and rhyme decisions
    - Imagery and cultural fidelity
- HR
- Small: 版权声明
  - “本译文与导读由【知韵译诗】施知韵VoxPoetica原创制作。未经授权，不得转载。若需引用，请注明出处。”

Inline CSS defaults:
- body: font-size: 16px; line-height: 1.8; color: #222;
- h1: font-size: 22px; margin: 12px 0;
- h2: font-size: 18px; margin: 16px 0 8px;
- pre/div poetry: font-family: serif; margin: 8px 0;
- li: margin: 4px 0;
- small: color: #666;

## 7. Translation Notes Summarization

Notes source:
- initial_translation_notes
- revised_translation_notes
- editor_suggestions

Heuristics:
- Extract key corrections and decisions; deduplicate.
- Limit to 3–6 bullets; each bullet <= 160 chars.
- Prefer concrete changes (term fixes, imagery preservation, rhythm choices).
- Create digest (80–120 chars) summarizing the translation outcome and theme.

## 8. CLI Specification

### 8.1 vpsweb generate-article

Usage:
- vpsweb generate-article --input-json PATH [--output-dir PATH] [--author STR] [--digest STR] [--dry-run]

Options:
- --input-json PATH: Required; points to outputs/*.json.
- --output-dir PATH: Optional; default outputs/wechat/articles/{slug}/.
- --author STR: Optional; default “施知韵VoxPoetica”.
- --digest STR: Optional; if absent, auto-generate (80–120 chars).
- --dry-run: Optional; perform rendering only; write files; no external network calls.

Behavior:
- Parse JSON; prefer congregated_output; fallback to top-level fields.
- Extract poem_title, poet_name, series index (“其二” etc.).
- Render article HTML; write metadata.json.
- Print summary: title, slug, output paths.

### 8.2 vpsweb publish-article

Usage:
- vpsweb publish-article --article-html PATH [--author STR] [--digest STR] [--config PATH] [--dry-run]

Options:
- --article-html PATH: Required; points to generated article.html.
- --author STR: Optional; default “施知韵VoxPoetica”.
- --digest STR: Optional; if absent, use metadata.json or auto-generate.
- --config PATH: Optional; default config/wechat.yaml.
- --dry-run: Optional; show payload; no API calls.

Behavior:
- Load config/wechat.yaml; fetch access_token.
- Prepare draft payload (no cover image):
  - title
  - author
  - digest
  - content (HTML)
  - content_source_url (optional, omitted by default)
- POST to /cgi-bin/draft/add; persist response to publish_result.json.
- Print success with draft_id; otherwise show error with guidance.

## 9. WeChat Official Account API Integration

Config file: config/wechat.yaml
- appid: "YOUR_APPID"
- secret: "YOUR_SECRET"
- base_url: "https://api.weixin.qq.com"
- timeouts:
  - connect: 5s
  - read: 20s
- retry:
  - attempts: 3
  - backoff: exponential (0.5, 1, 2s)

Token management:
- GET /cgi-bin/token?grant_type=client_credential&appid=APPID&secret=SECRET
- Cache to outputs/.cache/wechat_token.json with expiry.

Draft creation:
- POST /cgi-bin/draft/add
- Payload:
  {
    "articles": [{
      "title": "...",
      "author": "...",
      "digest": "...",
      "content": "<html>...</html>",
      "content_source_url": ""
    }]
  }

Image handling:
- No cover image (thumb_media_id) per spec.
- Inline images (if any) are optional and not required in current renderer; future versions may use /cgi-bin/media/uploadimg to obtain WeChat-hosted URLs.

Rate limits and errors:
- Handle known errcodes: 40001 (invalid token), 45009 (rate limit), 40003 (invalid openid) – log and guide remediation.
- Retry token once on 40001.

## 10. Modules and Responsibilities

New modules:
- services/wechat_mp.py
  - get_access_token()
  - add_draft(title, author, digest, content_html)
  - config loading, retries, caching

- utils/article_renderer.py
  - parse_metadata_from_json(json_path)
  - render_html_article(data, author, digest)
  - generate_digest_if_missing(data)
  - generate_slug(poet_name, poem_title, date)

- utils/notes_summarizer.py
  - summarize_notes(initial_notes, revised_notes, suggestions) -> bullets[], digest

CLI extensions (src/vpsweb/__main__.py):
- @cli.command() generate-article
- @cli.command() publish-article

## 11. Data Model Extensions (Optional in translate workflow)

Enhance translation JSON (optional for future runs):
- metadata.poem_title
- metadata.poet_name
- metadata.series_index
- metadata.slug
- metadata.translation_notes_summarized
- metadata.article_digest
- metadata.suggested_publish_date
- metadata.tags
These can be added during save or via a post-processing step.

## 12. Security and Configuration

- Do not hardcode secrets; use config/wechat.yaml not committed with real values.
- Consider environment variable overrides for appid/secret (WECHAT_APPID, WECHAT_SECRET).
- Token cache stored locally; ensure permissions.

## 13. Testing Strategy

Unit:
- notes_summarizer heuristics, digest length bounds
- metadata extraction from sample JSON
- HTML renderer output (structure, sections)

Integration:
- Mock HTTP for token and draft/add
- CLI flows with dry-run and real file outputs

Manual:
- Render article for sample JSON
- Publish with test account; verify draft appears and content formatting in WeChat editor

## 14. Migration and Backward Compatibility

- Works with existing outputs/*.json; uses congregated_output when present, falls back safely.
- No impact on vpsweb translate command behavior.

## 15. Operational Guidance

- Daily publish: use system scheduler (cron/launchd). Example cron:
  - Run generate-article for newest JSON; then publish-article.
- Log outputs in outputs/wechat/; keep drafts tracked via publish_result.json.

## 16. Acceptance Criteria

- generate-article creates HTML + metadata with correct title, slug, sections, disclaimer.
- publish-article successfully creates a WeChat Draft (visible in account) without requiring a cover image.
- Digest defaults to 80–120 chars when not provided.
- Config loaded from config/wechat.yaml; token cached; dry-run works.
- Tests pass; sample JSON produces expected article.

## 17. Future Enhancements (Out of scope)

- Inline image upload and URL replacement
- Multi-article batches
- Rich footnotes or glossary sections
- Scheduling helper command