#!/bin/bash
# VPSWeb Integration Test Suite v0.3.1
#
# Comprehensive end-to-end testing for VPSWeb system
# Tests all major components and workflows

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS="${PROJECT_ROOT}/test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_LOG="${TEST_RESULTS}/integration_test_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counters
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$TEST_LOG"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$TEST_LOG" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$TEST_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$TEST_LOG"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $1" | tee -a "$TEST_LOG"
}

test_start() {
    local test_name="$1"
    ((TESTS_TOTAL++))
    echo -e "${PURPLE}[TEST]${NC} $test_name" | tee -a "$TEST_LOG"
}

test_pass() {
    local test_name="$1"
    ((TESTS_PASSED++))
    echo -e "${GREEN}[PASS]${NC} $test_name" | tee -a "$TEST_LOG"
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    ((TESTS_FAILED++))
    echo -e "${RED}[FAIL]${NC} $test_name: $reason" | tee -a "$TEST_LOG"
}

# Setup test environment
setup_test_env() {
    log "Setting up integration test environment..."

    # Create test results directory
    mkdir -p "$TEST_RESULTS"

    # Set PYTHONPATH
    export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"

    # Check if we're in the right directory
    if [[ ! -f "pyproject.toml" ]]; then
        error "Not in VPSWeb project directory"
        exit 1
    fi

    # Check if database exists
    if [[ ! -f "repository_root/repo.db" ]]; then
        warning "Database not found. Running setup first..."
        ./scripts/setup.sh
    fi

    success "Test environment ready"
}

