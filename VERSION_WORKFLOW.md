# vpsweb — Release Process

This document describes the release process for `vpsweb`.

## ⚠️ **IMPORTANT: Process Update**

**Current Status**: The GitHub Actions automated workflow has reliability issues due to branch protection rules and permissions.

**Recommended Process**: Use **Claude-assisted manual release** - See [CLAUDE_RELEASE_PROCESS.md](./CLAUDE_RELEASE_PROCESS.md) for the complete step-by-step process.

## 🚀 **Simple Release Instructions**

**Just tell Claude**: `"Create release v0.4.4"`

Claude will handle:
- ✅ Repository preparation and validation
- ✅ Local backup creation
- ✅ Quality assurance checks
- ✅ Version updates across all files
- ✅ README.md and CHANGELOG.md updates
- ✅ Commit and release creation
- ✅ Verification and confirmation

---

## GitHub Actions Workflow (Legacy)

> **Note**: The automated workflow is currently unreliable due to branch protection rules blocking pushes when CI checks fail. Use the Claude-assisted manual process instead.

---

## 1. Overview

The release process is fully automated with a robust GitHub Actions workflow that handles all the tedious steps while providing extensive validation and safety measures. The workflow includes:

- **Pre-flight validation**: Checks repository state, version format, and prevents common issues
- **Automated backup**: Creates backup tags before making changes
- **Comprehensive testing**: Runs tests, code formatting checks, and optional linting/type checking
- **Atomic version updates**: Updates all version files with verification
- **Smart changelog management**: Creates structured release notes templates
- **Dry-run support**: Safe testing mode without pushing changes
- **Rollback protection**: Multiple safety checks to prevent accidental releases

This approach minimizes manual work, reduces the risk of human error, and ensures that every release is consistent and reliable.

---

## 2. How to Create a Release

Creating a new release requires just a few clicks with enhanced options for safety and testing.

### 2.1 Standard Release Process

1.  **Navigate to the Actions tab** in the `vpsweb` GitHub repository.

2.  In the left sidebar, click on the **"Create Release"** workflow.

3.  You will see a message saying "This workflow has a `workflow_dispatch` event trigger." Click the **"Run workflow"** dropdown button on the right.

4.  Configure the release options:
    - **Version**: Type the new semantic version number (e.g., `0.4.0`)
    - **Create backup**: Keep this checked (recommended) to create a backup tag
    - **Dry run**: Leave unchecked for actual release, or check to test the process

5.  Click the green **"Run workflow"** button.

### 2.2 Dry Run Mode (Recommended for Testing)

For testing or to preview changes without affecting the repository:

1.  Follow steps 1-4 above, but **check the "Dry run" option**
2.  The workflow will perform all steps except:
    - Pushing changes to GitHub
    - Creating the actual GitHub release
3.  Review the output to ensure everything would work correctly
4.  Run again without "Dry run" when ready to create the actual release

### 2.3 What the Automation Does

The workflow performs the following comprehensive steps:

#### Phase 1: Validation & Preparation
- 🔍 **Version Validation**: Validates semantic version format (X.Y.Z) and checks for duplicates
- 📋 **Backup Creation**: Creates backup tag (e.g., `v0.3.11-local-2025-11-01`)
- 🔒 **Repository State Check**: Ensures clean working directory, correct branch, and up-to-date
- 🧪 **Pre-flight Checks**: Validates all required files exist and are accessible

#### Phase 2: Quality Assurance
- 🧪 **Test Suite**: Runs full pytest test suite with short traceback format
- 🎨 **Code Formatting**: Runs Black formatting check on all source files
- 🔍 **Linting** (optional): Runs flake8 if available
- 🔎 **Type Checking** (optional): Runs MyPy if available

#### Phase 3: Version Management
- 📦 **Version Updates**: Updates version in `pyproject.toml`, `src/vpsweb/__init__.py`, and `src/vpsweb/__main__.py`
- 🔍 **Change Verification**: Verifies all version files were updated correctly
- 📝 **Changelog Update**: Creates structured release section in `CHANGELOG.md`

#### Phase 4: Release Creation
- 💾 **Commit Changes**: Commits all version-related changes with standardized message
- 🏷️ **Tag Creation**: Creates Git tag `vX.Y.Z` with release annotation
- 🚀 **Push Changes**: Pushes commit and tag to `main` branch
- 🎉 **GitHub Release**: Creates formal GitHub Release with release notes

---

## 3. Workflow Features and Options

### 3.1 Input Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `version` | String | Required | Semantic version number (e.g., `0.4.0`) |
| `create_backup` | Boolean | `true` | Create backup tag before release |
| `dry_run` | Boolean | `false` | Test mode - performs all steps except pushing to GitHub |

### 3.2 Safety Checks

The workflow includes comprehensive safety checks:

- **Version Format**: Validates semantic versioning pattern `X.Y.Z`
- **Version Uniqueness**: Prevents duplicate version releases
- **Repository Cleanliness**: Ensures no uncommitted changes
- **Branch Verification**: Must be on `main` branch
- **Remote Sync**: Ensures local `main` matches `origin/main`
- **File Existence**: Verifies all required version files exist
- **Update Verification**: Confirms all version files were updated correctly

### 3.3 Error Handling

- **Early Validation**: Fails fast if basic requirements aren't met
- **Clear Error Messages**: Provides specific guidance for each failure mode
- **Non-Destructive**: Dry run mode allows safe testing
- **Rollback Support**: Backup tags enable easy recovery

