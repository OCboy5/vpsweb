# vpsweb — Streamlined Release Workflow (VERSION_WORKFLOW.md)

A concise, GitHub‑compliant release process that Claude Code can follow reliably. Uses semantic versioning and GitHub CLI.

---

## 0) Prerequisites

- GitHub CLI installed and authenticated:
  - gh auth status
- Clean working tree on main:
  - git status (no changes)
  - git pull origin main
- Python tooling available:
  - Black and pytest installed (e.g., pip install black pytest)

Scripts available in repo:
- ./save-version.sh X.Y.Z  (optional local backup)
- ./push-version.sh X.Y.Z "Release notes"  (official release)
  - Note: push-version.sh handles existing tags gracefully

---

## 1) Pre‑Release Checklist (must pass)

- **Step 1.1**: Create local backup (HIGHLY RECOMMENDED before any changes)
  ```bash
  ./save-version.sh X.Y.Z
  ```

- **Step 1.2**: Version bump done and consistent across all files:
  - pyproject.toml → version = "X.Y.Z"
  - src/vpsweb/__init__.py → __version__ = "X.Y.Z"
  - src/vpsweb/__main__.py → version_option(version="X.Y.Z")
  - Quick check:
    - grep -R 'X\.Y\.Z' src/ pyproject.toml

- **Step 1.3**: Update CHANGELOG.md with release notes (MANDATORY)
  - Add new section: `## [X.Y.Z] - YYYY-MM-DD (Release Name)`
  - Include highlights, features, fixes
  - Use consistent format with previous releases

- **Step 1.4**: Update documentation files (MANDATORY):
  - README.md: Update version badge and current status section
  - STATUS.md: Update version number, executive summary, and completed features
  - CLAUDE.md: Update version references if present
  - DEVELOPMENT.md: Update version-specific development notes if applicable

- **Step 1.5**: Code formatting passes:
  - python -m black --check src/ tests/
  - If formatting fails: python -m black src/ tests/

- **Step 1.6**: Tests pass locally (if possible):
  - pytest -q
  - Note: Some test failures may be acceptable for non-breaking changes

- **Step 1.7**: Commit all changes to main:
  - git add .
  - git commit -m "Release vX.Y.Z - [Release Name]

  [Detailed release notes]

  🚀 Generated with Claude Code (https://claude.ai/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>"
  - git push origin main

---

## 2) Standard Release Flow (recommended path)

⚠️ **IMPORTANT**: Local backup should be created in Step 1.1 (before making changes)
- If you missed Step 1.1, create backup now: `./save-version.sh X.Y.Z`

1) Create the official GitHub release (tag + release)
```bash
./push-version.sh X.Y.Z "Brief release notes: highlights, features, fixes"
```

- push-version.sh will:
  - Create or reuse annotated tag vX.Y.Z
  - Push tag to origin
  - Create GitHub Release via gh release create
  - Provide helpful messages if tag/release already exists

---

## 3) Post‑Release Verification

Run these checks immediately after the release:

```bash
# Release exists on GitHub
gh release view vX.Y.Z

# Tag exists on remote
git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$" || echo "Tag missing on remote"

# CI/CD status (open in browser)
# https://github.com/OCboy5/vpsweb/actions
# Release page:
# https://github.com/OCboy5/vpsweb/releases/tag/vX.Y.Z
```

If CI fails:
- Fix issues, push commits to main.
- If needed, edit the GitHub Release notes via gh or web UI.

---

## 4) Fallback: Manual Release (only if the script fails)

1) Ensure tag exists locally and remotely
```bash
git tag -a vX.Y.Z -m "vX.Y.Z"  # if not already created
git push origin vX.Y.Z
```

2) Create GitHub Release manually
```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"
```

3) Verify (same as Post-Release Verification)

---

## 5) Rollback / Recovery

- Delete local tag and recreate:
```bash
git tag -d vX.Y.Z
git tag -a vX.Y.Z -m "vX.Y.Z"
```

- Delete remote tag (if necessary):
```bash
git push --delete origin vX.Y.Z
```

- If you used local backup:
```bash
# List local backups
git tag -l "*local*"

# Check out a local backup (example)
git checkout v0.1.0-local-2025-10-05
```

---

## 6) Release Notes — Minimal Template

Use concise, high-signal notes. Example:

```
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
```

---

## 7) Versioning Rules (SemVer)

- Major (X.0.0): Breaking changes
- Minor (x.Y.0): New features, backwards compatible
- Patch (x.y.Z): Fixes and small improvements

Tags: vX.Y.Z (e.g., v0.2.1)

---

## 8) Quick Reference (TL;DR)

```bash
# 0) Preconditions
gh auth status
git status
python -m black --check src/ tests/
pytest -q

# 1) 🚨 MANDATORY RELEASE CHECKLIST
# 1.1) Local backup (BEFORE making changes!)
./save-version.sh X.Y.Z

# 1.2) Version bump in 3 files
# Edit: pyproject.toml, src/vpsweb/__init__.py, src/vpsweb/__main__.py

# 1.3) Update CHANGELOG.md (MANDATORY)
# Add new section with release notes

# 1.4) Update documentation (MANDATORY)
# Edit: README.md (version + status), STATUS.md (version + features)

# 1.5) Format code if needed
python -m black src/ tests/

# 1.6) Commit and push
git add .
git commit -m "Release vX.Y.Z - [Release Name]

[Release notes]

🚀 Generated with Claude Code (https://claude.ai/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main

# 2) Official release
./push-version.sh X.Y.Z "Brief release notes: highlights, features, fixes"

# 3) Verify
gh release view vX.Y.Z
git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$"
# Open Actions and Releases pages to confirm
```

## 9) Release Checklist (Print this for reference)

```
□ 1.1 Create local backup: ./save-version.sh X.Y.Z
□ 1.2 Update version in pyproject.toml
□ 1.3 Update version in src/vpsweb/__init__.py
□ 1.4 Update version in src/vpsweb/__main__.py
□ 1.5 Verify version consistency: grep -R 'X.Y.Z' src/ pyproject.toml
□ 1.6 Update CHANGELOG.md with release notes
□ 1.7 Update README.md (version badge + status section)
□ 1.8 Update STATUS.md (version + executive summary + features)
□ 1.9 Update other docs if needed (CLAUDE.md, DEVELOPMENT.md)
□ 1.10 Check code formatting: python -m black --check src/ tests/
□ 1.11 Fix formatting if needed: python -m black src/ tests/
□ 1.12 Run tests if possible: pytest -q
□ 1.13 Commit all changes to main
□ 1.14 Push to main branch
□ 2.1 Create GitHub release: ./push-version.sh X.Y.Z "release notes"
□ 3.1 Verify release exists: gh release view vX.Y.Z
□ 3.2 Verify tag exists on remote
□ 3.3 Open GitHub Actions page to check CI
```

---

## 10) Notes and Best Practices

- Keep releases atomic: ensure main is up to date and green before tagging.
- Prefer ./push-version.sh as the single source of truth for releases; use ./save-version.sh as a safety net before major changes.
- If a tag already exists, push-version.sh will skip re-creating it and proceed—review its output for next steps.
- Always verify that the release appears on GitHub and CI/CD has run.
- Keep release notes meaningful and succinct.

---

This streamlined workflow preserves all critical checks, keeps GitHub‑standard tagging and releases, and is simple enough for Claude Code to follow deterministically.