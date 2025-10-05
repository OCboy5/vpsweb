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

## Best Practices
1. Always save locally before major changes
2. Only push stable versions to GitHub
3. Use semantic versioning (major.minor.patch)
4. Include meaningful release notes for GitHub releases
5. Keep your working directory clean before pushing releases