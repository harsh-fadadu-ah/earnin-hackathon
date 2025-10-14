# Slack Reply System for all-feedforward Channel

This system automatically replies to messages in the "all-feedforward" Slack channel (ID: C09KQHTCGFR) based on sentiment analysis. It replies in the same message thread with appropriate responses for positive/neutral and negative feedback.

## 🚀 Features

- **Automatic Sentiment Analysis**: Analyzes messages using keyword-based sentiment detection
- **Thread-based Replies**: Replies in the same message thread to maintain conversation context
- **JIRA Ticket Integration**: Generates JIRA ticket numbers for negative feedback
- **Configurable Responses**: Customizable reply templates for different sentiment types
- **Rate Limiting**: Built-in delays to avoid Slack API rate limits
- **Continuous Monitoring**: Can run continuously to monitor for new messages
- **Integration with Existing Workflow**: Works seamlessly with the current message processing system

## 📋 Reply Templates

### Positive/Neutral Feedback
```
Thank you for your kind words! I'm glad you found our app helpful and appreciate your feedback!
```

### Negative Feedback
```
Thank you for your feedback! We're a customer-centric organization and truly appreciate you sharing your concern. We've logged it as system {JIRA_TICKET}, and our team is actively working on it. You can track your ticket's progress here: https://jira.example.com/browse/{JIRA_TICKET}.
```

## 🛠️ Installation

The system uses the existing dependencies from `requirements.txt`. Make sure you have:

1. **Slack Bot Token**: Set `SLACK_BOT_TOKEN` in your `config/env.local` file
2. **Channel Access**: The bot must have access to the "all-feedforward" channel
3. **Python Environment**: Running in the `mcp-env` virtual environment

## 📖 Usage

### Quick Start

```bash
# Test the connection
python run_reply_system.py --test

# Process recent messages once
python run_reply_system.py --mode once --limit 10

# Run continuous monitoring
python run_reply_system.py --mode continuous --interval 60
```

### Enhanced Processor (with existing workflow)

```bash
# Test the enhanced processor
python run_enhanced_processor.py --test

# Process recent messages with replies
python run_enhanced_processor.py --mode once --limit 10

# Run continuous processing with replies
python run_enhanced_processor.py --mode continuous --interval 60 --batch-size 10

# Disable replies (only process and post to team channels)
python run_enhanced_processor.py --mode once --disable-replies
```

### Testing

```bash
# Run comprehensive tests
python test_reply_system.py
```

## 🔧 Configuration

### Environment Variables

The system uses the following environment variables from `config/env.local`:

- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_REVIEW_CHANNEL`: Channel name (default: "all-feedforward")
- `SLACK_CHANNEL_ID`: Channel ID (default: "C09KQHTCGFR")

### Sentiment Analysis

The system uses keyword-based sentiment analysis with the following categories:

**Positive Keywords**: love, great, awesome, amazing, perfect, excellent, good, thanks, thank you, wonderful, fantastic, brilliant, outstanding, helpful, useful, satisfied, happy, pleased, impressed, recommend, best, top, exceeded, surpassed, delighted

**Negative Keywords**: hate, terrible, awful, horrible, bad, worst, disappointed, frustrated, angry, annoyed, upset, disgusted, displeased, broken, bug, error, issue, problem, complaint, concern, unhappy, unsatisfied, poor, worst, fail, failed, failure, slow, crashed, freeze, glitch, malfunction, defective

**Issue Keywords**: issue, problem, bug, error, not working, broken, help, support, question, how to, unable to, cannot, can't, trouble, difficulty, confused, unclear, need help

### JIRA Ticket Generation

- **Format**: JIRA-XXXXXX (e.g., JIRA-613401)
- **Range**: 613401-614400
- **Consistency**: Same message always gets the same ticket number
- **URL**: https://jira.example.com/browse/{JIRA_TICKET}

## 📊 How It Works

1. **Message Detection**: Monitors the "all-feedforward" channel for new messages
2. **Sentiment Analysis**: Analyzes message content using keyword matching
3. **Reply Generation**: Generates appropriate reply based on sentiment
4. **JIRA Ticket**: Creates JIRA ticket number for negative feedback
5. **Thread Reply**: Posts reply in the same message thread
6. **Tracking**: Marks messages as processed to avoid duplicate replies

## 🔄 Integration with Existing Workflow

The reply system integrates seamlessly with the existing message processing workflow:

1. **Message Processing**: Messages are still classified and posted to appropriate team channels
2. **Reply Addition**: For messages from "all-feedforward" channel, replies are also posted
3. **JIRA Consistency**: Uses the same JIRA ticket number for both team channel posting and replies
4. **Database Integration**: Works with the existing unified database system

## 📝 Files Created

- `slack_reply_system.py`: Core reply system implementation
- `run_reply_system.py`: Standalone script to run the reply system
- `enhanced_message_processor.py`: Enhanced processor with reply integration
- `run_enhanced_processor.py`: Script to run the enhanced processor
- `test_reply_system.py`: Comprehensive test suite
- `README_reply_system.md`: This documentation

## 🚨 Important Notes

1. **No Workflow Changes**: The existing workflow remains unchanged
2. **Virtual Environment**: Run in the `mcp-env` virtual environment
3. **Rate Limiting**: Built-in delays prevent Slack API rate limiting
4. **Duplicate Prevention**: Tracks processed messages to avoid duplicate replies
5. **Error Handling**: Comprehensive error handling and logging
6. **JIRA URL**: Update the JIRA URL in the negative reply template as needed

## 🔍 Monitoring and Logs

- **Log Files**: 
  - `slack_reply_system.log`: Reply system logs
  - `enhanced_processor.log`: Enhanced processor logs
- **Console Output**: Real-time status updates
- **Error Handling**: Detailed error messages and recovery

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python test_reply_system.py
```

This will test:
- Sentiment analysis with various message types
- JIRA ticket generation
- Reply template formatting
- Slack connection validation

## 🚀 Production Deployment

For production use:

1. **Test First**: Always run `--test` mode first
2. **Start Small**: Begin with `--limit 10` to test with a small batch
3. **Monitor Logs**: Watch log files for any issues
4. **Continuous Mode**: Use continuous mode for ongoing monitoring
5. **Error Handling**: The system includes comprehensive error handling and recovery

## 📞 Support

The system is designed to be self-contained and includes:
- Comprehensive logging
- Error recovery
- Rate limiting
- Duplicate prevention
- Integration with existing workflow

All functionality is preserved from the original system while adding the new reply capability.
