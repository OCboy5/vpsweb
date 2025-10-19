#!/bin/bash

# VPSWeb Repository Backup Script
# Creates comprehensive backups of the VPSWeb Repository system
# Version: 0.3.1

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$PROJECT_ROOT/repository_root"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="vpsweb_repo_backup_$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Create backup directory if it doesn't exist
create_backup_dir() {
    log "Creating backup directory..."
    mkdir -p "$BACKUP_DIR"

    # Clean up old backups (keep last 10)
    log "Cleaning up old backups (keeping last 10)..."
    cd "$BACKUP_DIR"
    ls -t | tail -n +11 | xargs -r rm -rf
}

# Backup SQLite database
backup_database() {
    log "Backing up SQLite database..."

    if [ ! -f "$REPO_ROOT/repo.db" ]; then
        warn "Database file not found at $REPO_ROOT/repo.db"
        return
    fi

    # Create database backup directory
    mkdir -p "$BACKUP_PATH/database"

    # Use SQLite backup command for consistent backup
    log "Creating consistent database backup..."
    sqlite3 "$REPO_ROOT/repo.db" ".backup $BACKUP_PATH/database/repo.db"

    # Also create SQL dump for additional safety
    log "Creating SQL dump..."
    sqlite3 "$REPO_ROOT/repo.db" ".dump" > "$BACKUP_PATH/database/repo_dump.sql"

    # Create database info
    log "Creating database info..."
    sqlite3 "$REPO_ROOT/repo.db" "SELECT 'Poems: ' || COUNT(*) FROM poems;" > "$BACKUP_PATH/database/stats.txt"
    sqlite3 "$REPO_ROOT/repo.db" "SELECT 'Translations: ' || COUNT(*) FROM translations;" >> "$BACKUP_PATH/database/stats.txt"
    sqlite3 "$REPO_ROOT/repo.db" "SELECT 'AI Logs: ' || COUNT(*) FROM ai_logs;" >> "$BACKUP_PATH/database/stats.txt"
    sqlite3 "$REPO_ROOT/repo.db" "SELECT 'Human Notes: ' || COUNT(*) FROM human_notes;" >> "$BACKUP_PATH/database/stats.txt"
    sqlite3 "$REPO_ROOT/repo.db" "SELECT 'Backup created: ' || datetime('now');" >> "$BACKUP_PATH/database/stats.txt"

    log "Database backup completed"
}

# Backup configuration files
backup_config() {
    log "Backing up configuration files..."

    mkdir -p "$BACKUP_PATH/config"

    # Backup environment file if it exists
    if [ -f "$PROJECT_ROOT/.env.local" ]; then
        cp "$PROJECT_ROOT/.env.local" "$BACKUP_PATH/config/.env.local"
        log "Environment file backed up"
    fi

    # Backup template file
    if [ -f "$PROJECT_ROOT/.env.local.template" ]; then
        cp "$PROJECT_ROOT/.env.local.template" "$BACKUP_PATH/config/.env.local.template"
    fi

    # Backup repository configuration
    if [ -f "$PROJECT_ROOT/config/repository.yaml" ]; then
        cp "$PROJECT_ROOT/config/repository.yaml" "$BACKUP_PATH/config/repository.yaml"
        log "Repository configuration backed up"
    fi

    # Backup main VPSWeb configuration files
    mkdir -p "$BACKUP_PATH/config/vpsweb"
    if [ -d "$PROJECT_ROOT/config" ]; then
        cp -r "$PROJECT_ROOT/config/"* "$BACKUP_PATH/config/vpsweb/" 2>/dev/null || true
        log "VPSWeb configuration files backed up"
    fi
}

# Backup source code (optional, for development)
backup_source() {
    log "Backing up source code..."

    mkdir -p "$BACKUP_PATH/source"

    # Backup critical source files
    mkdir -p "$BACKUP_PATH/source/src/vpsweb"

    # Repository module
    if [ -d "$PROJECT_ROOT/src/vpsweb/repository" ]; then
        cp -r "$PROJECT_ROOT/src/vpsweb/repository" "$BACKUP_PATH/source/src/vpsweb/"
        log "Repository source code backed up"
    fi

    # WebUI module
    if [ -d "$PROJECT_ROOT/src/vpsweb/webui" ]; then
        cp -r "$PROJECT_ROOT/src/vpsweb/webui" "$BACKUP_PATH/source/src/vpsweb/"
        log "WebUI source code backed up"
    fi

    # Models and core
    if [ -d "$PROJECT_ROOT/src/vpsweb/models" ]; then
        cp -r "$PROJECT_ROOT/src/vpsweb/models" "$BACKUP_PATH/source/src/vpsweb/"
    fi
    if [ -d "$PROJECT_ROOT/src/vpsweb/core" ]; then
        cp -r "$PROJECT_ROOT/src/vpsweb/core" "$BACKUP_PATH/source/src/vpsweb/"
    fi

    # Backup key Python files
    cp "$PROJECT_ROOT/src/vpsweb/__main__.py" "$BACKUP_PATH/source/src/vpsweb/" 2>/dev/null || true
    cp "$PROJECT_ROOT/pyproject.toml" "$BACKUP_PATH/source/" 2>/dev/null || true
}

