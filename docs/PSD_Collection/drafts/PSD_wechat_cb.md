vpsweb — WeChat Article Generation & Publishing — Project Specification
Summary
Add two CLI commands to vpsweb:

vpsweb generate-article: generate a WeChat-ready article from an existing translation JSON; synthesize concise, reader-oriented publication notes (target: general readers); optionally auto-generate a cover image.
vpsweb publish-article: upload the generated article to the user's WeChat Official Account Drafts (草稿) for manual review/publish.
This spec covers CLI behavior, internal modules, data-model changes, WeChat integration details, image generation, tests, configuration, security, error handling, and an implementation checklist.

Goals & Rationale
Automate transforming translation workflow outputs into polished, publication-ready WeChat articles while preserving editorial integrity.
Keep translator workflow and publication responsibilities decoupled: create publication notes during generate-article (user preference).
Provide safe, configurable publishing that deposits content into Drafts for final human review.
High-level Architecture
CLI (click): new commands in src/vpsweb/__main__.py.
Article generation module: src/vpsweb/utils/article_generator.py.
WeChat API client: src/vpsweb/services/wechat/client.py.
Optional image generation integration: reuse existing LLM/image provider abstractions under src/vpsweb/services/llm or add services/images.
Storage and assets under outputs/articles/{timestamp}_{workflow_id8}/.
Data model changes (persistent metadata)
Modify and extend existing metadata fields (in TranslationInput.metadata and persisted in TranslationOutput) to support publication needs:

New metadata keys (optional, recommended):
poem_title: str
author_name: str
source_reference: str (e.g., book/URL)
original_publication_year: int | null
copyright_status: enum {public_domain, licensed, unknown}
tags: List[str] (themes/keywords)
audience_level: enum {general, scholarly} (default: general)
wechat_digest: str | null (optional digest override)
cover_prompt: str | null (hint for auto image generation)
article_series: str (default: "知韵译诗")
Generated (derived) fields stored in metadata or in article meta:
publication_notes: str (concise 120–200 Chinese characters recommended)
inferred_title, inferred_author (if poem_title/author_name absent)
Rationale: these fields enable deterministic article formation, better cover prompts, and reuse.

