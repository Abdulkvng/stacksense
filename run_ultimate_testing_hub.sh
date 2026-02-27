#!/bin/bash

# StackSense Ultimate Testing Hub
# One dashboard for ALL testing

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

# Change to project directory
cd "$(dirname "$0")"

# Install pytest-json-report if not installed
pip install -q pytest-json-report 2>/dev/null

# Start unified testing hub
python3 tests/unified_testing_hub.py
