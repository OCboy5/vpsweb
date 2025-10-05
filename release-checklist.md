# VPSWeb Release Checklist

This checklist ensures consistent, high-quality releases by following the lessons learned from previous releases.

## 🚀 Pre-Release Checklist

### 📋 Development Quality Checks
- [ ] Run `./dev-check.sh --release-mode` to validate code quality
- [ ] All linting checks pass (Black, Flake8, MyPy)
- [ ] All tests pass
- [ ] No uncommitted changes in working directory
- [ ] On main branch

### 🔧 Version Management
- [ ] Update version numbers in all files:
  - [ ] `pyproject.toml` (line 3: `version = "X.Y.Z"`)
  - [ ] `src/vpsweb/__init__.py` (line 33: `__version__ = "X.Y.Z"`)
  - [ ] `src/vpsweb/__main__.py` (line 248: `version_option(version="X.Y.Z")`)

### 📝 Documentation Updates
- [ ] Update `CHANGELOG.md` with new version section
- [ ] Add detailed release notes including:
  - [ ] New features
  - [ ] Bug fixes
  - [ ] Breaking changes (if any)
  - [ ] Performance improvements
  - [ ] Technical debt reduction

### 🧪 Testing & Validation
- [ ] Manual testing of core functionality:
  - [ ] CLI commands work correctly
  - [ ] Translation workflow executes successfully
  - [ ] Markdown export functionality works
  - [ ] Error handling is robust
- [ ] Integration tests with actual APIs (if applicable)
- [ ] Configuration validation with test cases

### 🔐 Security & Dependencies
- [ ] Check for any security vulnerabilities in dependencies
- [ ] Update dependencies if needed
- [ ] Verify no sensitive information in codebase
- [ ] Check API keys and secrets are properly handled

## 📦 Release Process

### 1. Final Checks
```bash
# Run comprehensive development checks
./dev-check.sh --release-mode

# Fix any issues found
./dev-check.sh --release-mode --fix
```

### 2. Commit Changes
```bash
# Add all changes
git add -A

# Commit with detailed message
git commit -m "feat: release v{VERSION} - {BRIEF_DESCRIPTION}

🚀 Features:
- Feature 1 description
- Feature 2 description

🐛 Bug Fixes:
- Bug fix 1 description
- Bug fix 2 description

📈 Improvements:
- Improvement 1 description
- Improvement 2 description

🧪 Testing:
- All tests passing
- Manual validation completed

📋 Documentation:
- CHANGELOG.md updated
- Release notes prepared

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 3. Create Release
```bash
# Use the improved push script
./push-version.sh "{VERSION}" "{COMPREHENSIVE_RELEASE_NOTES}"
```

## ✅ Post-Release Checklist

### 📊 Release Verification
- [ ] Verify release appears on GitHub: https://github.com/OCboy5/vpsweb/releases
- [ ] Check release is marked as "Latest"
- [ ] Verify release notes are correctly formatted
- [ ] Confirm tag was created and pushed

### 🧹 Cleanup
- [ ] Remove any temporary test files
- [ ] Clean up branches if needed
- [ ] Update local development environment

### 📈 Communication
- [ ] Announce release to stakeholders
- [ ] Update project documentation
- [ ] Create release summary report

### 🔮 Future Planning
- [ ] Document lessons learned from this release
- [ ] Update roadmap if needed
- [ ] Plan next development cycle

## 🛠️ Troubleshooting Guide

### Common Issues & Solutions

#### GitHub Release Not Created
**Problem**: Tag pushed but no GitHub release appears
**Solution**:
- Check GitHub Actions workflow (should use `softprops/action-gh-release@v1`)
- Use manual CLI: `gh release create vX.Y.Z --title "Release vX.Y.Z" --notes "..."`

#### Version Inconsistency
**Problem**: Different version numbers across files
**Solution**: Run `./dev-check.sh` to detect and fix inconsistencies

#### Linting Failures
**Problem**: Code style issues
**Solution**: Run `./dev-check.sh --fix` to auto-fix formatting issues

#### Tests Failing
**Problem**: Unit tests failing
**Solution**: Check test logs, fix issues, and re-run `./dev-check.sh --test-only`

### Emergency Rollback
If critical issues are discovered after release:

1. **Delete the release**:
   ```bash
   gh release delete vX.Y.Z
   git tag -d vX.Y.Z
   git push origin :refs/tags/vX.Y.Z
   ```

2. **Fix the issues** and create a new release with a patch version

## 📚 Scripts Reference

### `dev-check.sh`
- **Purpose**: Comprehensive development quality checks
- **Usage**: `./dev-check.sh [options]`
- **Options**:
  - `--release-mode`: Run all checks for release preparation
  - `--lint-only`: Run only linting checks
  - `--test-only`: Run only tests
  - `--fix`: Auto-fix issues where possible

### `push-version.sh` (v2.0)
- **Purpose**: Create and push GitHub releases reliably
- **Usage**: `./push-version.sh <version> [release_notes]`
- **Features**:
  - Pre-flight checks (clean repo, main branch, GitHub CLI)
  - Uses GitHub CLI instead of unreliable GitHub Actions
  - Automatic release verification

### `save-version.sh`
- **Purpose**: Create local backup versions
- **Usage**: `./save-version.sh <version>`
- **Creates**: Local tag and backup branch

## 🎯 Best Practices

### Before Every Release
1. **Always run `./dev-check.sh --release-mode`**
2. **Test on a clean environment**
3. **Verify version consistency**
4. **Update documentation thoroughly**

### During Release
1. **Use the improved scripts** (learned from v0.1.1 issues)
2. **Verify each step completes successfully**
3. **Don't skip the verification steps**

### After Release
1. **Confirm release is visible on GitHub**
2. **Test the release locally**
3. **Document any issues for future reference**

---

**Version History**:
- v1.0: Initial checklist created after v0.1.1 release lessons learned
- Covers all issues encountered and solutions implemented

**Last Updated**: 2025-10-05
**Next Review**: After next release cycle