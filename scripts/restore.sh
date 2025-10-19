#!/bin/bash
# VPSWeb Repository Restore Script v0.3.1
#
# This script restores VPSWeb repository system from a comprehensive backup
# including database, files, configuration, and outputs.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"

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

# Show usage
show_usage() {
    echo "VPSWeb Restore Script v0.3.1"
    echo
    echo "Usage: $0 [OPTIONS] <backup_file>"
    echo
    echo "Arguments:"
    echo "  backup_file    Path to backup file (.tar.gz)"
    echo
    echo "Options:"
    echo "  --help, -h     Show this help message"
    echo "  --list         List available backups"
    echo "  --dry-run      Show what would be restored without doing it"
    echo "  --db-only      Restore only database"
    echo "  --config-only  Restore only configuration"
    echo "  --source-only  Restore only source code"
    echo "  --outputs-only Restore only outputs"
    echo "  --force        Force restore (overwrite existing files)"
    echo
    echo "Examples:"
    echo "  $0 --list                                    # List available backups"
    echo "  $0 backups/vpsweb_backup_20231019_120000.tar.gz    # Full restore"
    echo "  $0 --db-only backups/vpsweb_backup_20231019_120000.tar.gz  # Database only"
    echo "  $0 --dry-run backups/vpsweb_backup_20231019_120000.tar.gz  # Preview restore"
    echo
}

# List available backups
list_backups() {
    log "Listing available backups..."
    echo

    if [[ -d "$BACKUP_DIR" ]]; then
        local backups=($(ls -1t "${BACKUP_DIR}"/vpsweb_backup_*.tar.gz 2>/dev/null))

        if [[ ${#backups[@]} -eq 0 ]]; then
            warning "No backups found in $BACKUP_DIR"
            return 1
        fi

        echo "Available backups:"
        echo

        for i in "${!backups[@]}"; do
            local backup="${backups[$i]}"
            local basename=$(basename "$backup")
            local size=$(du -h "$backup" | cut -f1)
            local date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c "%y" "$backup" 2>/dev/null | cut -d' ' -f1-2)

            echo "  $((i+1)). $basename"
            echo "     Size: $size, Date: $date"
            echo

            # Show backup info if possible
            if tar -tzf "$backup" | grep -q "backup_info.json"; then
                local temp_dir=$(mktemp -d)
                tar -xzf "$backup" -C "$temp_dir" "*/backup_info.json" 2>/dev/null || true

                local info_file=$(find "$temp_dir" -name "backup_info.json" | head -1)
                if [[ -f "$info_file" ]]; then
                    local git_commit=$(python -c "import json; print(json.load(open('$info_file')).get('git_commit', 'N/A')[:7])" 2>/dev/null || echo "N/A")
                    local created_at=$(python -c "import json; print(json.load(open('$info_file')).get('created_at', 'N/A')[:19])" 2>/dev/null || echo "N/A")
                    echo "     Git: $git_commit, Created: $created_at"
                fi
                rm -rf "$temp_dir"
            fi
            echo
        done
    else
        warning "Backup directory not found: $BACKUP_DIR"
        return 1
    fi
}

# Validate backup file
validate_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
        return 1
    fi

    if [[ ! "$backup_file" =~ \.tar\.gz$ ]]; then
        error "Backup file must be a .tar.gz file: $backup_file"
        return 1
    fi

    # Test tar file integrity
    if ! tar -tzf "$backup_file" > /dev/null; then
        error "Backup file is corrupted or invalid: $backup_file"
        return 1
    fi

    # Check if it contains expected structure
    if ! tar -tzf "$backup_file" | grep -q "backup_info.json"; then
        warning "Backup file does not contain metadata (may be older format)"
    fi

    success "Backup file validation passed: $backup_file"
}

# Extract backup to temporary directory
extract_backup() {
    local backup_file="$1"
    local temp_dir="$2"

    log "Extracting backup: $backup_file"

    mkdir -p "$temp_dir"
    tar -xzf "$backup_file" -C "$temp_dir"

    # Find the actual backup directory (it might be nested)
    local backup_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "vpsweb_backup_*" | head -1)

    if [[ -z "$backup_dir" ]]; then
        error "Invalid backup structure - backup directory not found"
        return 1
    fi

    echo "$backup_dir"
}

