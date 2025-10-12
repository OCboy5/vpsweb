# Version Management Workflow

## Scripts Overview

### 1. Local Backup: `save-version.sh`
- **Purpose**: Create local backup versions
- **Usage**: `./save-version.sh <version>`
- **Creates**: Local tag + backup branch
- **Example**: `./save-version.sh 0.1.1`

### 2. GitHub Release: `push-version.sh`
- **Purpose**: Push official releases to GitHub
- **Usage**: `./push-version.sh <version> [release_notes]`
- **Creates**: Annotated tag + GitHub release
- **Example**: `./push-version.sh 0.2.0 "Added new features"`

## Recommended Workflow

### Pre-Release Checklist
1. **Version Consistency Check**: Verify version numbers across all files
2. **Commit Changes**: Ensure all changes are committed to main branch
3. **Create Local Backup**: Save current state locally before release
4. **Push to GitHub**: Create official release with comprehensive notes

### Before Major Changes
```bash
# Save current state locally before making changes
./save-version.sh 0.1.0
```

### After Completing Features
```bash
# 1. Check version consistency
grep -r "0\.2\.0" src/ pyproject.toml  # Should find 3 files

# 2. Commit your changes
git add .
git commit -m "Add new features for v0.2.0"

# 3. Create local backup (safety net)
./save-version.sh 0.2.0

# 4. Push as official release
./push-version.sh 0.2.0 "Added user authentication and dashboard"
```

### Emergency Recovery
```bash
# List all local versions
git tag -l "*local*"

# Restore specific version
git checkout v0.1.0-local-2025-10-05
```

### GitHub Actions Failure Recovery
If the automatic GitHub release creation fails (403 errors):

1. **Verify Current Status**:
   ```bash
   # Check if release exists on GitHub
   gh release view vX.Y.Z 2>/dev/null && echo "Release exists" || echo "Release missing"

   # Check if tag exists remotely
   git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$"

   # Check CI/CD status on GitHub
   # Visit: https://github.com/OCboy5/vpsweb/actions
   ```

2. **Manual Release Creation**:
   ```bash
   # Create release manually using GitHub CLI
   gh release create vX.Y.Z --title "Release X.Y.Z" --notes "Your release notes here"

   # Or visit GitHub web interface:
   # https://github.com/OCboy5/vpsweb/releases/new
   ```

3. **Verify Release Success**:
   ```bash
   # Verify release exists
   gh release view vX.Y.Z

   # Check tag is pushed
   git ls-remote --tags origin | grep "refs/tags/vX.Y.Z$"

   # Visit release page:
   # https://github.com/OCboy5/vpsweb/releases/tag/vX.Y.Z
   ```

## Version Naming Convention
- **Local tags**: `v{version}-local-{date}` (e.g., `v0.1.1-local-2025-10-05`)
- **Local branches**: `backup-v{version}-{date}` (e.g., `backup-v0.1.1-2025-10-05`)
- **Remote tags**: `v{version}` (e.g., `v0.1.0`)

## v0.2.1 Release Lessons Learned

### ✅ What Worked Well
- **Local backup system**: Created safety net before GitHub release with `save-version.sh`
- **Manual release creation**: GitHub CLI successfully created release when Actions failed
- **Comprehensive documentation**: Detailed release notes and changelog updates
- **Version consistency**: All version files updated correctly

### ⚠️ Issues Encountered & Solutions

#### 1. GitHub Actions Permission Issues
**Problem**: GitHub Actions failed with 403 status when creating release
**Solution**:
- Manual release creation using GitHub CLI: `gh release create v0.2.1 --title "..." --notes "..."`
- Updated `push-version.sh` to handle existing tags and provide better error messages
- Added fallback manual instructions when automatic creation fails

#### 2. Tag Already Exists Scenario
**Problem**: `push-version.sh` failed when tag already existed locally
**Solution**: Updated script to detect existing tags and skip creation:
```bash
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "ℹ️  Tag $TAG already exists locally, skipping tag creation"
else
    # Create tag
fi
```

#### 3. Release Creation Failures
**Problem**: GitHub CLI release creation can fail due to permissions or existing releases
**Solution**: Enhanced error handling with helpful fallback instructions:
- Check if release already exists
- Provide manual creation URL
- Show GitHub CLI alternative commands
- Don't exit with error if release already exists

## v0.2.0 Release Lessons Learned (Previous)

### ✅ What Worked Well
- **Workflow scripts**: `save-version.sh` and `push-version.sh` worked perfectly
- **Local backup system**: Created safety net before GitHub release
- **Release notes**: Comprehensive release notes with feature descriptions

### ⚠️ Issues Encountered & Solutions

#### 1. Version Inconsistency
**Problem**: Version numbers were inconsistent across files
**Solution**: Always update ALL version files before release:
- `pyproject.toml` (line 3: `version = "X.Y.Z"`)
- `src/vpsweb/__init__.py` (line 33: `__version__ = "X.Y.Z"`)
- `src/vpsweb/__main__.py` (line 278: `version_option(version="X.Y.Z")`)

#### 2. CI/CD Formatting Failures
**Problem**: GitHub Actions failed due to Black code formatting issues
**Solution**: Run code formatting tools before release:
```bash
# Install and run Black formatter
pip install black
python -m black src/ tests/

# Check for formatting issues
python -m black --check src/ tests/
```

#### 3. Import Errors in Tests
**Problem**: Tests failed due to incorrect import names
**Solution**: Verify all imports are correct after refactoring:
- Check `ProviderConfig` → `ModelProviderConfig` changes
- Run tests locally before releasing

### 📋 Updated Release Checklist

#### Pre-Release Validation
1. **Version Consistency Check**:
   ```bash
   grep -r "X\.Y\.Z" src/ pyproject.toml  # Should find 3 files
   ```

2. **Code Formatting Check**:
   ```bash
   python -m black --check src/ tests/  # Should pass
   ```

3. **Test Validation**:
   ```bash
   python -m pytest tests/  # Should pass
   ```

4. **Import Validation**:
   ```bash
   python -c "from src.vpsweb.models.config import ModelProviderConfig"
   ```

5. **GitHub CLI Authentication Check**:
   ```bash
   gh auth status  # Verify GitHub CLI is authenticated
   ```

#### Release Process
1. **Update all relevant documents (README.md, CHANGELOG.md, etc.) accordingly**
2. Commit all changes
3. Create local backup: `./save-version.sh X.Y.Z`
4. Push to GitHub: `./push-version.sh X.Y.Z "Release notes"`
5. If GitHub Actions fails, manually create release: `gh release create vX.Y.Z --title "..." --notes "..."`
6. Verify CI/CD passes on GitHub
7. **NEW**: Verify release appears on GitHub: https://github.com/OCboy5/vpsweb/releases

## Best Practices (Updated)
1. Always save locally before major changes
2. Only push stable versions to GitHub
3. Use semantic versioning (major.minor.patch)
4. Include meaningful release notes for GitHub releases
5. Keep your working directory clean before pushing releases
6. Update all relevant documents (README.md, CHANGELOG.md, etc.) before any release
7. Verify version consistency across ALL files before release
8. Run Black formatting checks before pushing to GitHub
9. Test imports and functionality locally before release
10. Monitor GitHub Actions after release for CI/CD compliance
11. **NEW (v0.2.1)**: Check GitHub CLI authentication before release
12. **NEW (v0.2.1)**: Be prepared to create releases manually if GitHub Actions fails
13. **NEW (v0.2.1)**: Verify release appears on GitHub after pushing
14. **NEW (v0.2.1)**: `push-version.sh` now handles existing tags gracefully