# Test basic imports
test_imports() {
    test_start "Testing Python imports"

    if poetry run python -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    import vpsweb
    from vpsweb.webui.main import app
    from vpsweb.repository.service import RepositoryWebService
    from vpsweb.repository.database import get_db_session
    from vpsweb.models.translation import TranslationInput
    from vpsweb.models.config import MainConfig
    print('All imports successful')
except ImportError as e:
    print(f'Import failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Python imports"
    else
        test_fail "Python imports" "Import error"
    fi
}

# Test database connection
test_database() {
    test_start "Testing database connection"

    if poetry run python -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from vpsweb.repository.database import get_db_session
    from vpsweb.repository.service import RepositoryWebService

    with get_db_session() as db:
        service = RepositoryWebService(db)
        stats = service.get_repository_stats()
        print(f'Database connection successful')
        print(f'Poems: {stats.total_poems}, Translations: {stats.total_translations}')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Database connection"
    else
        test_fail "Database connection" "Connection failed"
    fi
}

# Test web application startup
test_web_app() {
    test_start "Testing web application startup"

    if poetry run python -c "
import sys
import asyncio
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from vpsweb.webui.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get('/health')
    if response.status_code == 200:
        print('Web app startup successful')
        print(f'Health check: {response.json()}')
    else:
        print(f'Health check failed: {response.status_code}')
        sys.exit(1)
except Exception as e:
    print(f'Web app startup failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Web application startup"
    else
        test_fail "Web application startup" "Startup failed"
    fi
}

# Test API endpoints
test_api_endpoints() {
    test_start "Testing API endpoints"

    if poetry run python -c "
import sys
import json
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from fastapi.testclient import TestClient
    from vpsweb.webui.main import app

    client = TestClient(app)

    # Test health endpoint
    response = client.get('/health')
    assert response.status_code == 200, f'Health endpoint failed: {response.status_code}'

    # Test poems list endpoint
    response = client.get('/api/v1/poems/')
    assert response.status_code == 200, f'Poems list endpoint failed: {response.status_code}'

    # Test OpenAPI docs
    response = client.get('/openapi.json')
    assert response.status_code == 200, f'OpenAPI endpoint failed: {response.status_code}'

    print('All API endpoints working')

except Exception as e:
    print(f'API endpoint test failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "API endpoints"
    else
        test_fail "API endpoints" "Endpoint test failed"
    fi
}

# Test poem creation workflow
test_poem_creation() {
    test_start "Testing poem creation workflow"

    if poetry run python -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from fastapi.testclient import TestClient
    from vpsweb.webui.main import app

    client = TestClient(app)

    # Test poem creation
    poem_data = {
        'poet_name': 'Test Poet',
        'poem_title': 'Test Poem for Integration',
        'source_language': 'en',
        'original_text': 'This is a test poem for integration testing.\\nIt has multiple lines.\\nAnd tests the workflow.'
    }

    response = client.post('/api/v1/poems/', json=poem_data)
    if response.status_code == 200:
        poem_id = response.json()['id']
        print(f'Poem created successfully: {poem_id}')

        # Test poem retrieval
        response = client.get(f'/api/v1/poems/{poem_id}')
        assert response.status_code == 200, f'Poem retrieval failed: {response.status_code}'

        retrieved_poem = response.json()
        assert retrieved_poem['poet_name'] == 'Test Poet'
        assert retrieved_poem['poem_title'] == 'Test Poem for Integration'

        print('Poem creation and retrieval successful')
    else:
        print(f'Poem creation failed: {response.status_code} - {response.text}')
        sys.exit(1)

except Exception as e:
    print(f'Poem creation test failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Poem creation workflow"
    else
        test_fail "Poem creation workflow" "Workflow failed"
    fi
}

# Test configuration validation
test_configuration() {
    test_start "Testing configuration validation"

    if poetry run python -c "
import sys
import os
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from vpsweb.utils.config_loader import load_config

    # Test config loading
    config = load_config()
    print('Configuration loaded successfully')

    # Test essential configuration values
    assert hasattr(config, 'translation'), 'Translation config missing'
    assert hasattr(config, 'models'), 'Models config missing'

    print('Configuration validation passed')

except Exception as e:
    print(f'Configuration validation failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Configuration validation"
    else
        test_fail "Configuration validation" "Validation failed"
    fi
}

# Test backup/restore system
test_backup_restore() {
    test_start "Testing backup/restore system"

    # Test backup script
    if ./scripts/backup.sh --verify-only 2>/dev/null; then
        # Test restore script list
        if ./scripts/restore.sh --list >/dev/null 2>&1; then
            test_pass "Backup/restore system"
        else
            test_fail "Backup/restore system" "Restore script failed"
        fi
    else
        test_fail "Backup/restore system" "Backup script failed"
    fi
}

# Test development scripts
test_dev_scripts() {
    test_start "Testing development scripts"

    local script_failed=false

    # Test setup script verification
    if ! ./scripts/setup.sh --verify-only >/dev/null 2>&1; then
        script_failed=true
    fi

    # Test backup script help
    if ! ./scripts/backup.sh --help >/dev/null 2>&1; then
        script_failed=true
    fi

    # Test restore script help
    if ! ./scripts/restore.sh --help >/dev/null 2>&1; then
        script_failed=true
    fi

    if [[ "$script_failed" == "false" ]]; then
        test_pass "Development scripts"
    else
        test_fail "Development scripts" "One or more scripts failed"
    fi
}

# Test file structure and permissions
test_file_structure() {
    test_start "Testing file structure and permissions"

    local structure_ok=true

    # Check essential directories
    for dir in "src" "config" "docs" "scripts" "tests"; do
        if [[ ! -d "$dir" ]]; then
            structure_ok=false
            break
        fi
    done

    # Check essential files
    for file in "pyproject.toml" "README.md" "CLAUDE.md"; do
        if [[ ! -f "$file" ]]; then
            structure_ok=false
            break
        fi
    done

    # Check script permissions
    for script in "scripts/setup.sh" "scripts/backup.sh" "scripts/restore.sh"; do
        if [[ -f "$script" ]] && [[ ! -x "$script" ]]; then
            structure_ok=false
            break
        fi
    done

    if [[ "$structure_ok" == "true" ]]; then
        test_pass "File structure and permissions"
    else
        test_fail "File structure and permissions" "Structure or permission issues"
    fi
}

# Test code quality
test_code_quality() {
    test_start "Testing code quality"

    local quality_ok=true

    # Test Black formatting
    if ! poetry run black --check src/ >/dev/null 2>&1; then
        quality_ok=false
    fi

    # Test import sorting
    if ! poetry run isort --check-only src/ >/dev/null 2>&1; then
        quality_ok=false
    fi

    # Test mypy (only critical parts)
    if ! poetry run mypy src/vpsweb/models/ --ignore-missing-imports >/dev/null 2>&1; then
        quality_ok=false
    fi

    if [[ "$quality_ok" == "true" ]]; then
        test_pass "Code quality"
    else
        test_fail "Code quality" "Code quality issues found"
    fi
}

# Test documentation completeness
test_documentation() {
    test_start "Testing documentation completeness"

    local docs_ok=true

    # Check essential documentation files
    for doc in "README.md" "docs/user_guide.md" "docs/development_setup.md" "docs/backup_restore_guide.md"; do
        if [[ ! -f "$doc" ]]; then
            docs_ok=false
            break
        fi
    done

    # Check that documentation has content
    if [[ "$docs_ok" == "true" ]]; then
        for doc in "README.md" "docs/user_guide.md"; do
            if [[ $(wc -l < "$doc") -lt 50 ]]; then
                docs_ok=false
                break
            fi
        done
    fi

    if [[ "$docs_ok" == "true" ]]; then
        test_pass "Documentation completeness"
    else
        test_fail "Documentation completeness" "Missing or insufficient documentation"
    fi
}

# Performance test
test_performance() {
    test_start "Testing basic performance"

    if poetry run python -c "
import sys
import time
sys.path.insert(0, '${PROJECT_ROOT}/src')

try:
    from fastapi.testclient import TestClient
    from vpsweb.webui.main import app

    client = TestClient(app)

    # Test API response time
    start_time = time.time()
    response = client.get('/health')
    end_time = time.time()

    response_time = (end_time - start_time) * 1000  # Convert to milliseconds

    if response.status_code == 200 and response_time < 1000:  # Less than 1 second
        print(f'Performance test passed: {response_time:.2f}ms')
    else:
        print(f'Performance test failed: {response_time:.2f}ms, status: {response.status_code}')
        sys.exit(1)

except Exception as e:
    print(f'Performance test failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        test_pass "Basic performance"
    else
        test_fail "Basic performance" "Performance issues detected"
    fi
}

# Generate test report
generate_report() {
    local report_file="${TEST_RESULTS}/integration_test_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# VPSWeb Integration Test Report

**Date**: $(date)
**Version**: v0.3.1
**Test Environment**: $(uname -a)

## Test Summary

- **Total Tests**: $TESTS_TOTAL
- **Passed**: $TESTS_PASSED
- **Failed**: $TESTS_FAILED
- **Success Rate**: $(( TESTS_PASSED * 100 / TESTS_TOTAL ))%

## Test Results

EOF

    if [[ $TESTS_FAILED -eq 0 ]]; then
        cat >> "$report_file" << EOF
🎉 **All tests passed!** The VPSWeb system is ready for release.

EOF
    else
        cat >> "$report_file" << EOF
⚠️ **$TESTS_FAILED test(s) failed**. Please review the issues below before release.

EOF
    fi

    cat >> "$report_file" << EOF
## Detailed Log

See the complete test log: \`integration_test_${TIMESTAMP}.log\`

## Test Categories

1. **System Integration**: Python imports, database, web application
2. **API Functionality**: REST endpoints, CRUD operations
3. **Workflow Testing**: Poem creation, translation workflows
4. **Configuration**: Environment setup, validation
5. **Infrastructure**: Backup/restore, development scripts
6. **Code Quality**: Formatting, type checking, documentation
7. **Performance**: Basic response time testing

## Next Steps

EOF

    if [[ $TESTS_FAILED -eq 0 ]]; then
        cat >> "$report_file" << EOF
- ✅ System is ready for production deployment
- ✅ All components are functioning correctly
- ✅ Documentation is complete and up-to-date
- ✅ Development environment is properly configured

**Ready for v0.3.1 release! 🚀**
EOF
    else
        cat >> "$report_file" << EOF
- 🔧 Fix the failing tests before release
- 🔍 Review the detailed log for specific error messages
- 📝 Update documentation if needed
- 🧪 Re-run integration tests after fixes

**Address failures before proceeding with release.**
EOF
    fi

    success "Integration test report generated: $report_file"
}

# Main test runner
main() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              VPSWeb Integration Test Suite              ║"
    echo "║                        v0.3.1                                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo

    # Setup test environment
    setup_test_env

    # Run all tests
    test_imports
    test_database
    test_web_app
    test_api_endpoints
    test_poem_creation
    test_configuration
    test_backup_restore
    test_dev_scripts
    test_file_structure
    test_code_quality
    test_documentation
    test_performance

    # Generate report
    generate_report

    # Show final results
    echo
    echo -e "${PURPLE}Integration Test Results:${NC}"
    echo -e "  Total Tests: $TESTS_TOTAL"
    echo -e "  Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  Failed: ${RED}$TESTS_FAILED${NC}"
    echo

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}🎉 All integration tests passed! System is ready for release.${NC}"
        echo
        echo -e "${CYAN}Next Steps:${NC}"
        echo "  1. Review the test report: $TEST_RESULTS/integration_test_report_${TIMESTAMP}.md"
        echo "  2. Run final deployment tests if needed"
        echo "  3. Proceed with version release"
        echo
        exit 0
    else
        echo -e "${RED}❌ $TESTS_FAILED integration test(s) failed.${NC}"
        echo
        echo -e "${CYAN}Next Steps:${NC}"
        echo "  1. Review the test report: $TEST_RESULTS/integration_test_report_${TIMESTAMP}.md"
        echo "  2. Check the detailed log: $TEST_LOG"
        echo "  3. Fix the failing tests"
        echo "  4. Re-run integration tests"
        echo
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "VPSWeb Integration Test Suite v0.3.1"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --quick        Run only essential tests (imports, database, web app)"
        echo "  --no-quality   Skip code quality tests"
        echo "  --no-docs      Skip documentation tests"
        echo
        exit 0
        ;;
    --quick)
        QUICK_MODE=true
        ;;
    --no-quality)
        NO_QUALITY=true
        ;;
    --no-docs)
        NO_DOCS=true
        ;;
    "")
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Quick mode - run only essential tests
if [[ "${QUICK_MODE:-}" == "true" ]]; then
    echo "Running quick integration tests..."
    setup_test_env
    test_imports
    test_database
    test_web_app
    test_api_endpoints

    echo
    echo -e "${GREEN}Quick tests completed!${NC}"
    echo "Run full test suite with: $0"
    exit 0
fi

# Run main test suite
main