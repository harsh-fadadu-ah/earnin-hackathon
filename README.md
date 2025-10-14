# Feedback Management MCP Server

A comprehensive Model Context Protocol (MCP) server for collecting, processing, and managing feedback from multiple sources including App Store, Google Play, Reddit, Twitter, and other channels.

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10 or higher** (Python 3.11+ recommended)
- **Homebrew** (for macOS) or package manager for your OS
- **Slack workspace** with admin access

### 1. Install Python 3.11

```bash
# On macOS with Homebrew
brew install python@3.11

# Verify installation
python3.11 --version
# Should output: Python 3.11.x
```

### 2. Clone and Setup

```bash
# Navigate to your project directory
cd /Users/nitinnayan/hackathon

# Install dependencies
python3.11 -m pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Create .env file from template
cp env.local .env

# Edit .env file with your Slack bot token
nano .env
```

**Required configuration in .env:**
```env
SLACK_BOT_TOKEN=xoxb-your-actual-slack-bot-token-here
SLACK_REVIEW_CHANNEL=app-review
```

### 4. Test the Setup

```bash
# Run comprehensive tests
python3.11 test_server.py
```

**Expected output:**
```
🎯 Summary: 5/5 tests passed
🎉 All tests passed! Server is ready to use.
```

### 5. Run the Server

```bash
# Start the MCP server
python3.11 feedback_mcp_server.py
```

## 📋 Detailed Setup Instructions

### Slack Bot Setup

1. **Create a Slack App:**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name: "Feedback Management Bot"
   - Select your workspace

2. **Configure Bot Permissions:**
   - Go to "OAuth & Permissions"
   - Add these Bot Token Scopes:
     - `channels:history` - Read messages from public channels
     - `groups:history` - Read messages from private channels
     - `channels:read` - View basic information about public channels
     - `groups:read` - View basic information about private channels

3. **Install the App:**
   - Click "Install to Workspace"
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

4. **Create the app-review Channel:**
   - Create a channel named `app-review` (or use existing)
   - Invite your bot to the channel
   - Start posting app reviews in this format:
     ```
     App Store: 5 stars - Great app, love the new features!
     Play Store: 2 stars - App crashes sometimes, needs fixing.
     ```

### Environment Configuration

Create a `.env` file with the following content:

```env
# Database Configuration
DATABASE_PATH=feedback.db

# Slack Integration (Required)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_REVIEW_CHANNEL=app-review

# Processing Configuration
BATCH_SIZE=10
CONCURRENT_WORKERS=3
RETRY_ATTEMPTS=3

# Security Settings
PII_DETECTION_ENABLED=true
PII_REMOVAL_ENABLED=true

# Development Settings
DEBUG_MODE=false
MOCK_APIS=true  # Set to false for production with real APIs
```

## 🛠️ Available Tools

### Data Collection Tools

#### `fetch_slack_reviews`
Fetch all app reviews from your Slack channel.

```python
# Fetch all reviews from default channel
await fetch_slack_reviews({"limit": 50})

# Fetch from specific channel
await fetch_slack_reviews({
    "channel_name": "ios-reviews",
    "limit": 25
})
```

#### `fetch_appstore_reviews`
Fetch only App Store reviews from Slack.

```python
await fetch_appstore_reviews({
    "channel_name": "app-review",
    "limit": 30
})
```

#### `fetch_playstore_reviews`
Fetch only Play Store reviews from Slack.

```python
await fetch_playstore_reviews({
    "channel_name": "app-review", 
    "limit": 30
})
```

### Processing Tools

#### `classify_feedback`
Classify feedback into categories, sentiment, and severity.

```python
await classify_feedback({"feedback_id": "feedback_123"})
```

#### `score_business_impact`
Calculate business impact score for feedback.

```python
await score_business_impact({"feedback_id": "feedback_123"})
```

#### `process_feedback_queue`
Process all unprocessed feedback in batch.

```python
await process_feedback_queue({"batch_size": 10})
```

### Response Tools

#### `generate_reply`
Generate contextual replies for feedback.

```python
await generate_reply({
    "feedback_id": "feedback_123",
    "tone": "professional"
})
```

#### `post_reply`
Post replies to original platforms.

```python
await post_reply({
    "feedback_id": "feedback_123",
    "reply_content": "Thank you for your feedback...",
    "platform": "slack"
})
```

### Analytics Tools

#### `get_metrics`
Get feedback metrics and dashboard data.

```python
await get_metrics({
    "timeframe": "week",
    "source": "app_store"
})
```

### Automatic Processing Tools

#### `check_new_reviews`
Check for new reviews and automatically process them.

```python
# Check and automatically process new reviews
await check_new_reviews({
    "channel_name": "app-review",
    "auto_process": true
})

# Just check for new reviews without processing
await check_new_reviews({
    "channel_name": "app-review", 
    "auto_process": false
})
```

## 🔄 Automatic Processing

The server now includes **automatic processing** that triggers every time new reviews are detected:

### How It Works

1. **Background Monitoring**: The server runs a background task that checks for new reviews every 60 seconds (configurable)
2. **Automatic Detection**: When new reviews are posted to your Slack channel, they are automatically detected
3. **Instant Processing**: New reviews are immediately:
   - Normalized and cleaned
   - Classified by category, sentiment, and severity
   - Scored for business impact
   - Saved to the database
   - Marked as processed