CLI Design
Command: vpsweb generate-article
Purpose: create WeChat-ready article (HTML + optional markdown preview + assets + meta).
Usage
vpsweb generate-article -j /path/to/translation.json [options]
Options
--json / -j PATH (default: latest translation JSON in outputs/)
--format [html|markdown|both] (default: html)
--title-override TEXT
--cover [auto|none|/path/to/image] (default: auto)
--digest TEXT (optional override)
--outdir / -o PATH (default: outputs/articles)
--cover-style TEXT (optional style preset for image generator)
--no-cache (skip reusing cached generated cover)
--verbose / -v
Behavior
Locate and load translation JSON via StorageHandler.load_translation.
Infer title and author if missing (see inference rules).
Synthesize publication_notes targeted to general readers (concise, ~120–200 chars / 3–5 bullet points). Use revised_translation.revised_translation_notes, initial_translation.initial_translation_notes, and editor_review.editor_suggestions as sources.
Build article HTML optimized for WeChat rendering with sections:
Header/title: 【知韵译诗】诗歌名（诗人名）
Subtitle: source → target language
原诗: original poem preserved with line breaks ( or preserved )
终稿译文: final translation
翻译札记: synthesized publication notes (reader-friendly)
Footer: standard copyright disclaimer
Optionally generate or copy cover image:
auto: call image generation routine and save to outdir
path: copy user image
Save outputs:
article.html (WeChat-compatible HTML)
article.md (markdown preview)
cover.jpg/png (if generated)
meta.json with: title, digest, author, thumb_media_id (placeholder), created_at, workflow_id, article_paths
Print summary and paths to created files.
Command: vpsweb publish-article
Purpose: upload article to WeChat Drafts (草稿) for manual review/publish.
Usage
vpsweb publish-article -a /path/to/article/meta.json [options]
Options
--article / -a PATH (article meta.json or article.html)
--cover / -c PATH (optional; will be uploaded if not present in meta)
--digest TEXT (optional override)
--show-cover-pic [0|1] (default 1)
--wechat-profile KEY (select profile if multi-account config)
--dry-run (shows payload without sending)
--verbose
Behavior
Load meta.json or infer required fields from article.html + translation JSON.
Instantiate WeChatClient with credentials from config or environment.
Fetch access_token (with caching).
Upload cover via /cgi-bin/media/upload?type=image to get thumb_media_id if needed.
Upload inline images (if article contains images) via /cgi-bin/media/uploadimg and replace URLs.
Build draft/add payload (single-article array supported):
title, author (from meta or inferred), digest, content (HTML), thumb_media_id, show_cover_pic.
Call WeChat draft/add endpoint; on success save draft_id and response to meta.json.
Return draft id and URL (if available) for manual review.
Article Content & Formatting (WeChat best practices)
Title: exactly 【知韵译诗】{poem_title}（{author_name}） — fallback to inferred values.
Digest: 120–200 Chinese characters, no emojis by default. If user not provided, auto-generate from synthesized notes.
HTML constraints for WeChat:
Avoid external CSS/JS. Use inline minimal styles.
Prefer semantic tags: /, , , for poems, with absolute URLs (WeChat-hosted).
Preserve original line breaks in poem and translation (use or ).
Keep images <= 1080px width; deliver moderate size to avoid upload failures.
Translation Notes:
Deliver 3–5 short paragraphs or bullet points targeted at general readers:
What translator preserved (tone, image)
Key change choices (title, idioms)
How to read the translation (ritual)
Keep neutral, explanatory, not academic.
Footer (copyright)
Standard text in Chinese (template provided):
“本文译文与评论为【知韵译诗】原创内容。原诗版权归原作者或版权方所有，本篇发布仅用于学习与交流。若涉及版权问题，请联系公众号后台，我们将及时处理。”
Implementation Modules
utils/article_generator.py
Responsibilities:
Load TranslationOutput model.
Infer metadata (title, author) when missing.
Synthesize publication_notes targeted to general readers (algorithm outlined below).
Render WeChat-compatible HTML and markdown preview.
Manage local assets (cover, inline images).
Public API:
ArticleBundle generate_from_translation(translation_output: TranslationOutput, opts) -> ArticleBundle
ArticleBundle contains: title, digest, html_path, md_path, cover_path, meta_path
Key helpers:
infer_title_author(input.original_poem, input.metadata)
synthesize_publication_notes(revised_notes, initial_notes, editor_suggestions) -> str
render_wechat_html(bundle) -> str
sanitize_html_for_wechat(html) -> str
Notes on synthesis algorithm:

