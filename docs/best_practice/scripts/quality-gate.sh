#!/bin/bash
# Quality gate validation script
# Based on VPSWeb project quality standards

set -e

echo "🔍 Running Quality Gate Validation"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    print_status "FAIL" "Poetry is not installed. Please install Poetry first."
    exit 1
fi

# Check if we're in a Poetry project
if [ ! -f "pyproject.toml" ]; then
    print_status "FAIL" "Not in a Poetry project (no pyproject.toml found)"
    exit 1
fi

# Set environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Code formatting
echo "📝 Checking code formatting..."
if poetry run black --check src/ tests/ 2>/dev/null; then
    print_status "PASS" "Code formatting"
else
    print_status "FAIL" "Code formatting issues found"
    echo "Run 'poetry run black src/ tests/' to fix"
    exit 1
fi

# Linting
echo "🔍 Running linting..."
if poetry run flake8 src/ tests/ 2>/dev/null; then
    print_status "PASS" "Code linting"
else
    print_status "FAIL" "Linting issues found"
    exit 1
fi

# Type checking
echo "🔍 Running type checking..."
if poetry run mypy src/ 2>/dev/null; then
    print_status "PASS" "Type checking"
else
    print_status "FAIL" "Type checking issues found"
    exit 1
fi

# Security check
echo "🔒 Running security check..."
if poetry run safety check 2>/dev/null; then
    print_status "PASS" "Security scan"
else
    print_status "WARN" "Security vulnerabilities found (review needed)"
fi

# Tests
echo "🧪 Running tests..."
if poetry run pytest tests/ -v --cov=src --cov-report=term-missing 2>/dev/null; then
    print_status "PASS" "All tests passing"
else
    print_status "FAIL" "Test failures or insufficient coverage"
    echo "Run 'poetry run pytest tests/ -v' for details"
    exit 1
fi

echo ""
echo "🎉 All quality gates passed!"
echo "📊 Coverage report generated in htmlcov/index.html"