---

## 4. Post-Release Step: Update Release Notes

After the workflow completes successfully, update the release notes for better communication:

### 4.1 Manual Release Notes Update

1.  Go to the [**Releases page**](https://github.com/OCboy5/vpsweb/releases) of the repository.
2.  Find the newly created release (e.g., `v0.4.0`).
3.  Click the **"Edit"** button (pencil icon) for that release.
4.  **Update the release notes** with meaningful descriptions.

### 4.2 Release Notes Template

The workflow creates a structured template in `CHANGELOG.md` that you can use:

```markdown
## [0.4.0] - 2025-11-01

### 🚀 Overview
VPSWeb v0.4.0 - [Concise description of the release]

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

### 4.3 Best Practices for Release Notes

- **User-focused**: Write from the user's perspective
- **Categorize changes**: Use the provided categories for consistency
- **Be specific**: Include concrete details about what changed
- **Mention breaking changes**: Clearly highlight any breaking changes
- **Credit contributors**: Acknowledge people who contributed

---

## 5. Troubleshooting and Recovery

### 5.1 Common Issues and Solutions

#### Version Format Error
- **Issue**: Invalid version format provided
- **Solution**: Use semantic versioning format `X.Y.Z` (e.g., `0.4.0`)
- **Example**: `1.2.3` ✅, `v1.2.3` ❌, `1.2` ❌

#### Repository State Error
- **Issue**: Uncommitted changes or wrong branch
- **Solution**:
  ```bash
  git status  # Check for changes
  git add . && git commit -m "WIP"  # Commit or stash changes
  git checkout main  # Switch to main branch
  git pull origin main  # Sync with remote
  ```

#### Test Failures
- **Issue**: Test suite fails
- **Solution**:
  - Review test output in workflow logs
  - Fix failing tests locally
  - Ensure all dependencies are properly installed

#### Version Update Failures
- **Issue**: Version files not updated correctly
- **Solution**:
  - Check that `__version__` exists in `src/vpsweb/__init__.py`
  - Check that `version_option()` exists in `src/vpsweb/__main__.py`
  - Verify `pyproject.toml` has valid `version = "X.Y.Z"` format

### 5.2 Rollback Procedures

If a release was made in error, you have multiple recovery options:

#### Option 1: Full Rollback (Destructive)
**⚠️ Warning: This removes the release and all changes**

1.  **Delete the GitHub Release**:
    - Go to the Releases page
    - Find the release and delete it

2.  **Delete the remote Git tag**:
    ```bash
    git push --delete origin v0.4.0
    ```

3.  **Revert the release commit**:
    ```bash
    # Find the commit hash from workflow logs or git log
    git log --oneline --grep="chore(release)"
    # Revert the specific commit
    git revert <commit-hash>
    git push origin main
    ```

#### Option 2: Use Backup Tag (Recommended)
**Non-destructive recovery using automatic backup**

1.  **Identify the backup tag**: Find the backup tag from workflow logs (e.g., `v0.3.11-local-2025-11-01`)

2.  **Restore from backup**:
    ```bash
    # Checkout the backup state
    git checkout v0.3.11-local-2025-11-01

    # Create a new branch from the backup
    git checkout -b restore-backup

    # Push to main (force push - use with caution)
    git push origin restore-backup:main --force
    ```

3.  **Clean up**:
    ```bash
    # Switch back to main
    git checkout main

    # Pull the restored state
    git pull origin main

    # Delete the temporary branch
    git branch -D restore-backup
    ```

### 5.3 Getting Help

If you encounter issues:

1.  **Check Workflow Logs**: Review the detailed output in the GitHub Actions tab
2.  **Try Dry Run Mode**: Test the release process with `dry_run: true`
3.  **Verify Local State**: Ensure your local repository matches expectations
4.  **Review Git History**: Check for any unexpected commits or changes

---

## 6. Versioning Rules (SemVer)

This project follows [Semantic Versioning](https://semver.org/).

- **MAJOR** version (`X.y.z`): For incompatible API changes
- **MINOR** version (`x.Y.z`): For adding functionality in a backward-compatible manner
- **PATCH** version (`x.y.Z`): For backward-compatible bug fixes

### Version Examples
- ✅ `0.3.11` - Patch release (bug fixes)
- ✅ `0.4.0` - Minor release (new features)
- ✅ `1.0.0` - Major release (breaking changes)

### Tag Format
- Git tags are prefixed with `v`: `v0.3.11`
- Version in files does **not** include the prefix: `version = "0.3.11"`

---

## 7. Workflow Optimization Tips

### 7.1 Before Creating a Release

1.  **Run Tests Locally**: `poetry run pytest`
2.  **Check Formatting**: `poetry run black --check src/ tests/`
3.  **Clean Working Directory**: Commit or stash all changes
4.  **Sync with Main**: `git pull origin main`
5.  **Verify Version**: Confirm the version you want to release

### 7.2 Testing New Features

Use the **Dry Run** mode to test:
- New version formats
- Custom changelog entries
- Workflow modifications
- Integration changes

### 7.3 Release Planning

- **Schedule releases** when you have time to update release notes
- **Test thoroughly** before releasing major versions
- **Communicate changes** to users through detailed release notes
- **Monitor feedback** after release for any issues
