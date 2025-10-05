#!/bin/bash

# Development workflow quality check script (v1.0)
# Usage: ./dev-check.sh [options]
# Options:
#   --lint-only     Run only linting checks
#   --test-only     Run only tests
#   --release-mode  Run all checks for release preparation
#   --fix           Auto-fix issues where possible

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
LINT_ONLY=false
TEST_ONLY=false
RELEASE_MODE=false
AUTO_FIX=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --lint-only)
            LINT_ONLY=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --release-mode)
            RELEASE_MODE=true
            shift
            ;;
        --fix)
            AUTO_FIX=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔍 VPSWeb Development Quality Checks"
echo "=================================="

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Check if we're in the right directory
check_project_structure() {
    print_info "Checking project structure..."

    if [ ! -f "pyproject.toml" ]; then
        print_status 1 "pyproject.toml not found - not a Poetry project"
        exit 1
    fi

    if [ ! -d "src" ]; then
        print_status 1 "src directory not found"
        exit 1
    fi

    if [ ! -d "src/vpsweb" ]; then
        print_status 1 "src/vpsweb directory not found"
        exit 1
    fi

    print_status 0 "Project structure is valid"
}

# 2. Python environment and dependencies
check_python_env() {
    print_info "Checking Python environment..."

    # Check Python version
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status 0 "Python version: $PYTHON_VERSION"

    # Check Poetry
    if command -v poetry &> /dev/null; then
        POETRY_VERSION=$(poetry --version)
        print_status 0 "Poetry: $POETRY_VERSION"
    else
        print_warning "Poetry not found - installing it is recommended"
    fi

    # Check if dependencies are installed
    if [ -d ".venv" ] || poetry env info --path &> /dev/null; then
        print_status 0 "Virtual environment found"
    else
        print_warning "No virtual environment found - run 'poetry install'"
    fi
}

# 3. Linting checks
run_linting() {
    if [ "$TEST_ONLY" = true ]; then
        return 0
    fi

    print_info "Running linting checks..."

    LINT_ERRORS=0

    # Black formatting check
    print_info "Checking code formatting with Black..."
    if command -v black &> /dev/null; then
        if [ "$AUTO_FIX" = true ]; then
            black src/ --line-length 88
            print_status 0 "Code formatted with Black"
        else
            if black src/ --line-length 88 --check; then
                print_status 0 "Code formatting is correct"
            else
                print_warning "Code formatting issues found (run with --fix to auto-fix)"
                LINT_ERRORS=$((LINT_ERRORS + 1))
            fi
        fi
    else
        print_warning "Black not installed - run 'poetry add --group dev black'"
    fi

    # Flake8 linting
    print_info "Running Flake8 linter..."
    if command -v flake8 &> /dev/null; then
        if flake8 src/ --max-line-length=88 --ignore=E203,W503; then
            print_status 0 "Flake8 checks passed"
        else
            print_warning "Flake8 issues found"
            LINT_ERRORS=$((LINT_ERRORS + 1))
        fi
    else
        print_warning "Flake8 not installed - run 'poetry add --group dev flake8'"
    fi

    # MyPy type checking
    print_info "Running MyPy type checking..."
    if command -v mypy &> /dev/null; then
        if mypy src/ --ignore-missing-imports --no-strict-optional; then
            print_status 0 "MyPy checks passed"
        else
            print_warning "MyPy issues found"
            LINT_ERRORS=$((LINT_ERRORS + 1))
        fi
    else
        print_warning "MyPy not installed - run 'poetry add --group dev mypy'"
    fi

    return $LINT_ERRORS
}

# 4. Import validation
check_imports() {
    print_info "Checking Python imports..."

    # Test if main module can be imported
    if PYTHONPATH=src python3 -c "import vpsweb; print('✅ Main module imports successfully')" 2>/dev/null; then
        print_status 0 "Main module imports correctly"
    else
        print_status 1 "Main module import failed"
        return 1
    fi

    # Test CLI entry point
    if PYTHONPATH=src python3 -c "from vpsweb.__main__ import cli; print('✅ CLI entry point works')" 2>/dev/null; then
        print_status 0 "CLI entry point works"
    else
        print_status 1 "CLI entry point failed"
        return 1
    fi
}

# 5. Git status and version consistency
check_git_status() {
    if [ "$RELEASE_MODE" = true ]; then
        print_info "Checking git status for release..."

        if [ -n "$(git status --porcelain)" ]; then
            print_status 1 "Uncommitted changes found - commit before release"
            return 1
        else
            print_status 0 "Working directory is clean"
        fi

        # Check if we're on main branch
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        if [ "$CURRENT_BRANCH" = "main" ]; then
            print_status 0 "On main branch"
        else
            print_status 1 "Not on main branch - switch to main for release"
            return 1
        fi
    fi
}

