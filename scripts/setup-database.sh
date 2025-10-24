#!/bin/bash
# VPSWeb Database Setup Script v0.3.2
#
# Dedicated script for database initialization and management
# This script handles all database-related operations separately from main setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/database-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

step() {
    echo -e "${PURPLE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Show usage
show_usage() {
    echo "VPSWeb Database Setup Script v0.3.2"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  init         Initialize database with migrations"
    echo "  reset        Reset database (delete and recreate)"
    echo "  backup       Backup current database"
    echo "  status       Show database status and information"
    echo "  help         Show this help message"
    echo
    echo "Examples:"
    echo "  $0 init      # Initialize database for first time"
    echo "  $0 reset     # Reset database to clean state"
    echo "  $0 status    # Check database status"
}

# Check prerequisites
check_prerequisites() {
    step "Checking prerequisites..."

    # Check Poetry
    if command -v poetry &> /dev/null; then
        success "Poetry is available"
    else
        error "Poetry is not installed. Please run main setup script first."
        exit 1
    fi

    # Check project structure
    if [[ ! -d "${PROJECT_ROOT}/src/vpsweb/repository" ]]; then
        error "Repository directory not found. Please run main setup script first."
        exit 1
    fi

    # Set PYTHONPATH
    export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"
    info "PYTHONPATH set to: ${PROJECT_ROOT}/src"
}

# Initialize database
init_database() {
    step "Initializing VPSWeb database..."

    cd "$PROJECT_ROOT"

    # Create repository directory
    mkdir -p repository_root
    info "Repository directory ensured: $(pwd)/repository_root"

    # Check if database already exists
    if [[ -f "repository_root/repo.db" ]]; then
        warning "Database file already exists"
        read -p "Do you want to reset it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -f repository_root/repo.db
            info "Existing database removed"
        else
            info "Keeping existing database"
            return 0
        fi
    fi

    # Run database migrations
    info "Running database migrations..."
    cd src/vpsweb/repository

    if poetry run alembic upgrade head; then
        success "Database migrations completed successfully"
    else
        error "Database migrations failed"
        cd - > /dev/null
        exit 1
    fi

    cd - > /dev/null

    # Verify database creation
    if [[ -f "repository_root/repo.db" ]]; then
        DB_SIZE=$(du -h repository_root/repo.db | cut -f1)
        success "Database created successfully (size: $DB_SIZE)"

        # Show basic stats
        TABLE_COUNT=$(sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
        info "Database contains $TABLE_COUNT tables"
    else
        error "Database file not found after migrations"
        exit 1
    fi
}

# Reset database
reset_database() {
    step "Resetting VPSWeb database..."

    cd "$PROJECT_ROOT"

    # Stop any running processes
    pkill -f "vpsweb" || true

    # Remove database file
    if [[ -f "repository_root/repo.db" ]]; then
        rm -f repository_root/repo.db
        success "Database file removed"
    else
        info "No database file to remove"
    fi

    # Recreate database
    mkdir -p repository_root
    export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"
    cd src/vpsweb/repository

    if poetry run alembic upgrade head; then
        success "Database reset completed successfully"
    else
        error "Database reset failed"
        cd - > /dev/null
        exit 1
    fi

    cd - > /dev/null
    success "Database is now in clean state"
}

# Backup database
backup_database() {
    step "Creating database backup..."

    cd "$PROJECT_ROOT"

    if [[ ! -f "repository_root/repo.db" ]]; then
        error "Database file not found"
        exit 1
    fi

    # Create backup directory
    mkdir -p repository_root/backups

    # Create backup with timestamp
    BACKUP_FILE="repository_root/backups/repo_backup_$(date +%Y%m%d_%H%M%S).db"

    if cp repository_root/repo.db "$BACKUP_FILE"; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        success "Database backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        error "Failed to create backup"
        exit 1
    fi
}

# Show database status
show_status() {
    step "Database status..."

    cd "$PROJECT_ROOT"

    if [[ -f "repository_root/repo.db" ]]; then
        DB_SIZE=$(du -h repository_root/repo.db | cut -f1)
        DB_MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" repository_root/repo.db)

        success "Database file exists"
        info "  Size: $DB_SIZE"
        info "  Modified: $DB_MODIFIED"
        info "  Location: $(pwd)/repository_root/repo.db"

        # Show table information
        echo
        info "Database tables:"
        sqlite3 repository_root/repo.db ".tables" 2>/dev/null | while read -r table; do
            if [[ -n "$table" ]]; then
                COUNT=$(sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
                info "  - $table: $COUNT records"
            fi
        done

        # Show recent backups
        echo
        info "Recent backups:"
        ls -la repository_root/backups/*.db 2>/dev/null | tail -3 | while read -r line; do
            if [[ -n "$line" ]]; then
                info "  - $line"
            fi
        done || info "  No backups found"

    else
        warning "Database file does not exist"
        info "Run '$0 init' to create the database"
    fi
}

# Test database connection
test_connection() {
    step "Testing database connection..."

    cd "$PROJECT_ROOT"
    export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"

    if poetry run python -c "
import os
# Unset any conflicting environment variables
os.environ.pop('REPO_DATABASE_URL', None)

from vpsweb.repository.database import check_db_connection, create_session
from vpsweb.repository.service import RepositoryWebService

try:
    # Test basic connection
    if check_db_connection():
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
        exit(1)

    # Test service layer
    db = create_session()
    service = RepositoryWebService(db)
    stats = service.get_repository_stats()
    db.close()

    print(f'✅ Repository service working')
    print(f'   - Total poems: {stats.total_poems}')
    print(f'   - Total translations: {stats.total_translations}')

except Exception as e:
    print(f'❌ Database test failed: {e}')
    exit(1)
"; then
        success "Database connection test passed"
    else
        error "Database connection test failed"
        exit 1
    fi
}

# Main execution
main() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              VPSWeb Database Setup Script                  ║"
    echo "║                          v0.3.2                             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo

    # Initialize log file
    echo "VPSWeb Database Setup Log - $(date)" > "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"

    # Handle command line arguments
    case "${1:-help}" in
        init)
            check_prerequisites
            init_database
            test_connection
            ;;
        reset)
            check_prerequisites
            reset_database
            test_connection
            ;;
        backup)
            backup_database
            ;;
        status)
            show_status
            ;;
        test)
            check_prerequisites
            test_connection
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac

    echo
    success "Database setup completed successfully! 🎉"
}

# Run main function with all arguments
main "$@"