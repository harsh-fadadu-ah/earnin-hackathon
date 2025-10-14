# Unified Messages Database System

## Overview

This system creates a unified database that stores all messages from Reddit, Slack, and other platforms with comprehensive metadata. It replaces the previous separate database files with a single, well-structured database that provides better data organization and analysis capabilities.

## Database Structure

### Main Table: `messages`

The unified database uses a single `messages` table that stores all types of messages with the following comprehensive schema:

#### Core Fields
- `id` - Unique message identifier
- `source` - Source platform (reddit, slack, app_store, play_store, twitter, web)
- `platform` - Platform type (reddit, slack, ios, android, twitter, web)
- `content` - Message content/text
- `title` - Message title (for Reddit posts)
- `author` - Author username
- `author_id` - Platform-specific author ID
- `timestamp` - Message timestamp (ISO format)
- `created_utc` - Unix timestamp (for Reddit)
- `url` - Original message URL
- `permalink` - Reddit permalink

#### Reddit-Specific Fields
- `subreddit` - Subreddit name
- `score` - Reddit score/upvotes
- `num_comments` - Number of comments
- `is_self` - Whether it's a self post
- `over_18` - NSFW flag
- `selftext` - Post text content

#### App Store/Play Store Fields
- `rating` - Star rating (1-5)
- `app_version` - App version
- `device_info` - Device information

#### Slack-Specific Fields
- `channel_id` - Slack channel ID
- `channel_name` - Slack channel name
- `thread_ts` - Thread timestamp
- `reply_count` - Number of replies

#### Twitter-Specific Fields
- `retweet_count` - Number of retweets
- `favorite_count` - Number of likes
- `hashtags` - JSON array of hashtags
- `mentions` - JSON array of mentions

#### Analysis Fields
- `language` - Detected language
- `sentiment` - Sentiment analysis (positive, negative, neutral)
- `category` - Message category (bug, feature_request, complaint, praise, question, spam, other)
- `severity` - Severity level (low, medium, high, critical)
- `business_impact_score` - Business impact score (0.0-1.0)
- `pii_detected` - Whether PII was detected
- `processed` - Whether message has been processed

#### Metadata Fields
- `raw_data` - JSON of original raw data
- `tags` - JSON array of custom tags
- `notes` - Manual notes
- `created_at` - Record creation timestamp
- `updated_at` - Record update timestamp
- `saved_at` - Database save timestamp

### Additional Tables

- `authors` - Author information and reputation
- `channels` - Channel/subreddit information
- `threads` - Message thread relationships
- `attachments` - File attachments
- `reactions` - Message reactions/upvotes

## Files Created

### Core Database Files
1. **`unified_messages.db`** - The main unified database file
2. **`create_unified_database.py`** - Script to create and migrate data to unified database
3. **`unified_database_stats.json`** - Database statistics

### Updated Monitor Scripts
4. **`reddit_monitor_unified.py`** - Reddit monitor using unified database
5. **`feedback_mcp_server_unified.py`** - Feedback server using unified database
6. **`unified_mcp_monitor_updated.py`** - Updated unified monitor

### Database Tools
7. **`database_viewer.py`** - Command-line tool to view and search the database

## Current Data Summary

As of the latest migration:
- **Total Messages**: 174
- **By Source**:
  - Reddit: 101 messages
  - Slack: 41 messages
  - Play Store: 14 messages
  - App Store: 13 messages
  - Twitter: 5 messages
- **By Platform**:
  - Reddit: 101 messages
  - Slack: 41 messages
  - Android: 14 messages
  - iOS: 13 messages
  - Twitter: 5 messages
- **Processing Status**:
  - Processed: 68 messages
  - Unprocessed: 106 messages
- **Recent Activity**: 119 messages in the last 24 hours

## Usage

### 1. Create and Migrate Database

```bash
python create_unified_database.py
```

This will:
- Create the unified database with proper schema
- Migrate all existing data from separate databases
- Generate statistics and save them to `unified_database_stats.json`

### 2. View Database Statistics

```bash
python database_viewer.py --stats
```

### 3. Search Messages

```bash
# Search by content
python database_viewer.py --search "earnin"

# Filter by source
python database_viewer.py --source reddit --limit 10

# Filter by sentiment
python database_viewer.py --sentiment positive

# Show recent messages
python database_viewer.py --recent 24 --limit 20
```

### 4. Export Data

```bash
# Export all messages to JSON
python database_viewer.py --export messages.json

# Export specific source
python database_viewer.py --source reddit --export reddit_messages.json
```

### 5. Get Message Details

```bash
python database_viewer.py --message-id "reddit_1o6copu"
```

### 6. Run Updated Monitors

```bash
# Run unified Reddit monitor
python reddit_monitor_unified.py

# Run updated unified monitor
python unified_mcp_monitor_updated.py
```

## Database Schema Details

### Indexes Created

The database includes several indexes for optimal query performance:
- `idx_messages_source` - For filtering by source
- `idx_messages_platform` - For filtering by platform
- `idx_messages_author` - For filtering by author
- `idx_messages_timestamp` - For time-based queries
- `idx_messages_processed` - For processing status queries
- `idx_messages_sentiment` - For sentiment analysis queries
- `idx_messages_category` - For category queries
- `idx_messages_subreddit` - For Reddit subreddit queries
- `idx_messages_channel_name` - For Slack channel queries

### Data Types

- **TEXT**: Strings, JSON data, timestamps
- **INTEGER**: Counts, ratings, scores
- **REAL**: Floating-point numbers (scores, impact scores)
- **BOOLEAN**: True/false flags

## Benefits of Unified Database

1. **Single Source of Truth**: All messages in one place
2. **Comprehensive Metadata**: Rich metadata for analysis
3. **Better Performance**: Optimized indexes and queries
4. **Easier Analysis**: Unified schema for cross-platform analysis
5. **Scalability**: Designed to handle large volumes of data
6. **Flexibility**: Extensible schema for new platforms
7. **Data Integrity**: Proper relationships and constraints

## Migration Notes

- All existing data has been preserved and migrated
- Original database files remain intact as backups
- New messages will be stored in the unified database
- The system maintains backward compatibility

## Future Enhancements

1. **Real-time Processing**: Stream processing for new messages
2. **Advanced Analytics**: Machine learning for sentiment and categorization
3. **API Endpoints**: REST API for database access
4. **Dashboard**: Web interface for data visualization
5. **Automated Alerts**: Notifications for important messages
6. **Data Export**: Multiple export formats (CSV, JSON, XML)

## Troubleshooting

### Database Not Found
If you get "Database not found" errors:
1. Run `python create_unified_database.py` first
2. Check that `unified_messages.db` exists in the current directory

### Migration Issues
If migration fails:
1. Check that original database files exist
2. Verify file permissions
3. Check disk space

### Performance Issues
For large databases:
1. Use appropriate indexes
2. Limit query results with `--limit`
3. Use specific filters to narrow results

## Support

For issues or questions:
1. Check the logs in `unified_monitor_updated.log`
2. Use `python database_viewer.py --stats` to verify database status
3. Review the database schema with SQLite tools
