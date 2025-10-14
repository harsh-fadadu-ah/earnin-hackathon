#!/bin/bash

# Reddit EarnIn Monitor Startup Script

echo "🚀 Starting Reddit EarnIn Monitor..."
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed or not in PATH"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import praw" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ PRAW (Python Reddit API Wrapper) is not installed"
    echo "Installing PRAW..."
    pip3 install praw
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the monitor
echo "🔄 Starting continuous monitoring..."
echo "Press Ctrl+C to stop the monitor"
echo "=================================="

python3 reddit_earnin_monitor.py