# Show backup metadata
show_backup_info() {
    local backup_dir="$1"
    local metadata_file="${backup_dir}/backup_info.json"

    if [[ -f "$metadata_file" ]]; then
        log "Backup Information:"
        echo

        # Use Python to parse and display JSON nicely
        python -c "
import json
import sys
try:
    with open('$metadata_file') as f:
        data = json.load(f)

    print(f'Backup Name: {data.get(\"backup_name\", \"Unknown\")}')
    print(f'Created At: {data.get(\"created_at\", \"Unknown\")}')
    print(f'Git Commit: {data.get(\"git_commit\", \"Unknown\")}')
    print(f'Git Branch: {data.get(\"git_branch\", \"Unknown\")}')
    print(f'Python Version: {data.get(\"python_version\", \"Unknown\")}')
    print(f'OS Info: {data.get(\"os_info\", \"Unknown\")}')

    contents = data.get('backup_contents', {})
    if contents:
        print()
        print('Backup Contents:')
        for key, value in contents.items():
            print(f'  - {key}: {value}')
except Exception as e:
    print(f'Error reading metadata: {e}')
" 2>/dev/null || echo "Could not parse backup metadata"
        echo
    fi
}

# Restore database
restore_database() {
    local backup_dir="$1"
    local force_restore="${2:-false}"

    log "Restoring database..."

    local db_file="${PROJECT_ROOT}/data/vpsweb.db"
    local backup_db="${backup_dir}/vpsweb.db"
    local backup_sql="${backup_dir}/vpsweb_schema.sql"

    # Create data directory if it doesn't exist
    mkdir -p "$(dirname "$db_file")"

    # Check if database already exists
    if [[ -f "$db_file" ]] && [[ "$force_restore" != "true" ]]; then
        read -p "Database file exists. Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warning "Database restore skipped"
            return 0
        fi
    fi

    if [[ -f "$backup_db" ]]; then
        # Direct database file restore
        cp "$backup_db" "$db_file"
        success "Database restored from file"
    elif [[ -f "$backup_sql" ]]; then
        # Restore from SQL dump
        sqlite3 "$db_file" < "$backup_sql"
        success "Database restored from SQL dump"
    else
        warning "No database backup found"
        return 1
    fi

    # Verify database integrity
    if sqlite3 "$db_file" "PRAGMA integrity_check;" | grep -q "ok"; then
        success "Database integrity check passed"
    else
        error "Database integrity check failed"
        return 1
    fi
}

# Restore configuration
restore_config() {
    local backup_dir="$1"
    local force_restore="${2:-false}"

    log "Restoring configuration..."

    local backup_config="${backup_dir}/config"

    if [[ ! -d "$backup_config" ]]; then
        warning "No configuration backup found"
        return 1
    fi

    # Restore config directory
    if [[ -d "${backup_config}/config" ]]; then
        if [[ -d "${PROJECT_ROOT}/config" ]] && [[ "$force_restore" != "true" ]]; then
            read -p "Config directory exists. Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                warning "Configuration restore skipped"
                return 0
            fi
        fi

        cp -r "${backup_config}/config" "${PROJECT_ROOT}/"
        success "Configuration directory restored"
    fi

    # Restore environment files
    for env_file in ".env" ".env.local" ".env.production"; do
        local backup_env="${backup_config}/${env_file}"
        if [[ -f "$backup_env" ]]; then
            local target_env="${PROJECT_ROOT}/${env_file}"
            if [[ -f "$target_env" ]] && [[ "$force_restore" != "true" ]]; then
                read -p "Environment file ${env_file} exists. Overwrite? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    continue
                fi
            fi
            cp "$backup_env" "$target_env"
            success "Environment file ${env_file} restored"
        fi
    done
}

