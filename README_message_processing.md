# Message Processing and Classification System

This system automatically classifies messages from the unified database and posts them to appropriate Slack channels based on the classification results.

## 🚀 Features

- **Automatic Message Classification**: Classifies messages into Level 1 and Level 2 categories
- **Slack Integration**: Posts classified messages to appropriate Slack channels
- **JIRA Ticket Generation**: Generates unique JIRA ticket IDs for each message
- **Database Integration**: Fetches unprocessed messages from `unified_messages.db`
- **Batch Processing**: Processes multiple messages efficiently
- **Continuous Monitoring**: Can run continuously to process new messages

## 📋 Classification Categories

### Level 1 Categories
- **Product Feedback (Feature/Functionality)**
- **Customer Experience (CX) & Support**
- **Technical Issues / Bugs**
- **Trust, Security, and Transparency**
- **Onboarding and Account Setup**
- **Payments and Cash Out**
- **Notifications and Communication**
- **General Sentiment**
- **Non-relevant or Ambiguous**

### Level 2 Categories & Slack Channels
| L2 Category | Slack Channel |
|-------------|---------------|
| Cash Out | #help-cashout-experience |
| Balance Shield | #help-cashout-experience |
| EarnIn Card / Tip Jar | #help-earnin-card |
| Lightning Speed / Transfer Mechanism | #help-money-movement |
| Insights & Financial Tools | #help-analytics |
| Bank Connections | #help-edx-accountverification |
| Notifications & Reminders | #help-marketing |
| App UX / Performance | #help-performance-ux |
| Customer Support | #help-cx |
| Security / Compliance | #help-security |

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Make sure your `env.local` file contains:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   ```

3. **Verify Database**:
   Ensure `unified_messages.db` exists and contains message data.

## 📖 Usage

### Quick Start

```bash
# Process 10 messages once
python run_processor.py --mode once --count 10

# Show statistics only
python run_processor.py --stats

# Run continuously (processes new messages every 5 minutes)
python run_processor.py --mode continuous --interval 300
```

### Advanced Usage

```bash
# Process specific number of messages
python message_processor.py --batch-size 50

# Run continuously with custom interval
python message_processor.py --continuous --interval 600

# Show statistics without processing
python message_processor.py --stats-only
```

### Testing

```bash
# Run comprehensive tests
python test_message_processor.py

# Test classifier only
python -c "from message_classifier import classify_message_simple; print(classify_message_simple('My cash out is slow'))"
```

## 🔧 Components

### 1. Message Classifier (`message_classifier.py`)
- Classifies messages into categories using keyword matching
- Generates JIRA ticket IDs
- Provides confidence scores and reasoning

### 2. Slack Poster (`slack_poster.py`)
- Posts classified messages to appropriate Slack channels
- Creates rich message blocks with classification details
- Handles channel validation and error handling

### 3. Message Processor (`message_processor.py`)
- Main integration script
- Fetches unprocessed messages from database
- Coordinates classification and Slack posting
- Updates database with processing status

### 4. Test Suite (`test_message_processor.py`)
- Comprehensive testing of all components
- Validates classification accuracy
- Tests Slack integration

## 📊 Example Output

### Classification Result
```json
{
  "level_1_category": "Payments and Cash Out",
  "level_2_category": "Cash Out",
  "slack_channel": "#help-cashout-experience",
  "jira_ticket": "JIRA-123456"
}
```

### Slack Message
The system posts rich messages to Slack channels with:
- Classification details
- Original message content
- Source information (author, platform, timestamp)
- JIRA ticket link
- Action buttons for processing

## 🔄 Processing Flow

1. **Fetch Messages**: Get unprocessed messages from `unified_messages.db`
2. **Classify**: Use keyword matching to determine categories
3. **Post to Slack**: Send classified message to appropriate channel
4. **Update Database**: Mark message as processed
5. **Log Results**: Record success/failure statistics

## 📈 Monitoring

### Statistics
The system tracks:
- Total messages processed
- Success/failure rates
- Processing speed
- Category distribution
- Slack channel distribution

### Logging
- All operations are logged to `message_processor.log`
- Console output shows real-time progress
- Error details are captured for debugging

## 🚨 Error Handling

- **Database Errors**: Graceful handling of SQLite issues
- **Slack API Errors**: Retry logic and error reporting
- **Classification Errors**: Fallback to default categories
- **Network Issues**: Timeout handling and reconnection

## 🔧 Configuration

### Environment Variables
```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret
```

### Processing Options
- `batch_size`: Number of messages to process per cycle
- `interval`: Seconds between continuous processing cycles
- `rate_limit_delay`: Delay between Slack API calls

## 🧪 Testing Examples

### Test Messages
```python
# Cash out issue
"My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!"

# App performance issue  
"The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings."

# General positive sentiment
"I just love how easy it is to see my earnings now, thanks!"
```

### Expected Classifications
1. **Cash out issue** → Payments and Cash Out → Cash Out → #help-cashout-experience
2. **App performance** → Product Feedback → App UX / Performance → #help-performance-ux  
3. **Positive sentiment** → General Sentiment → Non-relevant → (no Slack channel)

## 🔍 Troubleshooting

### Common Issues

1. **Slack Channels Not Found**
   - Verify channel names exist in your Slack workspace
   - Check bot permissions for channel access
   - Ensure channels are public or bot is invited

2. **Classification Not Working**
   - Check keyword matching in `message_classifier.py`
   - Verify message content is being processed correctly
   - Review confidence thresholds

3. **Database Connection Issues**
   - Ensure `unified_messages.db` exists and is accessible
   - Check database schema matches expected structure
   - Verify SQLite permissions

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python message_processor.py --batch-size 5
```

## 📝 Customization

### Adding New Categories
1. Update `Level1Category` and `Level2Category` enums
2. Add keywords to `KEYWORDS` and `L2_KEYWORDS` dictionaries
3. Update `SLACK_CHANNEL_MAPPING` for new channels
4. Test with sample messages

### Modifying Classification Logic
- Adjust keyword weights in `_classify_level1()` and `_classify_level2()`
- Update confidence thresholds
- Add new keyword categories
- Implement machine learning models for better accuracy

## 🤝 Contributing

1. Test changes with `python test_message_processor.py`
2. Update documentation for new features
3. Follow existing code style and patterns
4. Add appropriate error handling and logging

## 📄 License

This project is part of the unified feedback processing system for EarnIn.

