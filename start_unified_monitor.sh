#!/bin/bash

# Unified MCP Monitor Startup Script

echo "🚀 Starting Unified MCP Monitor..."
echo "=================================="

# Check if Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 is not installed or not in PATH"
    echo "Please install Python 3.11 or update the script to use available Python version"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3.11 -c "import mcp, slack_sdk, praw, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Required packages are not installed"
    echo "Installing dependencies..."
    python3.11 -m pip install mcp slack-sdk praw python-dotenv
fi

# Check if environment file exists
if [ ! -f "env.local" ]; then
    echo "⚠️  Warning: env.local file not found"
    echo "Creating from env.example..."
    if [ -f "env.example" ]; then
        cp env.example env.local
        echo "Please update env.local with your actual credentials"
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Load environment variables
if [ -f "env.local" ]; then
    echo "📋 Loading environment variables from env.local..."
    export $(cat env.local | grep -v '^#' | xargs)
fi

# Start the unified monitor
echo "🔄 Starting unified monitoring system..."
echo "This will monitor all MCP servers and check for new posts/messages every minute"
echo "Press Ctrl+C to stop the monitor"
echo "=================================="

python3.11 unified_mcp_monitor.py
