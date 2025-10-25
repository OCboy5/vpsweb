#!/bin/bash

# =============================================================================
# VPSWeb Complete Cleanup and Restart Script
# =============================================================================
# This script performs a complete cleanup of all VPSWeb processes and provides
# a clean restart environment. Use this whenever you encounter hanging processes
# or need a fresh testing environment.
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if port 8000 is in use
check_port_8000() {
    if lsof -i :8000 >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to forcefully kill all VPSWeb related processes
kill_all_processes() {
    print_step "Forcefully killing all VPSWeb related processes..."

    # Kill Python processes
    pkill -f "python.*uvicorn" 2>/dev/null || true
    pkill -f "uvicorn.*vpsweb" 2>/dev/null || true
    pkill -f "python.*main\.py" 2>/dev/null || true

    # Kill curl processes making requests to localhost:8000
    pkill -f "curl.*localhost:8000" 2>/dev/null || true

    # Kill script processes
    pkill -f "start\.sh" 2>/dev/null || true
    pkill -f "stop\.sh" 2>/dev/null || true

    # Give processes time to die
    sleep 3

    # Force kill any remaining processes
    if pgrep -f "uvicorn.*vpsweb" >/dev/null; then
        print_warning "Some processes survived, using force kill..."
        pkill -9 -f "uvicorn.*vpsweb" 2>/dev/null || true
        pkill -9 -f "python.*main\.py" 2>/dev/null || true
        sleep 2
    fi
}

# Function to clear log files
clear_logs() {
    print_step "Clearing all log files..."

    # Clear application logs
    find /Volumes/Work/Dev/vpsweb/vpsweb -name "*.log" -type f -delete 2>/dev/null || true

    # Clear any temp files
    find /Volumes/Work/Dev/vpsweb/vpsweb -name "*.tmp" -type f -delete 2>/dev/null || true
    find /Volumes/Work/Dev/vpsweb/vpsweb -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

    print_status "Log files cleared"
}

# Function to verify cleanup
verify_cleanup() {
    print_step "Verifying cleanup..."

    # Check for any remaining processes
    remaining_processes=$(ps aux | grep -E "(uvicorn|fastapi|python.*main\.py|python.*vpsweb)" | grep -v grep | wc -l)

    if [ "$remaining_processes" -gt 0 ]; then
        print_error "Found $remaining_processes remaining processes:"
        ps aux | grep -E "(uvicorn|fastapi|python.*main\.py|python.*vpsweb)" | grep -v grep
        return 1
    fi

    # Check if port 8000 is still in use
    if check_port_8000; then
        print_error "Port 8000 is still in use:"
        lsof -i :8000
        return 1
    fi

    print_status "Cleanup verification successful - no remaining processes found"
    return 0
}

# Function to start clean server
start_clean_server() {
    print_step "Starting clean VPSWeb server..."

    # Change to the correct directory
    cd /Volumes/Work/Dev/vpsweb/vpsweb

    # Use the official start script
    ./scripts/start.sh

    print_status "Server startup initiated"
}

# Function to show final status
show_status() {
    print_step "Final status check..."

    sleep 5  # Give server time to start

    if check_port_8000; then
        print_status "✅ Server is running on port 8000"
        print_status "✅ Web interface available at: http://localhost:8000"
        print_status "✅ Environment is clean and ready for testing"
    else
        print_error "❌ Server failed to start on port 8000"
        return 1
    fi
}

# Main execution
main() {
    echo "=================================="
    echo "🧹 VPSWeb Complete Cleanup Script"
    echo "=================================="
    echo ""

    # Check if we're in the right directory
    if [ ! -f "/Volumes/Work/Dev/vpsweb/vpsweb/scripts/start.sh" ]; then
        print_error "VPSWeb start script not found. Please run from the correct directory."
        exit 1
    fi

    # Execute cleanup steps
    kill_all_processes
    clear_logs

    # Verify cleanup worked
    if ! verify_cleanup; then
        print_error "Cleanup failed. There may be system-level process issues."
        print_error "You may need to manually kill processes or restart your terminal."
        exit 1
    fi

    echo ""
    print_status "🎉 Cleanup completed successfully!"
    echo ""

    # Ask user if they want to start the server
    echo -n "Do you want to start the clean server now? (y/n): "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        start_clean_server
        show_status
    else
        print_status "Skipping server startup. Environment is clean."
        print_status "Run './scripts/start.sh' when you're ready to start the server."
    fi

    echo ""
    echo "=================================="
    echo "✅ VPSWeb Cleanup Script Complete"
    echo "=================================="
}

# Handle script interruption
trap 'print_error "Script interrupted by user"; exit 1' INT

# Run main function
main "$@"