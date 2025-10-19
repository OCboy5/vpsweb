#!/bin/bash
# VPSWeb Repository Backup Script v0.3.1
#
# This script creates comprehensive backups of the VPSWeb repository system
# including database, files, configuration, and outputs.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="vpsweb_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create backup directory
setup_backup_dir() {
    log "Setting up backup directory..."
    mkdir -p "$BACKUP_DIR"
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"
    success "Backup directory created: ${BACKUP_DIR}/${BACKUP_NAME}"
}

# Backup database
backup_database() {
    log "Backing up SQLite database..."

    local db_file="${PROJECT_ROOT}/data/vpsweb.db"
    local backup_db="${BACKUP_DIR}/${BACKUP_NAME}/vpsweb.db"

    if [[ -f "$db_file" ]]; then
        # Create a consistent backup using SQLite backup command
        sqlite3 "$db_file" ".backup '${backup_db}'"
        success "Database backed up successfully"

        # Also backup as SQL for human readability
        sqlite3 "$db_file" ".dump" > "${BACKUP_DIR}/${BACKUP_NAME}/vpsweb_schema.sql"
        success "Database schema exported as SQL"
    else
        warning "Database file not found at $db_file"
    fi
}

# Backup configuration files
backup_config() {
    log "Backing up configuration files..."

    local config_backup="${BACKUP_DIR}/${BACKUP_NAME}/config"
    mkdir -p "$config_backup"

    # Backup config directory
    if [[ -d "${PROJECT_ROOT}/config" ]]; then
        cp -r "${PROJECT_ROOT}/config" "$config_backup/"
        success "Configuration files backed up"
    else
        warning "Config directory not found"
    fi

    # Backup environment files if they exist
    for env_file in ".env" ".env.local" ".env.production"; do
        if [[ -f "${PROJECT_ROOT}/${env_file}" ]]; then
            cp "${PROJECT_ROOT}/${env_file}" "$config_backup/"
            success "Environment file ${env_file} backed up"
        fi
    done
}

# Backup source code (exclude build artifacts and cache)
backup_source() {
    log "Backing up source code..."

    local source_backup="${BACKUP_DIR}/${BACKUP_NAME}/src"
    mkdir -p "$source_backup"

    if [[ -d "${PROJECT_ROOT}/src" ]]; then
        # Use rsync to exclude unnecessary files
        rsync -av --exclude='__pycache__' \
                  --exclude='*.pyc' \
                  --exclude='*.pyo' \
                  --exclude='.pytest_cache' \
                  --exclude='*.egg-info' \
                  --exclude='.mypy_cache' \
                  --exclude='.coverage' \
                  --exclude='htmlcov' \
                  "${PROJECT_ROOT}/src/" "$source_backup/"
        success "Source code backed up"
    else
        warning "Source directory not found"
    fi
}

# Backup outputs and generated data
backup_outputs() {
    log "Backing up outputs and generated data..."

    local outputs_backup="${BACKUP_DIR}/${BACKUP_NAME}/outputs"
    mkdir -p "$outputs_backup"

    if [[ -d "${PROJECT_ROOT}/outputs" ]]; then
        # Backup outputs but exclude potentially large cache files
        rsync -av --exclude='.cache' \
                  --exclude='*.tmp' \
                  --exclude='*.log' \
                  "${PROJECT_ROOT}/outputs/" "$outputs_backup/"
        success "Outputs backed up"
    else
        warning "Outputs directory not found"
    fi
}

# Backup tests and documentation
backup_docs_tests() {
    log "Backing up tests and documentation..."

    local docs_backup="${BACKUP_DIR}/${BACKUP_NAME}/docs"
    mkdir -p "$docs_backup"

    # Backup tests
    if [[ -d "${PROJECT_ROOT}/tests" ]]; then
        cp -r "${PROJECT_ROOT}/tests" "$docs_backup/"
        success "Tests backed up"
    fi

    # Backup documentation
    if [[ -d "${PROJECT_ROOT}/docs" ]]; then
        cp -r "${PROJECT_ROOT}/docs" "$docs_backup/"
        success "Documentation backed up"
    fi

    # Backup key project files
    for file in "README.md" "pyproject.toml" "poetry.lock" "CLAUDE.md" "DEVELOPMENT.md" "STATUS.md" "ToDos.md"; do
        if [[ -f "${PROJECT_ROOT}/${file}" ]]; then
            cp "${PROJECT_ROOT}/${file}" "${docs_backup}/"
        fi
    done
    success "Key project files backed up"
}

