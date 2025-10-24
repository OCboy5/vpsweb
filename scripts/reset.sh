#!/bin/bash
# VPSWeb Database Reset Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Resetting VPSWeb database..."

# Stop any running processes
pkill -f "vpsweb" || true

# Remove database file
rm -f repository_root/repo.db

# Recreate database
mkdir -p repository_root
export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"
cd src/vpsweb/repository
poetry run alembic upgrade head
cd - > /dev/null

echo "Database reset complete!"
