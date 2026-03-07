#!/bin/bash
# StackSense Development Dashboard Runner
# This script runs the dashboard in development mode with a test account

echo "🚀 Starting StackSense Dashboard in DEV MODE..."
echo ""
echo "📋 Test Account:"
echo "   Email: test@stacksense.dev"
echo "   Name: Test User"
echo ""
echo "🌐 Dashboard will be available at: http://127.0.0.1:5000"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
fi

# Set development mode and encryption key
export STACKSENSE_DEV_MODE=true
export STACKSENSE_ENCRYPTION_KEY=dev-test-key-change-this-in-production-32chars

# Run the dashboard
python -m stacksense.dashboard
