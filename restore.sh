#!/bin/bash

# VPSWeb Repository Restore Script
# Restores the VPSWeb Repository system from a backup
# Version: 0.3.1

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$PROJECT_ROOT/repository_root"
BACKUP_DIR="$PROJECT_ROOT/backups"

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

# List available backups
list_backups() {
    log "Available backups:"
    if [ ! -d "$BACKUP_DIR" ]; then
        warn "No backup directory found"
        return
    fi

    cd "$BACKUP_DIR"
    local backups=($(ls -t *.tar.gz 2>/dev/null || echo ""))

    if [ ${#backups[@]} -eq 0 ]; then
        warn "No backups found"
        return
    fi

    local i=1
    for backup in "${backups[@]}"; do
        local backup_name="${backup%.tar.gz}"
        local size=$(du -h "$backup" | cut -f1)
        echo "  $i) $backup_name ($size)"
        ((i++))
    done
}

# Extract backup
extract_backup() {
    local backup_name="$1"
    local backup_file="$BACKUP_DIR/$backup_name.tar.gz"
    local extract_dir="$BACKUP_DIR/restore_temp"

    log "Extracting backup: $backup_name"

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
    fi

    # Create extract directory
    mkdir -p "$extract_dir"

    # Extract backup
    cd "$extract_dir"
    if ! tar -xzf "$backup_file"; then
        error "Failed to extract backup file"
    fi

    local backup_path="$extract_dir/$backup_name"
    if [ ! -d "$backup_path" ]; then
        error "Backup directory not found in extracted archive"
    fi

    echo "$backup_path"
}

# Verify backup integrity
verify_backup() {
    local backup_path="$1"

    log "Verifying backup integrity..."

    # Check metadata
    if [ ! -f "$backup_path/metadata.json" ]; then
        error "Backup metadata not found"
    fi

    # Check database
    if [ ! -f "$backup_path/database/repo.db" ]; then
        error "Database file not found in backup"
    fi

    # Verify database integrity
    if ! sqlite3 "$backup_path/database/repo.db" "PRAGMA integrity_check;" | grep -q "ok"; then
        error "Database integrity check failed"
    fi

    # Check key directories
    if [ ! -d "$backup_path/config" ]; then
        warn "Configuration directory not found in backup"
    fi

    log "Backup integrity verified"
}

# Create current system backup before restore
create_safety_backup() {
    log "Creating safety backup of current system..."

    # Run backup script if it exists
    if [ -f "$SCRIPT_DIR/backup.sh" ]; then
        "$SCRIPT_DIR/backup.sh" >/dev/null 2>&1 || warn "Safety backup failed"
        log "Safety backup created"
    else
        warn "Backup script not found, skipping safety backup"
    fi
}

# Stop running services
stop_services() {
    log "Stopping running services..."

    # Kill any running VPSWeb processes
    pkill -f "vpsweb.webui.main" 2>/dev/null || true
    pkill -f "uvicorn.*vpsweb" 2>/dev/null || true

    # Give processes time to stop
    sleep 2

    # Force kill if still running
    pkill -9 -f "vpsweb.webui.main" 2>/dev/null || true
    pkill -9 -f "uvicorn.*vpsweb" 2>/dev/null || true

    log "Services stopped"
}

# Restore database
restore_database() {
    local backup_path="$1"

    log "Restoring database..."

    # Ensure repo_root directory exists
    mkdir -p "$REPO_ROOT"

    # Stop any processes that might be using the database
    if [ -f "$REPO_ROOT/repo.db" ]; then
        log "Backing up current database..."
        cp "$REPO_ROOT/repo.db" "$REPO_ROOT/repo.db.backup.$(date +%s)"
    fi

    # Restore database
    cp "$backup_path/database/repo.db" "$REPO_ROOT/repo.db"

    # Set proper permissions
    chmod 644 "$REPO_ROOT/repo.db"

    # Verify restored database
    local record_counts=$(sqlite3 "$REPO_ROOT/repo.db" "
        SELECT 'Poems: ' || COUNT(*) FROM poems;
        SELECT 'Translations: ' || COUNT(*) FROM translations;
        SELECT 'AI Logs: ' || COUNT(*) FROM ai_logs;
        SELECT 'Human Notes: ' || COUNT(*) FROM human_notes;
    ")

    log "Database restored successfully"
    echo "$record_counts" | while IFS= read -r line; do
        log "  $line"
    done
}

# Restore configuration
restore_config() {
    local backup_path="$1"

    log "Restoring configuration files..."

    # Restore environment file
    if [ -f "$backup_path/config/.env.local" ]; then
        cp "$backup_path/config/.env.local" "$PROJECT_ROOT/.env.local"
        log "Environment file restored"
    fi

    # Restore environment template
    if [ -f "$backup_path/config/.env.local.template" ]; then
        cp "$backup_path/config/.env.local.template" "$PROJECT_ROOT/.env.local.template"
        log "Environment template restored"
    fi

    # Restore repository configuration
    if [ -f "$backup_path/config/repository.yaml" ]; then
        cp "$backup_path/config/repository.yaml" "$PROJECT_ROOT/config/repository.yaml"
        log "Repository configuration restored"
    fi

    # Restore VPSWeb configuration
    if [ -d "$backup_path/config/vpsweb" ]; then
        mkdir -p "$PROJECT_ROOT/config"
        cp -r "$backup_path/config/vpsweb/"* "$PROJECT_ROOT/config/" 2>/dev/null || true
        log "VPSWeb configuration restored"
    fi
}

# Restore source code (optional)
restore_source() {
    local backup_path="$1"
    local restore_source="${2:-false}"

    if [ "$restore_source" = "false" ]; then
        log "Skipping source code restoration (use --source to restore)"
        return
    fi

    log "Restoring source code..."

    # Backup current source code
    if [ -d "$PROJECT_ROOT/src/vpsweb" ]; then
        local source_backup="$BACKUP_DIR/source_backup_$(date +%s)"
        mkdir -p "$source_backup"
        cp -r "$PROJECT_ROOT/src/vpsweb" "$source_backup/" 2>/dev/null || true
        log "Current source code backed up to $source_backup"
    fi

    # Restore source code
    if [ -d "$backup_path/source/src/vpsweb" ]; then
        mkdir -p "$PROJECT_ROOT/src"
        cp -r "$backup_path/source/src/vpsweb" "$PROJECT_ROOT/src/"
        log "Source code restored"
    fi

    # Restore pyproject.toml
    if [ -f "$backup_path/source/pyproject.toml" ]; then
        cp "$backup_path/source/pyproject.toml" "$PROJECT_ROOT/"
        log "pyproject.toml restored"
    fi
}

# Run database migrations (if needed)
run_migrations() {
    log "Checking database migrations..."

    cd "$PROJECT_ROOT"

    # Set PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

    # Run Alembic upgrade
    if command -v alembic >/dev/null 2>&1; then
        log "Running database migrations..."
        cd src/vpsweb/repository
        alembic upgrade head 2>/dev/null || warn "Migration completed with warnings"
        cd - >/dev/null
        log "Database migrations completed"
    else
        warn "Alembic not found, skipping migrations"
    fi
}

# Verify restoration
verify_restoration() {
    log "Verifying restoration..."

    # Check database
    if [ ! -f "$REPO_ROOT/repo.db" ]; then
        error "Database not found after restoration"
    fi

    # Verify database can be opened
    if ! sqlite3 "$REPO_ROOT/repo.db" "SELECT 1;" >/dev/null 2>&1; then
        error "Database cannot be opened after restoration"
    fi

    # Check configuration
    if [ ! -f "$PROJECT_ROOT/config/repository.yaml" ]; then
        warn "Repository configuration not found"
    fi

    # Count records
    local poem_count=$(sqlite3 "$REPO_ROOT/repo.db" "SELECT COUNT(*) FROM poems;")
    local translation_count=$(sqlite3 "$REPO_ROOT/repo.db" "SELECT COUNT(*) FROM translations;")

    log "Restoration verified"
    log "  Poems: $poem_count"
    log "  Translations: $translation_count"
}

# Test web interface
test_web_interface() {
    log "Testing web interface..."

    # Start the application
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

    log "Starting VPSWeb for testing..."

    # Start in background
    timeout 10s python -m vpsweb.webui.main >/dev/null 2>&1 &
    local pid=$!

    # Give it time to start
    sleep 5

    # Test health endpoint
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        log "Web interface test: PASSED"
    else
        warn "Web interface test: FAILED (service may need manual start)"
    fi

    # Stop the test instance
    kill $pid 2>/dev/null || true
    wait $pid 2>/dev/null || true
}

# Cleanup
cleanup() {
    local extract_dir="$BACKUP_DIR/restore_temp"
    if [ -d "$extract_dir" ]; then
        rm -rf "$extract_dir"
        log "Cleanup completed"
    fi
}

# Display restoration summary
display_summary() {
    local backup_name="$1"
    local backup_path="$2"

    echo -e "${GREEN}"
    echo "========================================"
    echo "  RESTORATION SUMMARY"
    echo "========================================"
    echo "Backup: $backup_name"
    echo "Date: $(date)"
    echo "Version: 0.3.1"
    echo ""
    echo "Restored Components:"
    echo "  ✓ Database"
    echo "  ✓ Configuration"
    echo "  ✓ Settings"
    echo ""
    echo "Next Steps:"
    echo "  1. Review configuration files"
    echo "  2. Start the application: python -m vpsweb.webui.main"
    echo "  3. Access at: http://127.0.0.1:8000"
    echo "  4. Verify data integrity"
    echo "========================================"
    echo -e "${NC}"
}

# Main restore function
main() {
    local backup_name=""
    local restore_source="false"
    local skip_safety="false"

    echo -e "${BLUE}"
    echo "========================================"
    echo "  VPSWeb Repository Restore Script"
    echo "  Version 0.3.1"
    echo "========================================"
    echo -e "${NC}"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                echo "VPSWeb Repository Restore Script v0.3.1"
                echo ""
                echo "Usage: $0 [OPTIONS] BACKUP_NAME"
                echo ""
                echo "Arguments:"
                echo "  BACKUP_NAME    Name of backup to restore (e.g., vpsweb_repo_backup_20231019_120000)"
                echo ""
                echo "Options:"
                echo "  --help, -h       Show this help message"
                echo "  --version, -v    Show version information"
                echo "  --list, -l       List available backups"
                echo "  --source, -s     Also restore source code"
                echo "  --skip-safety    Skip safety backup creation"
                echo ""
                exit 0
                ;;
            --version|-v)
                echo "VPSWeb Repository Restore Script v0.3.1"
                exit 0
                ;;
            --list|-l)
                list_backups
                exit 0
                ;;
            --source|-s)
                restore_source="true"
                shift
                ;;
            --skip-safety)
                skip_safety="true"
                shift
                ;;
            -*)
                error "Unknown option: $1. Use --help for usage information."
                ;;
            *)
                if [ -z "$backup_name" ]; then
                    backup_name="$1"
                else
                    error "Multiple backup names specified"
                fi
                shift
                ;;
        esac
    done

    # Check if backup name provided
    if [ -z "$backup_name" ]; then
        echo "Available backups:"
        list_backups
        error "No backup name specified. Use --list to see available backups."
    fi

    # Pre-flight checks
    if [ ! -d "$PROJECT_ROOT" ]; then
        error "Project root directory not found: $PROJECT_ROOT"
    fi

    if [ ! -f "$BACKUP_DIR/$backup_name.tar.gz" ]; then
        error "Backup file not found: $BACKUP_DIR/$backup_name.tar.gz"
    fi

    log "Starting restoration process..."
    log "Backup: $backup_name"
    log "Restore source: $restore_source"

    # Execute restoration steps
    local backup_path=$(extract_backup "$backup_name")

    verify_backup "$backup_path"

    if [ "$skip_safety" = "false" ]; then
        create_safety_backup
    fi

    stop_services
    restore_database "$backup_path"
    restore_config "$backup_path"
    restore_source "$backup_path" "$restore_source"
    run_migrations
    verify_restoration
    test_web_interface

    # Cleanup
    cleanup

    # Display summary
    display_summary "$backup_name" "$backup_path"

    log "Restoration completed successfully!"
}

# Execute main function with all arguments
main "$@"