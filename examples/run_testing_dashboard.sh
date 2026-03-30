#!/bin/bash

# StackSense Gateway Testing Dashboard
# Quick start script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$("$PROJECT_ROOT/scripts/resolve_python.sh")"

echo "========================================================================"
echo "🧪 StackSense Live Testing Dashboard"
echo "========================================================================"
echo ""
echo "Starting server..."
echo "Dashboard will be available at: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================================================"
echo ""

cd "$PROJECT_ROOT"

# Start dashboard server
"$PYTHON_BIN" tests/dashboard_server.py
