# Reddit EarnIn Monitor

A continuous monitoring system that fetches new posts related to "earnin" from Reddit every minute and saves them to a database and JSON files.

## Features

- 🔄 **Continuous Monitoring**: Runs every minute to catch new posts
- 📊 **Database Storage**: SQLite database for persistent storage
- 📁 **JSON Export**: Individual JSON files for each monitoring cycle
- 📝 **Comprehensive Logging**: Detailed logs of all activities
- 🎯 **Targeted Subreddits**: Monitors 8 key subreddits related to EarnIn
- 🔍 **Cross-Subreddit Search**: Searches for "earnin" across all Reddit
- 📈 **Statistics Tracking**: Real-time monitoring statistics
- 🛑 **Graceful Shutdown**: Handles Ctrl+C and system signals properly

## Monitored Subreddits

1. **r/Earnin** - Main EarnIn community
2. **r/EarninB4B** - Boost for Boost requests
3. **r/EarninBoost** - EarnIn Boost community
4. **r/cashadvanceapps** - Cash advance discussions
5. **r/personalfinance** - Financial discussions
6. **r/EarningOnline** - Online earning opportunities
7. **r/beermoney** - Side income opportunities
8. **r/workonline** - Online work opportunities

## Quick Start

### Option 1: Using the startup script (Recommended)
```bash
./start_monitor.sh
```

### Option 2: Direct Python execution
```bash
python3 reddit_earnin_monitor.py
```

## Output Files

### Database
- **File**: `earnin_posts.db`
- **Format**: SQLite database
- **Tables**: 
  - `posts` - All collected posts
  - `monitoring_stats` - Monitoring statistics

### JSON Files
- **Format**: `earnin_posts_YYYYMMDD_HHMMSS.json`
- **Content**: New posts found in each monitoring cycle
- **Structure**: JSON with metadata and post details

### Logs
- **File**: `reddit_monitor.log`
- **Content**: Detailed monitoring logs
- **Level**: INFO and above

## Configuration

The monitor uses the following default settings:

- **Check Interval**: 60 seconds
- **Posts per Subreddit**: 10 (to catch new posts)
- **Search Limit**: 10 posts for cross-subreddit search
- **Age Filter**: Posts from last 2 minutes
- **Database**: SQLite with automatic schema creation

## Database Schema

### Posts Table
```sql
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    author TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    upvote_ratio REAL DEFAULT 0.0,
    num_comments INTEGER DEFAULT 0,
    created_utc TEXT NOT NULL,
    url TEXT,
    permalink TEXT NOT NULL,
    is_self BOOLEAN DEFAULT FALSE,
    over_18 BOOLEAN DEFAULT FALSE,
    flair TEXT,
    domain TEXT,
    fetched_at TEXT NOT NULL,
    is_new BOOLEAN DEFAULT TRUE
);
```

### Monitoring Stats Table
```sql
CREATE TABLE monitoring_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_time TEXT NOT NULL,
    posts_found INTEGER DEFAULT 0,
    new_posts INTEGER DEFAULT 0,
    subreddits_checked INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0.0
);
```

## Monitoring Statistics

The monitor tracks:
- Total posts found since startup
- New posts found in each cycle
- Number of monitoring checks performed
- Duration of each monitoring cycle
- Subreddit-specific statistics

## Example Output

```
🚀 Starting Reddit EarnIn Monitor...
============================================================
Monitoring 8 subreddits: Earnin, EarninB4B, EarninBoost, cashadvanceapps, personalfinance, EarningOnline, beermoney, workonline
Press Ctrl+C to stop monitoring

2025-10-14 11:30:28 - INFO - Starting new posts fetch...
2025-10-14 11:30:29 - INFO - r/Earnin: 0 posts found, 0 new
2025-10-14 11:30:30 - INFO - r/EarninB4B: 1 posts found, 1 new
2025-10-14 11:30:31 - INFO - Search results: 2 posts found
2025-10-14 11:30:32 - INFO - Fetch completed: 3 total posts, 3 new posts

🆕 Found 3 new EarnIn-related posts!
  • B4B please (r/EarninB4B)
  • Get up to $150/day cash advance before payday + $25 bonus... (r/ReferralNotReferal)
  • EarnIn boost request - need help (r/cashadvanceapps)

⏳ Waiting 60 seconds for next check...
```

## Stopping the Monitor

- Press **Ctrl+C** to stop the monitor gracefully
- The monitor will save final statistics and close cleanly
- All data is preserved in the database and JSON files

## Troubleshooting

### Common Issues

1. **Reddit API Rate Limits**
   - The monitor respects Reddit's rate limits
   - If you hit limits, the monitor will wait and retry

2. **Database Locked**
   - Make sure no other process is accessing the database
   - The monitor will retry database operations

3. **Network Issues**
   - The monitor will log network errors and continue
   - Failed checks are logged but don't stop the monitor

### Logs

Check `reddit_monitor.log` for detailed error information:
```bash
tail -f reddit_monitor.log
```

## Data Analysis

### Query the Database
```bash
sqlite3 earnin_posts.db
```

### Example Queries
```sql
-- Get all new posts from today
SELECT * FROM posts WHERE date(fetched_at) = date('now') AND is_new = 1;

-- Get posts by subreddit
SELECT subreddit, COUNT(*) FROM posts GROUP BY subreddit;

-- Get monitoring statistics
SELECT * FROM monitoring_stats ORDER BY check_time DESC LIMIT 10;
```

## Requirements

- Python 3.6+
- PRAW (Python Reddit API Wrapper)
- SQLite3 (included with Python)

## Installation

```bash
pip3 install praw
```

## Security Note

The Reddit credentials are embedded in the script for convenience. In a production environment, consider using environment variables or a secure configuration file.

---

**Note**: This monitor is designed to run continuously and will create new files with each monitoring cycle. Monitor disk space usage for long-running sessions.