# Restore source code
restore_source() {
    local backup_dir="$1"
    local force_restore="${2:-false}"

    log "Restoring source code..."

    local backup_source="${backup_dir}/src"

    if [[ ! -d "$backup_source" ]]; then
        warning "No source code backup found"
        return 1
    fi

    if [[ -d "${PROJECT_ROOT}/src" ]] && [[ "$force_restore" != "true" ]]; then
        read -p "Source directory exists. Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warning "Source code restore skipped"
            return 0
        fi
    fi

    cp -r "$backup_source" "${PROJECT_ROOT}/"
    success "Source code restored"
}

# Restore outputs
restore_outputs() {
    local backup_dir="$1"
    local force_restore="${2:-false}"

    log "Restoring outputs..."

    local backup_outputs="${backup_dir}/outputs"

    if [[ ! -d "$backup_outputs" ]]; then
        warning "No outputs backup found"
        return 1
    fi

    if [[ -d "${PROJECT_ROOT}/outputs" ]] && [[ "$force_restore" != "true" ]]; then
        read -p "Outputs directory exists. Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warning "Outputs restore skipped"
            return 0
        fi
    fi

    cp -r "$backup_outputs" "${PROJECT_ROOT}/"
    success "Outputs restored"
}

# Restore documentation and tests
restore_docs_tests() {
    local backup_dir="$1"
    local force_restore="${2:-false}"

    log "Restoring documentation and tests..."

    local backup_docs="${backup_dir}/docs"

    if [[ ! -d "$backup_docs" ]]; then
        warning "No documentation backup found"
        return 1
    fi

    # Restore tests
    if [[ -d "${backup_docs}/tests" ]]; then
        if [[ -d "${PROJECT_ROOT}/tests" ]] && [[ "$force_restore" != "true" ]]; then
            read -p "Tests directory exists. Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                warning "Tests restore skipped"
            else
                cp -r "${backup_docs}/tests" "${PROJECT_ROOT}/"
                success "Tests restored"
            fi
        else
            cp -r "${backup_docs}/tests" "${PROJECT_ROOT}/"
            success "Tests restored"
        fi
    fi

    # Restore documentation
    if [[ -d "${backup_docs}/docs" ]]; then
        if [[ -d "${PROJECT_ROOT}/docs" ]] && [[ "$force_restore" != "true" ]]; then
            read -p "Documentation directory exists. Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                warning "Documentation restore skipped"
            else
                cp -r "${backup_docs}/docs" "${PROJECT_ROOT}/"
                success "Documentation restored"
            fi
        else
            cp -r "${backup_docs}/docs" "${PROJECT_ROOT}/"
            success "Documentation restored"
        fi
    fi

    # Restore key project files
    for file in "README.md" "pyproject.toml" "poetry.lock" "CLAUDE.md" "DEVELOPMENT.md" "STATUS.md" "ToDos.md"; do
        local backup_file="${backup_docs}/${file}"
        if [[ -f "$backup_file" ]]; then
            local target_file="${PROJECT_ROOT}/${file}"
            if [[ -f "$target_file" ]] && [[ "$force_restore" != "true" ]]; then
                read -p "Project file ${file} exists. Overwrite? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    continue
                fi
            fi
            cp "$backup_file" "$target_file"
            success "Project file ${file} restored"
        fi
    done
}

