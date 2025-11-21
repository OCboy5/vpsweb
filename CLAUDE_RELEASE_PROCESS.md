# Claude Release Process - Standard Operating Procedure

This document defines the **standardized release process** that Claude Code follows when requested to create releases for the VPSWeb project.

## User Instructions (How to trigger a release)

**Simple command**: Just tell me `"Create release v0.4.4"` (or any version number)

**Alternative commands**:
- `"Release v0.5.0"`
- `"I want to release v1.0.0"`
- `"Help me create release v0.4.3.1"`

## Claude's Release Process (Step-by-Step)

### Phase 1: Repository Preparation
1. **Check current repository state**
   - Verify clean working directory (no uncommitted changes)
   - Confirm we're on main branch
   - Ensure local is synced with remote

2. **Version validation**
   - Check current version in all files
   - Verify requested version doesn't already exist
   - Validate semantic version format (X.Y.Z)

### Phase 2: Quality Assurance
3. **Run essential tests**
   - Test core CLI functionality
   - Verify model imports work
   - Test basic import functionality

4. **Code quality checks**
   - Run Black formatting check
   - Fix any formatting issues automatically
   - Skip optional linting (as per workflow design)

5. **File verification**
   - Confirm all required files exist:
     - `pyproject.toml`
     - `src/vpsweb/__init__.py`
     - `src/vpsweb/__main__.py`
     - `CHANGELOG.md`
     - `README.md`

### Phase 3: Version Management
6. **Update version files**
   - Update `pyproject.toml`: `version = "X.Y.Z"`
   - Update `src/vpsweb/__init__.py`: `__version__ = "X.Y.Z"`
   - Update `src/vpsweb/__main__.py`: `version="X.Y.Z"`
   - Verify all versions match

7. **Update CHANGELOG.md**
   - Create new release section with proper format
   - Include release date
   - Add structured template for release notes

8. **Update README.md** ⭐ **NEW**
   - Update version mentions in README.md
   - Update installation instructions if needed
   - Update any version-specific examples or documentation
   - Add new release to release history section if it exists

### Phase 4: Pre-Release Commit
9. **Commit all changes**
    - Stage all version and documentation changes
    - Create standardized commit message
    - Push to remote repository

### Phase 5: Release Creation
10. **Execute release script**
    - Use `./push-version.sh X.Y.Z "Release notes"`
    - Script handles:
      - Tag creation
      - GitHub release creation
      - Proper error handling

11. **Verification**
    - Confirm release appears in GitHub releases
    - Verify tag exists
    - Check release URL works
    - Confirm version consistency across all files

### Phase 6: Local Backup Creation ⭐ **NEW**
12. **Create local backup before making changes**
   - Run `./save-version.sh X.Y.Z` to create backup tag
   - Verify backup tag was created successfully
   - This provides rollback capability if anything goes wrong

## Release Notes Template

When updating CHANGELOG.md, use this structure:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### 🚀 Overview
VPSWeb vX.Y.Z - [Brief description of release]

### ✨ New Features
- ✨ Feature: [Description of new features]

### 🔧 Improvements
- 🛠️ Improvement: [Description of improvements]

### 🐛 Bug Fixes
- 🐛 Fix: [Description of bug fixes]

### 📚 Documentation Updates
- 📚 Docs: [Description of documentation changes]

### 🔧 Technical Changes
- 🔨 Technical: [Description of technical changes]
```

## README.md Updates Required

For each release, check and update these 5 sections in README.md:

1. **Version badge** (if present)
2. **Installation instructions** - ensure they reference latest stable version
3. **Changelog section** - add link to new release
4. **Examples** - update any version-specific examples
5. **Compatibility notes** - update if relevant

## Error Handling

If any step fails:
1. **Stop immediately** and report the specific failure
2. **Use backup tag** for rollback if needed: `git checkout vX.Y.Z-local-YYYY-MM-DD`
3. **Provide clear error message** with what went wrong
4. **Suggest next steps** (fix issue vs. manual intervention)
5. **Never proceed** with broken state

## Important Reminders for Claude

- **ALWAYS update README.md** with version information
- **ALWAYS use the manual `./push-version.sh` script** - it's proven reliable
- **NEVER rely on the GitHub Actions workflow** - it has permissions/protection issues
- **ALWAYS verify the release was created** before reporting success
- **NEVER skip quality checks** - they ensure reliable releases
- **COMMIT all changes** before running the release script
- **ALWAYS check version consistency** across all files
- **ALWAYS create a local backup first** using `./save-version.sh`

## Version Files That Must Be Updated

1. `pyproject.toml` - line 3: `version = "X.Y.Z"`
2. `src/vpsweb/__init__.py` - `__version__ = "X.Y.Z"`
3. `src/vpsweb/__main__.py` - line with `version="X.Y.Z"`
4. `README.md` - version mentions and documentation
5. `CHANGELOG.md` - release notes and history

## Quality Assurance Commands

```bash
# Create backup (STEP 3)
./save-version.sh X.Y.Z

# Test CLI functionality
export PYTHONPATH="$(pwd)/src:$PYTHONPATH" && poetry run vpsweb --version

# Test imports
python -c "from vpsweb.models.translation import InitialTranslation, RevisedTranslation; print('✅ Core models import successfully')"

# Test CLI entry point
python -c "from vpsweb.__main__ import cli; print('✅ CLI entry point available')"

# Check formatting
poetry run black --check src/ tests/

# Create release (STEP 11)
./push-version.sh X.Y.Z "Release notes with proper description"
```

## Rollback Process (If Needed)

If something goes wrong during release:

```bash
# List available backup tags
git tag -l "*local*"

# Restore from backup
git checkout vX.Y.Z-local-YYYY-MM-DD
git checkout -b restore-backup
git push origin restore-backup:main --force
git checkout main
git branch -D restore-backup
```

---

**Last Updated**: 2025-11-13
**Process Version**: 1.1
**Status**: Production Ready
**Key Updates**: Added local backup creation and README.md updates