### Configuration

Add these settings to your `.env` file:

```env
# Automatic Processing Configuration
AUTO_PROCESS_REVIEWS=true  # Enable automatic processing
REVIEW_CHECK_INTERVAL=60   # Check every 60 seconds
```

### Manual Trigger

You can also manually trigger processing:

```python
# Check and process new reviews immediately
await check_new_reviews({
    "channel_name": "app-review",
    "auto_process": true
})
```

### Real-time Benefits

- ✅ **Instant Processing**: Reviews are processed as soon as they're posted
- ✅ **No Manual Intervention**: Fully automated workflow
- ✅ **Configurable Timing**: Adjust check interval as needed
- ✅ **Background Operation**: Runs continuously without blocking other operations

## 📊 Workflow Example

Here's a complete workflow for processing feedback:

```python
# 1. Fetch reviews from Slack
await fetch_slack_reviews({"limit": 50})

# 2. Process the queue
await process_feedback_queue({"batch_size": 10})

# 3. Get metrics
await get_metrics({"timeframe": "week"})

# 4. Generate replies for high-impact feedback
await generate_reply({
    "feedback_id": "high_impact_feedback_id",
    "tone": "apologetic"
})

# 5. Post replies
await post_reply({
    "feedback_id": "high_impact_feedback_id",
    "reply_content": "We apologize for the issue...",
    "platform": "slack"
})
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Python Version Error
```
ERROR: Could not find a version that satisfies the requirement mcp>=1.0.0
```
**Solution:** Install Python 3.11+
```bash
brew install python@3.11
python3.11 -m pip install -r requirements.txt
```

#### 2. Slack Connection Error
```
WARNING: Slack client not available, returning mock data
```
**Solution:** Check your Slack bot token in `.env` file
```bash
# Verify token format
echo $SLACK_BOT_TOKEN
# Should start with: xoxb-
```

#### 3. Channel Not Found
```
ERROR: Channel 'app-review' not found
```
**Solution:** 
- Create the channel in Slack
- Invite your bot to the channel
- Check channel name in `.env` file

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'mcp'
```
**Solution:** Reinstall dependencies
```bash
python3.11 -m pip install -r requirements.txt
```

### Testing Your Setup

Run the comprehensive test suite:

```bash
python3.11 test_server.py
```

**All tests should pass:**
```
🎯 Summary: 5/5 tests passed
🎉 All tests passed! Server is ready to use.
```

### Verifying Slack Integration

Test Slack connectivity:

```bash
python3.11 -c "
from feedback_mcp_server import SlackReviewFetcher
import os
fetcher = SlackReviewFetcher()
print('Slack client available:', fetcher.client is not None)
"
```

## 📁 Project Structure

```
hackathon/
├── feedback_mcp_server.py    # Main MCP server
├── test_server.py           # Test suite
├── requirements.txt         # Python dependencies
├── setup.py                # Setup script
├── create_env.py           # Environment setup
├── .env                    # Environment variables (create this)
├── env.local              # Environment template
├── env.example            # Environment example
├── mcp_server_config.json # MCP configuration
├── README.md              # This file
├── feedback.db            # SQLite database (auto-created)
└── __pycache__/          # Python cache
```

## 🚀 Production Deployment

### 1. Update Environment Variables

```env
# Production settings
DEBUG_MODE=false
MOCK_APIS=false
PII_DETECTION_ENABLED=true
PII_REMOVAL_ENABLED=true
```

### 2. Configure MCP Client

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "feedback-management": {
      "command": "python3.11",
      "args": ["/Users/nitinnayan/hackathon/feedback_mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/nitinnayan/hackathon"
      }
    }
  }
}
```

### 3. Run as Service

```bash
# Using systemd (Linux)
sudo systemctl enable feedback-mcp-server
sudo systemctl start feedback-mcp-server

# Using launchd (macOS)
# Create plist file and load with launchctl
```

## 📈 Monitoring

### Health Checks

```bash
# Check server status
python3.11 -c "
import feedback_mcp_server
print('✅ Server imports successfully')
"

# Check database
python3.11 -c "
from feedback_mcp_server import FeedbackDatabase
db = FeedbackDatabase()
print('✅ Database connection successful')
"
```

### Logs

Server logs are written to:
- Console output (when running directly)
- `feedback_mcp_server.log` (if configured)

## 🤝 Support

### Getting Help

1. **Check the logs** for error messages
2. **Run the test suite** to identify issues
3. **Verify environment variables** are set correctly
4. **Check Slack bot permissions** and channel access

### Common Commands

```bash
# Test everything
python3.11 test_server.py

# Check Python version
python3.11 --version

# Verify dependencies
python3.11 -c "import mcp, slack_sdk; print('✅ Dependencies OK')"

# Check environment
python3.11 -c "import os; print('Slack token set:', bool(os.getenv('SLACK_BOT_TOKEN')))"
```

## 📝 License

MIT License - see LICENSE file for details.

---

**🎉 You're all set! The Feedback Management MCP Server is ready to collect, process, and manage feedback from your Slack channels and other sources.**