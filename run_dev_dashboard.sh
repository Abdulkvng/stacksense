#!/bin/bash
# StackSense Development Dashboard Runner
# This script runs the dashboard in development mode with a test account

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
PYTHON_BIN="$("$PROJECT_ROOT/scripts/resolve_python.sh")"

echo "🚀 Starting StackSense Dashboard in DEV MODE..."
echo ""
echo "📋 Test Account:"
echo "   Email: test@stacksense.dev"
echo "   Name: Test User"
echo ""
echo "🌐 Dashboard will be available at: http://127.0.0.1:5000"
echo ""

cd "$PROJECT_ROOT"

# Set development mode and encryption key
export STACKSENSE_DEV_MODE=true
export STACKSENSE_ENCRYPTION_KEY=dev-test-key-change-this-in-production-32chars

# Run the dashboard
"$PYTHON_BIN" -m stacksense.dashboard
