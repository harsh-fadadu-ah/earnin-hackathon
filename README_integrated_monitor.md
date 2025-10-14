# Integrated Unified MCP Monitor with Reply System

The `unified_mcp_monitor_updated.py` now includes the Slack Reply System as a fully integrated service. When you run this monitor, it automatically handles all aspects of the feedback processing workflow, including automatic replies to the all-feedforward channel.

## 🚀 Quick Start

Simply run the unified monitor and everything will work automatically:

```bash
python unified_mcp_monitor_updated.py
```

This single command will:
- ✅ Monitor and process Reddit posts about EarnIn
- ✅ Fetch and process messages from Slack channels
- ✅ Classify messages and post to appropriate team channels
- ✅ **Automatically reply to messages in all-feedforward channel based on sentiment**
- ✅ Generate JIRA tickets for negative feedback
- ✅ Provide comprehensive monitoring and logging

## 📊 Services Included

The integrated monitor now includes **5 services**:

1. **feedback-management-unified**: Manages feedback processing and database operations
2. **reddit-mcp-unified**: Monitors Reddit for EarnIn-related posts
3. **slack-integration-unified**: Fetches messages from Slack channels
4. **message-processor**: Classifies messages and posts to team channels
5. **slack-reply-system**: **NEW** - Automatically replies to all-feedforward channel messages

## 🎯 Reply System Features

When running the unified monitor, the reply system will:

- **Monitor**: Continuously check the all-feedforward channel (C09KQHTCGFR)
- **Analyze**: Perform sentiment analysis on new messages
- **Reply**: Post appropriate responses in the same message thread
- **Track**: Generate JIRA tickets for negative feedback
- **Log**: Provide detailed logging of all activities

### Reply Templates

**Positive/Neutral Messages:**
```
Thank you for your kind words! I'm glad you found our app helpful and appreciate your feedback!
```

**Negative Messages:**
```
Thank you for your feedback! We're a customer-centric organization and truly appreciate you sharing your concern. We've logged it as system JIRA-XXXXXX, and our team is actively working on it. You can track your ticket's progress here: https://jira.example.com/browse/JIRA-XXXXXX.
```

## 📈 Monitoring Output

When you run the monitor, you'll see output like this:

```
🚀 Starting Unified MCP Monitor (Updated) with Reply System...
Check interval: 60 seconds
Auto-processing: enabled
Using unified database: unified_messages.db
📝 Services: Feedback Management, Reddit MCP, Slack Integration, Message Processor, Slack Reply System

Running health checks for all MCP services (unified)...
Slack Reply System: Checking for new messages in all-feedforward channel...
Slack Reply System: ✅ Posted 1 replies to all-feedforward channel
Slack Reply System: 🎫 Generated 1 JIRA tickets for negative feedback
Status Report: 5/5 services healthy
```

## 🔧 Configuration

The reply system uses the same configuration as the existing system:

- **Environment**: Run in `mcp-env` virtual environment
- **Slack Token**: Uses `SLACK_BOT_TOKEN` from `config/env.local`
- **Channel**: Targets "all-feedforward" channel (ID: C09KQHTCGFR)
- **Database**: Uses the unified database system

## 📝 Log Files

The monitor creates comprehensive logs:

- **`unified_monitor_updated.log`**: Main monitor log with all service activities
- **`monitor_status_updated.json`**: JSON status report with service health
- **`slack_reply_system.log`**: Detailed reply system logs (if run separately)

## 🎮 Usage Examples

### Basic Usage (Recommended)
```bash
# Run the complete integrated system
python unified_mcp_monitor_updated.py
```

### Test Mode
```bash
# Test individual components
python -c "
import asyncio
from unified_mcp_monitor_updated import UnifiedMCPMonitorUpdated

async def test():
    monitor = UnifiedMCPMonitorUpdated()
    result = await monitor.check_slack_reply_system()
    print(f'Reply system test: {result}')

asyncio.run(test())
"
```

## 🔍 Status Monitoring

The monitor provides real-time status updates:

- **Service Health**: Shows which services are running/error
- **Processing Counts**: Tracks how many messages/replies processed
- **Error Tracking**: Monitors and reports any issues
- **Database Stats**: Shows unified database statistics

## 🚨 Important Notes

1. **No Changes Required**: The existing workflow remains unchanged
2. **Automatic Integration**: Reply system runs automatically with the monitor
3. **Rate Limiting**: Built-in delays prevent Slack API rate limiting
4. **Error Handling**: Comprehensive error handling and recovery
5. **Duplicate Prevention**: Tracks processed messages to avoid duplicate replies

## 🎉 Benefits

By running the integrated monitor, you get:

- **Complete Automation**: Everything runs from a single command
- **Unified Monitoring**: All services monitored in one place
- **Automatic Replies**: No manual intervention needed for all-feedforward channel
- **JIRA Integration**: Automatic ticket generation for negative feedback
- **Comprehensive Logging**: Full visibility into all operations
- **Error Recovery**: Robust error handling and automatic retry

## 🔄 Workflow

The complete workflow when running the monitor:

1. **Reddit Monitoring**: Searches for EarnIn-related posts
2. **Slack Fetching**: Gets messages from Slack channels
3. **Message Processing**: Classifies and posts to team channels
4. **Reply Processing**: **NEW** - Analyzes all-feedforward messages and replies
5. **Status Reporting**: Provides comprehensive status updates
6. **Repeat**: Continues every 60 seconds (configurable)

This integrated approach ensures that all your feedback processing needs are handled automatically with a single command! 🚀
