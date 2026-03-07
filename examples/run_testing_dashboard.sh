#!/bin/bash

# StackSense Gateway Testing Dashboard
# Quick start script

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

# Change to project directory
cd "$(dirname "$0")"

# Start dashboard server
python3 tests/dashboard_server.py