# 6. Version consistency check
check_version_consistency() {
    print_info "Checking version consistency..."

    # Get version from pyproject.toml
    if command -v poetry &> /dev/null; then
        POETRY_VERSION=$(poetry version -s)
    else
        POETRY_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    fi

    # Get version from __init__.py
    INIT_VERSION=$(grep '__version__ = ' src/vpsweb/__init__.py | sed 's/__version__ = "\(.*\)"/\1/')

    # Get version from __main__.py
    MAIN_VERSION=$(grep 'version_option(version=' src/vpsweb/__main__.py | sed 's/.*version="\([^"]*\)".*/\1/')

    print_info "Versions found:"
    print_info "  pyproject.toml: $POETRY_VERSION"
    print_info "  __init__.py: $INIT_VERSION"
    print_info "  __main__.py: $MAIN_VERSION"

    if [ "$POETRY_VERSION" = "$INIT_VERSION" ] && [ "$INIT_VERSION" = "$MAIN_VERSION" ]; then
        print_status 0 "Version consistency check passed"
    else
        print_status 1 "Version inconsistency detected"
        return 1
    fi
}

# 7. Configuration validation
check_configuration() {
    print_info "Checking configuration files..."

    # Check if config directory exists
    if [ -d "config" ]; then
        # Validate YAML syntax
        if command -v python3 &> /dev/null; then
            if [ -f "config/main.yml" ]; then
                if python3 -c "import yaml; yaml.safe_load(open('config/main.yml', 'r'))" 2>/dev/null; then
                    print_status 0 "main.yml syntax is valid"
                else
                    print_status 1 "main.yml has syntax errors"
                    return 1
                fi
            else
                print_warning "config/main.yml not found"
            fi

            if [ -f "config/models.yml" ]; then
                if python3 -c "import yaml; yaml.safe_load(open('config/models.yml', 'r'))" 2>/dev/null; then
                    print_status 0 "models.yml syntax is valid"
                else
                    print_status 1 "models.yml has syntax errors"
                    return 1
                fi
            else
                print_warning "config/models.yml not found"
            fi
        else
            print_warning "Python3 not available for YAML validation"
        fi
    else
        print_status 0 "Config directory not found (this is expected if using external config)"
    fi
}

# 8. Run tests if requested
run_tests() {
    if [ "$LINT_ONLY" = true ]; then
        return 0
    fi

    print_info "Running tests..."

    if command -v pytest &> /dev/null; then
        if pytest tests/ -v --tb=short; then
            print_status 0 "All tests passed"
        else
            print_status 1 "Some tests failed"
            return 1
        fi
    else
        print_warning "Pytest not found - run 'poetry add --group dev pytest'"
        return 1
    fi
}

# 9. Release-specific checks
run_release_checks() {
    if [ "$RELEASE_MODE" != true ]; then
        return 0
    fi

    print_info "Running release-specific checks..."

    # Check CHANGELOG is updated
    if [ -f "CHANGELOG.md" ]; then
        if grep -q "## \[Unreleased\]" CHANGELOG.md; then
            print_warning "CHANGELOG.md has [Unreleased] section - update version number"
        else
            print_status 0 "CHANGELOG.md looks good"
        fi
    else
        print_warning "CHANGELOG.md not found"
    fi

    # Check if all scripts are executable
    for script in save-version.sh push-version.sh dev-check.sh; do
        if [ -f "$script" ]; then
            if [ -x "$script" ]; then
                print_status 0 "$script is executable"
            else
                print_warning "$script is not executable - run chmod +x $script"
            fi
        fi
    done
}

# Main execution
main() {
    FAILED_CHECKS=0

    # Run checks
    check_project_structure || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_python_env || FAILED_CHECKS=$((FAILED_CHECKS + 1))

    # Skip git checks for non-release modes if not requested
    if [ "$RELEASE_MODE" = true ] || [ "$LINT_ONLY" = false ]; then
        check_git_status || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi

    check_version_consistency || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_configuration || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    check_imports || FAILED_CHECKS=$((FAILED_CHECKS + 1))

    run_linting || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    run_tests || FAILED_CHECKS=$((FAILED_CHECKS + 1))
    run_release_checks || FAILED_CHECKS=$((FAILED_CHECKS + 1))

    # Summary
    echo ""
    echo "📊 Summary"
    echo "=========="

    if [ $FAILED_CHECKS -eq 0 ]; then
        print_status 0 "All checks passed! 🎉"

        if [ "$RELEASE_MODE" = true ]; then
            echo ""
            print_info "Ready for release! You can now run:"
            print_info "  ./push-version.sh \"<version>\" \"<release notes>\""
        fi

        exit 0
    else
        print_status 1 "$FAILED_CHECKS check(s) failed"
        echo ""

        if [ "$AUTO_FIX" = false ]; then
            print_info "Try running with --fix to auto-fix some issues"
        fi

        exit 1
    fi
}

# Run main function
main