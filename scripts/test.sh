#!/bin/bash
# VPSWeb Test Runner Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"

echo "Running VPSWeb test suite..."

poetry run pytest tests/ -v --cov=src/vpsweb --cov-report=term-missing
