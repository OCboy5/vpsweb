#!/bin/bash
# Daily development setup script
# Based on VPSWeb project daily workflow

set -e

echo "🌅 Daily Development Setup"
echo "========================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "INFO" ]; then
        echo -e "${YELLOW}ℹ️  $message${NC}"
    fi
}

# Sync with latest changes
print_status "INFO" "Syncing with repository..."
git pull origin main 2>/dev/null || echo "No remote or up to date"

# Verify environment
print_status "INFO" "Verifying Poetry environment..."
poetry install

# Set environment variables
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
echo "🔧 PYTHONPATH set to: $PYTHONPATH"

# Quick health check
print_status "INFO" "Running quick health check..."
if python -c "from project_name.core import CoreComponent; print('✅ Import check passed')" 2>/dev/null; then
    print_status "PASS" "Import health check"
else
    print_status "INFO" "Import check: adjust import to match your project structure"
fi

# Morning quality check
print_status "INFO" "Morning quality check..."

if poetry run black --check src/ tests/ 2>/dev/null; then
    print_status "PASS" "Code formatting"
else
    print_status "INFO" "Code formatting needs attention"
fi

if poetry run flake8 src/ tests/ 2>/dev/null; then
    print_status "PASS" "Linting"
else
    print_status "INFO" "Linting issues found"
fi

# Check project tracking status
if [ -f "docs/claudecode/current_phase.md" ]; then
    print_status "PASS" "Project tracking is active"
else
    print_status "INFO" "Initialize project tracking with docs/best_practice/templates/phase_tracking.md"
fi

echo ""
print_status "PASS" "Daily setup complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Run './scripts/quality-gate.sh' for comprehensive validation"
echo "   2. Review 'docs/best_practice/04-development-workflow.md' for daily workflow"
echo "   3. Update your progress in docs/claudecode/current_phase.md"