#!/bin/bash

# StackSense Ultimate Testing Hub
# One dashboard for ALL testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$("$PROJECT_ROOT/scripts/resolve_python.sh")"

echo "================================================================================"
echo "🧪 StackSense Ultimate Testing Hub"
echo "================================================================================"
echo ""
echo "✨ Starting unified testing platform..."
echo ""
echo "Features:"
echo "  • Gateway Performance Tests"
echo "  • Unit Tests (pytest)"  
echo "  • Performance Benchmarks"
echo "  • Live Monitoring"
echo "  • Real-time Metrics"
echo "  • Visual Dashboards"
echo ""
echo "🌐 Dashboard will be available at: http://localhost:9000"
echo ""
echo "⚠️  Press Ctrl+C to stop"
echo "================================================================================"
echo ""

cd "$PROJECT_ROOT"

# Install pytest-json-report if not installed
"$PYTHON_BIN" -m pip install -q pytest-json-report 2>/dev/null

# Start unified testing hub
"$PYTHON_BIN" tests/unified_testing_hub.py
