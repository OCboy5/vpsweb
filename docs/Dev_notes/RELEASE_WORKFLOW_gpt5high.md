vpsweb — Streamlined Release Workflow (VERSION_WORKFLOW.md)
A concise, GitHub‑compliant release process that Claude Code can follow reliably. Uses semantic versioning and GitHub CLI.

0) Prerequisites
GitHub CLI installed and authenticated:
gh auth status
Clean working tree on main:
git status (no changes)
git pull origin main
Python tooling available:
Black and pytest installed (e.g., pip install black pytest)
Scripts available in repo:

./save-version.sh X.Y.Z (optional local backup)
./push-version.sh X.Y.Z "Release notes" (official release)
Note: push-version.sh handles existing tags gracefully
1) Pre‑Release Checklist (must pass)
Version bump done and consistent across all files:
pyproject.toml → version = "X.Y.Z"
src/vpsweb/init.py → version = "X.Y.Z"
src/vpsweb/main.py → version_option(version="X.Y.Z")
Quick check:
grep -R 'X.Y.Z' src/ pyproject.toml
Docs updated (as applicable):
README.md, CHANGELOG.md, CLAUDE.md, STATUS.md, DEVELOPMENT.md, etc.
Code formatting passes:
python -m black --check src/ tests/
Tests pass locally:
pytest -q
Commit all changes to main:
git add .
git commit -m "Release vX.Y.Z"
git push origin main
2) Standard Release Flow (recommended path)
Optional local backup (safety net)
Bash

./save-version.sh X.Y.Z
Create the official GitHub release (tag + release)
Bash

./push-version.sh X.Y.Z "Brief release notes: highlights, features, fixes"
push-version.sh will:
Create or reuse annotated tag vX.Y.Z
Push tag to origin
Create GitHub Release via gh release create
Provide helpful messages if tag/release already exists
3) Post‑Release Verification
Run these checks immediately after the release:

Bash

# Release exists on GitHub
gh release view vX.Y.Z

# Tag exists on remote
git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$" || echo "Tag missing on remote"

# CI/CD status (open in browser)
# https://github.com/OCboy5/vpsweb/actions
# Release page:
# https://github.com/OCboy5/vpsweb/releases/tag/vX.Y.Z
If CI fails:

Fix issues, push commits to main.
If needed, edit the GitHub Release notes via gh or web UI.
4) Fallback: Manual Release (only if the script fails)
Ensure tag exists locally and remotely
Bash

git tag -a vX.Y.Z -m "vX.Y.Z"  # if not already created
git push origin vX.Y.Z
Create GitHub Release manually
Bash

gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"
Verify (same as Post-Release Verification)
5) Rollback / Recovery
Delete local tag and recreate:
Bash

git tag -d vX.Y.Z
git tag -a vX.Y.Z -m "vX.Y.Z"
Delete remote tag (if necessary):
Bash

git push --delete origin vX.Y.Z
If you used local backup:
Bash

# List local backups
git tag -l "*local*"

# Check out a local backup (example)
git checkout v0.1.0-local-2025-10-05
6) Release Notes — Minimal Template
Use concise, high-signal notes. Example:

text

### Highlights
- New: WeChat article generator (generate-article) and publisher (publish-article)
- Improved: Translation repository schema and ingestion stability
- Fix: Better error handling for existing tags in push-version.sh

### Details
- CLI: vpsweb generate-article/publish-article with WeChat-compatible HTML and drafts API
- DB: SQLite FTS5 indexing fixes and tokenization tweaks
- Docs: Updated README and VERSION_WORKFLOW

### Compatibility
- No breaking changes to existing outputs/*.json
7) Versioning Rules (SemVer)
Major (X.0.0): Breaking changes
Minor (x.Y.0): New features, backwards compatible
Patch (x.y.Z): Fixes and small improvements
Tags: vX.Y.Z (e.g., v0.2.1)

8) Quick Reference (TL;DR)
Bash

# 0) Preconditions
gh auth status
git status
python -m black --check src/ tests/
pytest -q

# 1) Bump version + update docs, then:
git add .
git commit -m "Release vX.Y.Z"
git push origin main

# 2) Optional local backup
./save-version.sh X.Y.Z

# 3) Official release
./push-version.sh X.Y.Z "Notes: key features/fixes"

# 4) Verify
gh release view vX.Y.Z
git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$"
# Open Actions and Releases pages to confirm
9) Notes and Best Practices
Keep releases atomic: ensure main is up to date and green before tagging.
Prefer ./push-version.sh as the single source of truth for releases; use ./save-version.sh as a safety net before major changes.
If a tag already exists, push-version.sh will skip re-creating it and proceed—review its output for next steps.
Always verify that the release appears on GitHub and CI/CD has run.
Keep release notes meaningful and succinct.