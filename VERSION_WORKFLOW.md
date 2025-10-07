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

### Before Major Changes
```bash
# Save current state locally before making changes
./save-version.sh 0.1.0
```

### After Completing Features
```bash
# Commit your changes
git add .
git commit -m "Add new features for v0.2.0"

# Push as official release
./push-version.sh 0.2.0 "Added user authentication and dashboard"
```

### Emergency Recovery
```bash
# List all local versions
git tag -l "*local*"

# Restore specific version
git checkout v0.1.0-local-2025-10-05
```

## Version Naming Convention
- **Local tags**: `v{version}-local-{date}` (e.g., `v0.1.1-local-2025-10-05`)
- **Local branches**: `backup-v{version}-{date}` (e.g., `backup-v0.1.1-2025-10-05`)
- **Remote tags**: `v{version}` (e.g., `v0.1.0`)

## v0.2.0 Release Lessons Learned

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
   grep -r "0\.2\.0" src/ pyproject.toml  # Should find 3 files
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

#### Release Process
1. Commit all changes
2. Create local backup: `./save-version.sh X.Y.Z`
3. Push to GitHub: `./push-version.sh X.Y.Z "Release notes"`
4. Verify CI/CD passes on GitHub

## Best Practices (Updated)
1. Always save locally before major changes
2. Only push stable versions to GitHub
3. Use semantic versioning (major.minor.patch)
4. Include meaningful release notes for GitHub releases
5. Keep your working directory clean before pushing releases
6. **NEW**: Verify version consistency across ALL files before release
7. **NEW**: Run Black formatting checks before pushing to GitHub
8. **NEW**: Test imports and functionality locally before release
9. **NEW**: Monitor GitHub Actions after release for CI/CD compliance