# Main restore function
main() {
    local backup_file="$1"
    local db_only="${2:-false}"
    local config_only="${3:-false}"
    local source_only="${4:-false}"
    local outputs_only="${5:-false}"
    local dry_run="${6:-false}"
    local force_restore="${7:-false}"

    log "Starting VPSWeb restore process..."
    log "Backup file: $backup_file"

    # Validate backup
    validate_backup "$backup_file"

    # Extract backup to temporary directory
    local temp_dir=$(mktemp -d)
    trap "rm -rf '$temp_dir'" EXIT

    local backup_dir=$(extract_backup "$backup_file" "$temp_dir")

    # Show backup information
    show_backup_info "$backup_dir"

    if [[ "$dry_run" == "true" ]]; then
        log "DRY RUN: Showing what would be restored..."
        echo

        if [[ -f "${backup_dir}/vpsweb.db" ]] || [[ -f "${backup_dir}/vpsweb_schema.sql" ]]; then
            echo "✓ Database would be restored"
        fi

        if [[ -d "${backup_dir}/config" ]]; then
            echo "✓ Configuration files would be restored"
        fi

        if [[ -d "${backup_dir}/src" ]]; then
            echo "✓ Source code would be restored"
        fi

        if [[ -d "${backup_dir}/outputs" ]]; then
            echo "✓ Outputs would be restored"
        fi

        if [[ -d "${backup_dir}/docs" ]]; then
            echo "✓ Documentation and tests would be restored"
        fi

        echo
        success "Dry run completed. Use --force to actually restore."
        return 0
    fi

    # Perform restore based on options
    if [[ "$db_only" == "true" ]]; then
        restore_database "$backup_dir" "$force_restore"
    elif [[ "$config_only" == "true" ]]; then
        restore_config "$backup_dir" "$force_restore"
    elif [[ "$source_only" == "true" ]]; then
        restore_source "$backup_dir" "$force_restore"
    elif [[ "$outputs_only" == "true" ]]; then
        restore_outputs "$backup_dir" "$force_restore"
    else
        # Full restore
        restore_database "$backup_dir" "$force_restore"
        restore_config "$backup_dir" "$force_restore"
        restore_source "$backup_dir" "$force_restore"
        restore_outputs "$backup_dir" "$force_restore"
        restore_docs_tests "$backup_dir" "$force_restore"
    fi

    success "VPSWeb restore completed successfully!"

    # Show next steps
    echo
    log "Next Steps:"
    log "1. Verify database integrity: sqlite3 data/vpsweb.db 'PRAGMA integrity_check;'"
    log "2. Install dependencies: poetry install"
    log "3. Run database migrations if needed: alembic upgrade head"
    log "4. Test the application: python -m vpsweb.webui.main --help"
    echo
}

# Parse command line arguments
DB_ONLY=false
CONFIG_ONLY=false
SOURCE_ONLY=false
OUTPUTS_ONLY=false
DRY_RUN=false
FORCE_RESTORE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_usage
            exit 0
            ;;
        --list)
            list_backups
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --source-only)
            SOURCE_ONLY=true
            shift
            ;;
        --outputs-only)
            OUTPUTS_ONLY=true
            shift
            ;;
        --force)
            FORCE_RESTORE=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            if [[ -z "${BACKUP_FILE:-}" ]]; then
                BACKUP_FILE="$1"
            else
                error "Too many arguments"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [[ "${DRY_RUN}" == "false" ]] && [[ -z "${BACKUP_FILE:-}" ]]; then
    error "Backup file is required"
    show_usage
    exit 1
fi

# Validate mutually exclusive options
if [[ "$DB_ONLY" == "true" ]] && [[ "$CONFIG_ONLY" == "true" || "$SOURCE_ONLY" == "true" || "$OUTPUTS_ONLY" == "true" ]]; then
    error "Cannot combine --db-only with other selective restore options"
    exit 1
fi

if [[ "$CONFIG_ONLY" == "true" ]] && [[ "$SOURCE_ONLY" == "true" || "$OUTPUTS_ONLY" == "true" ]]; then
    error "Cannot combine --config-only with other selective restore options"
    exit 1
fi

if [[ "$SOURCE_ONLY" == "true" ]] && [[ "$OUTPUTS_ONLY" == "true" ]]; then
    error "Cannot combine --source-only with --outputs-only"
    exit 1
fi

# Execute main function
if [[ "${DRY_RUN}" == "false" ]]; then
    main "$BACKUP_FILE" "$DB_ONLY" "$CONFIG_ONLY" "$SOURCE_ONLY" "$OUTPUTS_ONLY" "$DRY_RUN" "$FORCE_RESTORE"
fi