Prefer revised_translation.revised_translation_notes for decisions.
Extract 3–5 key points by:
Searching for sentences containing keywords: title, idiom, imagery, tone, rhyme, rhythm, cultural.
If not found, compress paragraphs using summarization prompt (use existing LLM service) tuned for plain-language Chinese, length target 120–200 chars.
Guarantee readable output: short sentences, plain vocabulary.
services/wechat/client.py
Responsibilities:
Get/refresh access_token (cache to file/memory).
Upload image: POST to /cgi-bin/media/upload?type=image (returns media_id).
Upload inline images: /cgi-bin/media/uploadimg (returns URL to use in article HTML).
Add draft: /cgi-bin/draft/add with article(s) payload.
Implementation notes:
Respect WeChat API error codes and refresh tokens when necessary.
Use config: WECHAT_APPID, WECHAT_SECRET, optional wechat_profile mapping in config file.
Expose a publish_draft(article_payload) method returning WeChat response with draft_id.
Implement robust retry/backoff for network transient errors.
services/images (optional)
Responsibilities:
Interface to configured image generation model/provider.
Provide generate_cover(prompt, style, size) -> path
Integration:
Use existing services/llm factory/provider if image model exists; otherwise add a small provider wrapper.
Configuration & Secrets
Config locations: existing config loader (src/vpsweb/utils/config_loader.py) and .env.
New config keys:
main.publish.wechat_profiles: mapping names -> {appid, secret}
main.publish.default_profile: string
main.features.auto_cover: boolean
providers.images: provider config for cover generation
Secrets:
WECHAT_APPID, WECHAT_SECRET may be supplied through config or environment variables.
Never commit secrets to repo. Use .env and docs to set in deployment.
Error Handling & Safety
All network/publishing operations should be guarded and offer clear fail-safe:
publish-article must support --dry-run to validate payload locally.
If article upload fails, no deletion of local assets; add clear logging and save WeChat response into meta.json.
For image generation failures, fall back to no cover with warning.
Rate limiting:
Cache access_token and reuse until expiry.
Retry with exponential backoff for HTTP 5xx and network errors. Respect WeChat API rate limits.
User privacy & copyright:
Add clear disclaimer in footer.
Provide opt-out if copyright_status == licensed (flag warn).
Do not publish automatically — push to Drafts only.
Testing Strategy
Unit tests:
article_generator.infer_title_author: test with sample JSONs (with/without metadata).
article_generator.synthesize_publication_notes: assert length and presence of keyphrases; mock LLM responses.
wechat.client: mock HTTP responses to test payload creation, token refresh, image upload flows.
Integration tests:
CLI generate-article on provided sample JSON (tests/integration/test_article_cli.py): assert files produced, meta.json content, title format.
publish-article: use a local HTTP server mocking WeChat endpoints; verify requests for image upload and draft/add, and that meta.json is updated with returned draft_id.
Fixtures:
Use provided outputs/translation_reasoning_20251007_150804_400fab4e.json as canonical fixture.
Test coverage expectations:
80% coverage for new modules; critical path: payload building and file I/O should be thoroughly tested.
Security & Privacy
Never log secrets (appid/secret, access tokens).
Sanitize uploaded HTML: remove , style blocks, inline event handlers before sending to WeChat.
Validate cover image files for size and MIME type before upload.
Maintain local audit trail: meta.json should store timestamps and WeChat responses for accountability.
Implementation Plan & Tasks (Suggested order)
Data model: extend TranslationInput.metadata schema and TranslationOutput.to_dict() handling (backwards compatible).
Article generator:
Implement utils/article_generator.py with inference, synthesis (LLM call optional), and HTML/markdown rendering.
Implement unit tests for inference/synthesis/rendering.
CLI wiring:
Add generate-article command to src/vpsweb/__main__.py.
Use existing StorageHandler to load translation by path or pick latest.
Image generation (optional):
Implement services/images wrapper or integrate in article_generator with existing LLM providers.
Add config toggles.
WeChat client:
Implement services/wechat/client.py (access token, upload, draft/add).
Implement publish-article CLI that uses WeChat client.
Add integration tests with mocked WeChat endpoints.
Documentation:
CLI usage, config keys, environment variables, privacy and copyright notes.
Example: generate article from provided sample JSON and publish dry-run.
Tests & CI:
Add tests and ensure they run in CI; mock external network calls in tests.
Release:
Bump version; add changelog; provide example outputs under examples/.
Estimated implementation time (single experienced engineer):

Core (generate-article, article_generator, tests): 2–3 days
WeChat client & publish-article + tests: 2–3 days
Image generation & polish: 1–2 days
Docs & minor fixes: 0.5–1 day
Example Output Layout (on disk)
outputs/
articles/
20251012_170501_08fd15a4/
article.html
article.md
cover.jpg
meta.json
meta.json example:
{
"workflow_id": "08fd15a4-8d7c-46f0-a6fd-c4e8d8c75dcf",
"title": "【知韵译诗】First Fig（Edna St. Vincent Millay）",
"digest": "简短摘要（120-200字）",
"author": "Translator Name or Inferred",
"thumb_path": "cover.jpg",
"thumb_media_id": null,
"draft_id": null,
"created_at": "2025-10-12T17:05:01Z",
"paths": {
"html": "outputs/articles/.../article.html",
"md": "outputs/articles/.../article.md",
"cover": "outputs/articles/.../cover.jpg"
}
}

Examples: Title/Notes Inference Rules
Title: detect first line like "First Fig" or a "Title\nby Author" pattern. If metadata.poem_title exists, use it.
Author: prefer input.metadata.author_name, else look for "by" line: regex r"(?m)^by\s+(.+)$".
Publication notes generation:
If revised_translation.revised_translation_notes is present, extract top 3 sentences mentioning "title", "idiom", "tone", "culture", "rhyme".
Else call summarizer LLM to produce a 3-sentence, reader-friendly paragraph.
Acceptance Criteria
generate-article produces WeChat-compatible HTML with required sections and meta.json; titles match the 【知韵译诗】... format.
publication_notes are concise and aimed at general readers.
publish-article uploads the article to WeChat Drafts and saves returned draft_id in meta.json when credentials are valid.
Tests cover inference, rendering, and mocked publish flows.