# Create backup metadata
create_metadata() {
    log "Creating backup metadata..."

    local metadata_file="${BACKUP_DIR}/${BACKUP_NAME}/backup_info.json"

    cat > "$metadata_file" << EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$TIMESTAMP",
    "created_at": "$(date -Iseconds)",
    "project_root": "$PROJECT_ROOT",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'N/A')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')",
    "git_status": "$(git status --porcelain 2>/dev/null || echo 'N/A')",
    "python_version": "$(python --version 2>/dev/null || echo 'N/A')",
    "os_info": "$(uname -a)",
    "backup_contents": {
        "database": "SQLite database and schema dump",
        "config": "Configuration files and environment variables",
        "source": "Source code (excluding build artifacts)",
        "outputs": "Generated outputs and translations",
        "docs": "Documentation, tests, and project files"
    }
}
EOF

    success "Backup metadata created"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."

    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"

    success "Backup compressed: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

    # Remove uncompressed directory
    rm -rf "$BACKUP_NAME"
    success "Temporary uncompressed backup removed"
}

# Cleanup old backups (keep last 10)
cleanup_old_backups() {
    log "Cleaning up old backups (keeping last 10)..."

    cd "$BACKUP_DIR"
    ls -1t vpsweb_backup_*.tar.gz | tail -n +11 | xargs -r rm

    success "Old backups cleaned up"
}

# Verify backup
verify_backup() {
    log "Verifying backup integrity..."

    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

    if [[ -f "$backup_file" ]]; then
        # Test tar file integrity
        if tar -tzf "$backup_file" > /dev/null; then
            success "Backup verification passed"

            # Show backup size
            local size=$(du -h "$backup_file" | cut -f1)
            log "Backup size: $size"
        else
            error "Backup verification failed"
            return 1
        fi
    else
        error "Backup file not found"
        return 1
    fi
}

# Main backup function
main() {
    log "Starting VPSWeb backup process..."
    log "Backup name: $BACKUP_NAME"

    # Check prerequisites
    if ! command -v sqlite3 &> /dev/null; then
        error "sqlite3 command not found"
        exit 1
    fi

    if ! command -v rsync &> /dev/null; then
        error "rsync command not found"
        exit 1
    fi

    # Execute backup steps
    setup_backup_dir
    backup_database
    backup_config
    backup_source
    backup_outputs
    backup_docs_tests
    create_metadata
    compress_backup
    cleanup_old_backups
    verify_backup

    success "VPSWeb backup completed successfully!"
    success "Backup location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

    # Show backup summary
    echo
    log "Backup Summary:"
    log "- Backup name: $BACKUP_NAME"
    log "- Location: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
    log "- Timestamp: $(date)"
    log "- Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
    echo
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "VPSWeb Backup Script v0.3.1"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-compress  Create backup without compression"
        echo "  --verify-only  Verify existing backup only"
        echo
        exit 0
        ;;
    --no-compress)
        log "Running backup without compression..."
        # Run all steps except compression
        setup_backup_dir
        backup_database
        backup_config
        backup_source
        backup_outputs
        backup_docs_tests
        create_metadata
        verify_backup
        success "Uncompressed backup created: ${BACKUP_DIR}/${BACKUP_NAME}"
        ;;
    --verify-only)
        if [[ -n "${2:-}" ]]; then
            backup_file="$2"
        else
            # Find latest backup
            backup_file=$(ls -1t "${BACKUP_DIR}"/vpsweb_backup_*.tar.gz 2>/dev/null | head -1)
        fi

        if [[ -f "$backup_file" ]]; then
            log "Verifying backup: $backup_file"
            if tar -tzf "$backup_file" > /dev/null; then
                success "Backup verification passed"
            else
                error "Backup verification failed"
                exit 1
            fi
        else
            error "No backup file found"
            exit 1
        fi
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac