#!/usr/bin/env python3
"""
Setup script for Feedback Management MCP Server
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    try:
        # Try Python 3.11 first, fallback to system Python
        python_cmd = "python3.11" if subprocess.run(["which", "python3.11"], capture_output=True).returncode == 0 else sys.executable
        subprocess.check_call([python_cmd, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False
    return True

def setup_database():
    """Initialize the database"""
    print("Setting up database...")
    try:
        from feedback_mcp_server import FeedbackDatabase
        db = FeedbackDatabase()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    if not env_file.exists():
        print("Creating .env file...")
        env_content = """# Database
DATABASE_PATH=feedback.db

# API Keys (optional, for real integrations)
APP_STORE_API_KEY=your_app_store_api_key
GOOGLE_PLAY_API_KEY=your_google_play_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Platform Integrations
SLACK_BOT_TOKEN=your_slack_bot_token
JIRA_API_TOKEN=your_jira_api_token
ASANA_ACCESS_TOKEN=your_asana_access_token

# Processing Configuration
BATCH_SIZE=10
CONCURRENT_WORKERS=3
RETRY_ATTEMPTS=3
"""
        with open(env_file, "w") as f:
            f.write(env_content)
        print("✅ .env file created")
    else:
        print("✅ .env file already exists")

def test_server():
    """Test if the server can start"""
    print("Testing server startup...")
    try:
        # Import the server to check for syntax errors
        import feedback_mcp_server
        print("✅ Server imports successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing server: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Feedback Management MCP Server")
    print("=" * 50)
    
    success = True
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Create .env file
    create_env_file()
    
    # Setup database
    if not setup_database():
        success = False
    
    # Test server
    if not test_server():
        success = False
    
    print("=" * 50)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your API keys")
        print("2. Configure your MCP client with mcp_server_config.json")
        print("3. Run: python feedback_mcp_server.py")
    else:
        print("❌ Setup completed with errors. Please check the messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
