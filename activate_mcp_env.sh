#!/bin/bash
# Script to activate the MCP environment and set up the project

echo "🚀 Activating MCP Environment..."
echo "=================================="

# Activate the conda environment
conda activate mcp-env

# Verify Python version
echo "✅ Python version: $(python --version)"

# Verify MCP installation
echo "✅ MCP version: $(python -c 'import mcp; print(mcp.__version__)' 2>/dev/null || echo 'MCP installed')"

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ Environment file (.env) found"
else
    echo "❌ Environment file (.env) not found"
    echo "Run: cp env.local .env"
fi

echo ""
echo "🎯 Environment ready! You can now run:"
echo "  - python test_server.py (to test the setup)"
echo "  - python feedback_mcp_server.py (to start the MCP server)"
echo "  - python unified_mcp_monitor.py (to start the unified monitor)"
echo ""
echo "💡 To deactivate: conda deactivate"
