# Pull Request

## Description

<!-- Provide a detailed description of the changes in this PR -->

## Related Issues

<!-- Link to any related issues using GitHub keywords (e.g., "Fixes #123", "Addresses #456") -->

## Type of Change

<!-- Please check the boxes that apply -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test updates/additions
- [ ] 🔧 Configuration changes
- [ ] 🚀 Performance improvements
- [ ] 🔒 Security improvements

## Changes Made

<!-- Describe the specific changes made in this PR -->

### Code Changes
-

### Configuration Changes
-

### Documentation Updates
-

## Testing

### Automated Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass locally

### Manual Testing
- [ ] Tested with different configurations
- [ ] Tested with various poem inputs
- [ ] Tested CLI commands
- [ ] Tested Python API usage

**Test Configuration**:
```yaml
# Configuration used for testing
main:
  workflow:
    steps:
      - name: "initial_translation"
        provider: "tongyi"
        model: "qwen-max"
```

## Checklist

### Code Quality
- [ ] Code follows project style guidelines (Black, flake8, isort)
- [ ] Type hints are used appropriately
- [ ] Docstrings are updated/added
- [ ] No commented-out code
- [ ] No debugging statements left

### Documentation
- [ ] README.md updated if needed
- [ ] API documentation updated
- [ ] Configuration documentation updated
- [ ] Inline comments added where necessary

### Review
- [ ] Self-review completed
- [ ] Code is well-documented and readable
- [ ] Changes are focused and atomic
- [ ] No unnecessary dependencies added

### Security
- [ ] No sensitive information exposed
- [ ] No hardcoded credentials
- [ ] Input validation is adequate

## Screenshots / Examples

<!-- If applicable, add screenshots, configuration examples, or output examples -->

**Before**:
```
Example of previous behavior
```

**After**:
```
Example of new behavior
```

## Additional Notes

<!-- Any additional information for reviewers -->

## Breaking Changes

<!-- If this PR contains breaking changes, describe them here and how to migrate -->

## Deployment Notes

<!-- Any special deployment considerations or requirements -->