# Create backup metadata
create_metadata() {
    log "Creating backup metadata..."

    cat > "$BACKUP_PATH/metadata.json" << EOF
{
    "backup_info": {
        "name": "$BACKUP_NAME",
        "timestamp": "$TIMESTAMP",
        "version": "0.3.1",
        "created_by": "backup.sh",
        "description": "VPSWeb Repository System Backup"
    },
    "system_info": {
        "hostname": "$(hostname)",
        "user": "$(whoami)",
        "os": "$(uname -s)",
        "architecture": "$(uname -m)",
        "working_directory": "$PROJECT_ROOT"
    },
    "git_info": {
        "branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
        "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
        "is_clean": "$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    },
    "vpsweb_info": {
        "project_root": "$PROJECT_ROOT",
        "repo_root": "$REPO_ROOT",
        "database_path": "$REPO_ROOT/repo.db"
    }
}
EOF

    # Create README for this backup
    cat > "$BACKUP_PATH/README.md" << EOF
# VPSWeb Repository Backup - $TIMESTAMP

This is a complete backup of the VPSWeb Repository system created on $(date).

## Contents

- \`database/\`: SQLite database backup and SQL dump
- \`config/\`: Configuration files and environment settings
- \`source/\`: Source code backup (selected modules)
- \`metadata.json\`: Backup metadata and system information
- \`README.md\`: This file

## Restoration

Use the \`restore.sh\` script from the project root:

\`\`\`bash
./restore.sh $BACKUP_NAME
\`\`\`

## Important Notes

- This backup contains all your poems, translations, and notes
- Configuration files include sensitive information like API keys
- Keep this backup in a secure location
- Test restoration before relying on this backup

## Verification

After restoration, verify:
1. Database contains expected number of records
2. Web interface loads correctly
3. Configuration is properly applied
4. API endpoints respond correctly

Created: $(date)
Version: 0.3.1
EOF
}

# Compress backup
compress_backup() {
    log "Compressing backup..."

    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"

    # Verify the compressed file
    if [ ! -f "$BACKUP_NAME.tar.gz" ]; then
        error "Failed to create compressed backup file"
    fi

    # Remove uncompressed backup
    rm -rf "$BACKUP_PATH"

    # Get compressed file size
    local size=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)

    log "Backup compressed: $BACKUP_NAME.tar.gz ($size)"
}

# Verify backup
verify_backup() {
    log "Verifying backup integrity..."

    local archive_file="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

    # Test archive integrity
    if ! tar -tzf "$archive_file" > /dev/null 2>&1; then
        error "Backup archive is corrupted"
    fi

    # Extract database file to verify
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    cd "$temp_dir"
    tar -xzf "$archive_file" "$BACKUP_NAME/database/repo.db"

    # Verify database integrity
    if ! sqlite3 "$BACKUP_NAME/database/repo.db" "PRAGMA integrity_check;" | grep -q "ok"; then
        error "Database integrity check failed"
    fi

    # Check database size
    local db_size=$(du -h "$BACKUP_NAME/database/repo.db" | cut -f1)
    log "Database verified ($db_size)"

    rm -rf "$temp_dir"

    log "Backup verification completed successfully"
}

# Main backup function
main() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "  VPSWeb Repository Backup Script"
    echo "  Version 0.3.1"
    echo "========================================"
    echo -e "${NC}"

    log "Starting backup process..."
    log "Project root: $PROJECT_ROOT"
    log "Backup name: $BACKUP_NAME"

    # Pre-flight checks
    if [ ! -d "$PROJECT_ROOT" ]; then
        error "Project root directory not found: $PROJECT_ROOT"
    fi

    # Execute backup steps
    create_backup_dir
    backup_database
    backup_config
    backup_source
    create_metadata
    compress_backup
    verify_backup

    log "Backup completed successfully!"
    log "Backup location: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

    # Display summary
    echo -e "${GREEN}"
    echo "========================================"
    echo "  BACKUP SUMMARY"
    echo "========================================"
    echo "Name: $BACKUP_NAME"
    echo "Location: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    echo "Size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)"
    echo "Date: $(date)"
    echo "Version: 0.3.1"
    echo "========================================"
    echo -e "${NC}"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "VPSWeb Repository Backup Script v0.3.1"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --version, -v  Show version information"
        echo ""
        echo "Description:"
        echo "  Creates a comprehensive backup of the VPSWeb Repository system"
        echo "  including database, configuration, and selected source files."
        echo ""
        exit 0
        ;;
    --version|-v)
        echo "VPSWeb Repository Backup Script v0.3.1"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1. Use --help for usage information."
        ;;
esac