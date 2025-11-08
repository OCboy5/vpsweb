#!/bin/bash
# VPSWeb Development Server Start Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"

echo "Starting VPSWeb development server..."
echo "Access the web interface at: http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo

poetry run uvicorn vpsweb.webui.main:create_app \
    --factory \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --log-level debug
