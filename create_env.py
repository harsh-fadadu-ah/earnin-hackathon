#!/usr/bin/env python3
"""
Script to create .env file for Feedback Management MCP Server
"""

import os
import shutil

def create_env_file():
    """Create .env file from template"""
    
    # Check if .env already exists
    if os.path.exists('.env'):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cancelled. .env file not created.")
            return False
    
    # Copy from template
    if os.path.exists('env.local'):
        shutil.copy('env.local', '.env')
        print("✅ Created .env file from template")
    elif os.path.exists('env.example'):
        shutil.copy('env.example', '.env')
        print("✅ Created .env file from env.example")
    else:
        # Create basic .env file
        env_content = """# Database Configuration
DATABASE_PATH=feedback.db

# Slack Integration (Required for app reviews)
# Get this from your Slack app settings: https://api.slack.com/apps
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here

# Processing Configuration
BATCH_SIZE=10
CONCURRENT_WORKERS=3
RETRY_ATTEMPTS=3

# Security Settings
PII_DETECTION_ENABLED=true
PII_REMOVAL_ENABLED=true

# Development Settings
DEBUG_MODE=false
MOCK_APIS=true
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created basic .env file")
    
    print("\n📝 Next steps:")
    print("1. Edit .env file and add your Slack bot token")
    print("2. Get your bot token from: https://api.slack.com/apps")
    print("3. Replace 'xoxb-your-slack-bot-token-here' with your actual token")
    print("4. Run: python test_server.py to test the setup")
    
    return True

def main():
    """Main function"""
    print("🔧 Creating .env file for Feedback Management MCP Server")
    print("=" * 60)
    
    if create_env_file():
        print("\n🎉 Setup complete!")
    else:
        print("\n❌ Setup failed!")

if __name__ == "__main__":
    main()
