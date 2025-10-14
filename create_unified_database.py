#!/usr/bin/env python3
"""
Unified Messages Database Creator

This script creates a unified database that stores all messages from Reddit and Slack
with comprehensive metadata. It migrates existing data from separate databases and
provides a single source of truth for all message data.
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedMessageDatabase:
    """Unified database for all messages from Reddit, Slack, and other sources"""
    
    def __init__(self, db_path: str = "unified_messages.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the unified database with comprehensive schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create unified messages table with all possible fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,  -- 'reddit', 'slack', 'app_store', 'play_store', 'twitter', 'web'
                    platform TEXT,         -- 'reddit', 'slack', 'ios', 'android', 'twitter', 'web'
                    content TEXT NOT NULL,
                    title TEXT,            -- For Reddit posts
                    author TEXT NOT NULL,
                    author_id TEXT,        -- Platform-specific author ID
                    timestamp TEXT NOT NULL,
                    created_utc REAL,      -- Unix timestamp for Reddit
                    url TEXT,
                    permalink TEXT,        -- Reddit permalink
                    
                    -- Reddit-specific fields
                    subreddit TEXT,
                    score INTEGER,
                    num_comments INTEGER,
                    is_self BOOLEAN,
                    over_18 BOOLEAN,
                    selftext TEXT,
                    
                    -- App Store/Play Store specific fields
                    rating INTEGER,
                    app_version TEXT,
                    device_info TEXT,
                    
                    -- Slack-specific fields
                    channel_id TEXT,
                    channel_name TEXT,
                    thread_ts TEXT,
                    reply_count INTEGER,
                    
                    -- Twitter-specific fields
                    retweet_count INTEGER,
                    favorite_count INTEGER,
                    hashtags TEXT,         -- JSON array of hashtags
                    mentions TEXT,         -- JSON array of mentions
                    
                    -- Processing and analysis fields
                    language TEXT,
                    sentiment TEXT,        -- 'positive', 'negative', 'neutral'
                    category TEXT,         -- 'bug', 'feature_request', 'complaint', 'praise', 'question', 'spam', 'other'
                    severity TEXT,         -- 'low', 'medium', 'high', 'critical'
                    business_impact_score REAL,
                    pii_detected BOOLEAN DEFAULT FALSE,
                    processed BOOLEAN DEFAULT FALSE,
                    
                    -- Metadata
                    raw_data TEXT,         -- JSON of original raw data
                    tags TEXT,             -- JSON array of custom tags
                    notes TEXT,            -- Manual notes
                    
                    -- Timestamps
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create authors table for author information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    display_name TEXT,
                    platform TEXT,
                    author_id TEXT,        -- Platform-specific ID
                    reputation_score REAL,
                    follower_count INTEGER,
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    last_seen TEXT,
                    metadata TEXT          -- JSON of additional author data
                )
            """)
            
            # Create channels/subreddits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,  -- 'reddit', 'slack', 'twitter'
                    channel_id TEXT,         -- Platform-specific ID
                    description TEXT,
                    subscriber_count INTEGER,
                    is_private BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    metadata TEXT            -- JSON of additional channel data
                )
            """)
            
            # Create message threads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    platform TEXT,
                    thread_id TEXT,         -- Platform-specific thread ID
                    parent_message_id TEXT,
                    thread_url TEXT,
                    status TEXT,            -- 'active', 'closed', 'archived'
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            """)
            
            # Create message attachments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    filename TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    url TEXT,
                    local_path TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            """)
            
            # Create message reactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reactions (
                    id TEXT PRIMARY KEY,
                    message_id TEXT,
                    reaction_type TEXT,     -- 'upvote', 'downvote', 'like', 'emoji_name'
                    count INTEGER DEFAULT 1,
                    users TEXT,            -- JSON array of user IDs who reacted
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_author ON messages(author)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_processed ON messages(processed)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sentiment ON messages(sentiment)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_category ON messages(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_subreddit ON messages(subreddit)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel_name ON messages(channel_name)")
            
            conn.commit()
            logger.info(f"Unified database initialized at {self.db_path}")
    
    def migrate_reddit_data(self, reddit_db_path: str = "earnin_posts_ssl_fixed.db"):
        """Migrate Reddit posts from the existing database"""
        if not os.path.exists(reddit_db_path):
            logger.warning(f"Reddit database {reddit_db_path} not found, skipping migration")
            return 0
        
        migrated_count = 0
        with sqlite3.connect(reddit_db_path) as reddit_conn:
            reddit_cursor = reddit_conn.cursor()
            reddit_cursor.execute("SELECT * FROM posts")
            reddit_posts = reddit_cursor.fetchall()
            
            with sqlite3.connect(self.db_path) as unified_conn:
                unified_cursor = unified_conn.cursor()
                
                for post in reddit_posts:
                    # Map Reddit post data to unified schema
                    message_data = {
                        'id': f"reddit_{post[0]}",  # reddit_ + original_id
                        'source': 'reddit',
                        'platform': 'reddit',
                        'content': post[5] or post[1],  # selftext or title
                        'title': post[1],
                        'author': post[2],
                        'author_id': post[2],
                        'timestamp': datetime.fromtimestamp(post[8]).isoformat() if post[8] else post[12],
                        'created_utc': post[8],
                        'url': post[4],
                        'permalink': post[9],
                        'subreddit': post[3],
                        'score': post[6],
                        'num_comments': post[7],
                        'is_self': bool(post[10]),
                        'over_18': bool(post[11]),
                        'selftext': post[5],
                        'raw_data': json.dumps({
                            'original_id': post[0],
                            'title': post[1],
                            'author': post[2],
                            'subreddit': post[3],
                            'url': post[4],
                            'selftext': post[5],
                            'score': post[6],
                            'num_comments': post[7],
                            'created_utc': post[8],
                            'permalink': post[9],
                            'is_self': post[10],
                            'over_18': post[11],
                            'saved_at': post[12]
                        }),
                        'created_at': post[12] or datetime.now(timezone.utc).isoformat(),
                        'updated_at': post[12] or datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Insert into unified database
                    unified_cursor.execute("""
                        INSERT OR REPLACE INTO messages 
                        (id, source, platform, content, title, author, author_id, timestamp, created_utc, 
                         url, permalink, subreddit, score, num_comments, is_self, over_18, selftext, 
                         raw_data, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        message_data['id'], message_data['source'], message_data['platform'],
                        message_data['content'], message_data['title'], message_data['author'],
                        message_data['author_id'], message_data['timestamp'], message_data['created_utc'],
                        message_data['url'], message_data['permalink'], message_data['subreddit'],
                        message_data['score'], message_data['num_comments'], message_data['is_self'],
                        message_data['over_18'], message_data['selftext'], message_data['raw_data'],
                        message_data['created_at'], message_data['updated_at']
                    ))
                    
                    migrated_count += 1
                
                unified_conn.commit()
        
        logger.info(f"Migrated {migrated_count} Reddit posts to unified database")
        return migrated_count
    
    def migrate_feedback_data(self, feedback_db_path: str = "feedback.db"):
        """Migrate feedback data from the existing database"""
        if not os.path.exists(feedback_db_path):
            logger.warning(f"Feedback database {feedback_db_path} not found, skipping migration")
            return 0
        
        migrated_count = 0
        with sqlite3.connect(feedback_db_path) as feedback_conn:
            feedback_cursor = feedback_conn.cursor()
            feedback_cursor.execute("SELECT * FROM feedbacks")
            feedback_entries = feedback_cursor.fetchall()
            
            with sqlite3.connect(self.db_path) as unified_conn:
                unified_cursor = unified_conn.cursor()
                
                for feedback in feedback_entries:
                    # Map feedback data to unified schema
                    source = feedback[1]
                    platform = self._map_source_to_platform(source)
                    
                    message_data = {
                        'id': feedback[0],
                        'source': source,
                        'platform': platform,
                        'content': feedback[2],
                        'title': None,
                        'author': feedback[3],
                        'author_id': feedback[3],
                        'timestamp': feedback[4],
                        'created_utc': None,
                        'url': feedback[5],
                        'permalink': None,
                        'subreddit': None,
                        'score': None,
                        'num_comments': None,
                        'is_self': None,
                        'over_18': None,
                        'selftext': None,
                        'rating': feedback[6],
                        'language': feedback[7],
                        'sentiment': feedback[9],
                        'category': feedback[8],
                        'severity': feedback[10],
                        'business_impact_score': feedback[11],
                        'pii_detected': bool(feedback[12]),
                        'processed': bool(feedback[13]),
                        'raw_data': json.dumps({
                            'original_id': feedback[0],
                            'source': feedback[1],
                            'content': feedback[2],
                            'author': feedback[3],
                            'timestamp': feedback[4],
                            'url': feedback[5],
                            'rating': feedback[6],
                            'language': feedback[7],
                            'category': feedback[8],
                            'sentiment': feedback[9],
                            'severity': feedback[10],
                            'business_impact_score': feedback[11],
                            'pii_detected': feedback[12],
                            'processed': feedback[13],
                            'created_at': feedback[14],
                            'updated_at': feedback[15]
                        }),
                        'created_at': feedback[14],
                        'updated_at': feedback[15]
                    }
                    
                    # Insert into unified database
                    unified_cursor.execute("""
                        INSERT OR REPLACE INTO messages 
                        (id, source, platform, content, title, author, author_id, timestamp, created_utc,
                         url, permalink, subreddit, score, num_comments, is_self, over_18, selftext,
                         rating, language, sentiment, category, severity, business_impact_score,
                         pii_detected, processed, raw_data, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        message_data['id'], message_data['source'], message_data['platform'],
                        message_data['content'], message_data['title'], message_data['author'],
                        message_data['author_id'], message_data['timestamp'], message_data['created_utc'],
                        message_data['url'], message_data['permalink'], message_data['subreddit'],
                        message_data['score'], message_data['num_comments'], message_data['is_self'],
                        message_data['over_18'], message_data['selftext'], message_data['rating'],
                        message_data['language'], message_data['sentiment'], message_data['category'],
                        message_data['severity'], message_data['business_impact_score'],
                        message_data['pii_detected'], message_data['processed'], message_data['raw_data'],
                        message_data['created_at'], message_data['updated_at']
                    ))
                    
                    migrated_count += 1
                
                unified_conn.commit()
        
        logger.info(f"Migrated {migrated_count} feedback entries to unified database")
        return migrated_count
    
    def _map_source_to_platform(self, source: str) -> str:
        """Map source to platform"""
        mapping = {
            'app_store': 'ios',
            'play_store': 'android',
            'reddit': 'reddit',
            'slack': 'slack',
            'twitter': 'twitter',
            'web': 'web',
            'email': 'email'
        }
        return mapping.get(source, source)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Messages by source
            cursor.execute("SELECT source, COUNT(*) FROM messages GROUP BY source")
            by_source = dict(cursor.fetchall())
            
            # Messages by platform
            cursor.execute("SELECT platform, COUNT(*) FROM messages GROUP BY platform")
            by_platform = dict(cursor.fetchall())
            
            # Messages by sentiment
            cursor.execute("SELECT sentiment, COUNT(*) FROM messages WHERE sentiment IS NOT NULL GROUP BY sentiment")
            by_sentiment = dict(cursor.fetchall())
            
            # Messages by category
            cursor.execute("SELECT category, COUNT(*) FROM messages WHERE category IS NOT NULL GROUP BY category")
            by_category = dict(cursor.fetchall())
            
            # Processed vs unprocessed
            cursor.execute("SELECT processed, COUNT(*) FROM messages GROUP BY processed")
            by_processed = dict(cursor.fetchall())
            
            # Recent messages (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE datetime(timestamp) > datetime('now', '-1 day')
            """)
            recent_messages = cursor.fetchone()[0]
            
            return {
                'total_messages': total_messages,
                'by_source': by_source,
                'by_platform': by_platform,
                'by_sentiment': by_sentiment,
                'by_category': by_category,
                'by_processed': by_processed,
                'recent_messages_24h': recent_messages,
                'database_path': self.db_path,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    def add_message(self, message_data: Dict[str, Any]) -> bool:
        """Add a new message to the unified database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare the message data with defaults
                now = datetime.now(timezone.utc).isoformat()
                message_data.setdefault('created_at', now)
                message_data.setdefault('updated_at', now)
                message_data.setdefault('processed', False)
                message_data.setdefault('pii_detected', False)
                
                # Insert the message
                cursor.execute("""
                    INSERT OR REPLACE INTO messages 
                    (id, source, platform, content, title, author, author_id, timestamp, created_utc,
                     url, permalink, subreddit, score, num_comments, is_self, over_18, selftext,
                     rating, app_version, device_info, channel_id, channel_name, thread_ts, reply_count,
                     retweet_count, favorite_count, hashtags, mentions, language, sentiment, category,
                     severity, business_impact_score, pii_detected, processed, raw_data, tags, notes,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message_data.get('id'),
                    message_data.get('source'),
                    message_data.get('platform'),
                    message_data.get('content'),
                    message_data.get('title'),
                    message_data.get('author'),
                    message_data.get('author_id'),
                    message_data.get('timestamp'),
                    message_data.get('created_utc'),
                    message_data.get('url'),
                    message_data.get('permalink'),
                    message_data.get('subreddit'),
                    message_data.get('score'),
                    message_data.get('num_comments'),
                    message_data.get('is_self'),
                    message_data.get('over_18'),
                    message_data.get('selftext'),
                    message_data.get('rating'),
                    message_data.get('app_version'),
                    message_data.get('device_info'),
                    message_data.get('channel_id'),
                    message_data.get('channel_name'),
                    message_data.get('thread_ts'),
                    message_data.get('reply_count'),
                    message_data.get('retweet_count'),
                    message_data.get('favorite_count'),
                    json.dumps(message_data.get('hashtags', [])),
                    json.dumps(message_data.get('mentions', [])),
                    message_data.get('language'),
                    message_data.get('sentiment'),
                    message_data.get('category'),
                    message_data.get('severity'),
                    message_data.get('business_impact_score'),
                    message_data.get('pii_detected'),
                    message_data.get('processed'),
                    json.dumps(message_data.get('raw_data', {})),
                    json.dumps(message_data.get('tags', [])),
                    message_data.get('notes'),
                    message_data.get('created_at'),
                    message_data.get('updated_at')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False

def main():
    """Main function to create unified database and migrate data"""
    logger.info("🚀 Starting unified database creation and migration...")
    
    # Create unified database
    unified_db = UnifiedMessageDatabase()
    
    # Migrate existing data
    reddit_count = unified_db.migrate_reddit_data()
    feedback_count = unified_db.migrate_feedback_data()
    
    # Get final statistics
    stats = unified_db.get_database_stats()
    
    logger.info("✅ Unified database creation and migration completed!")
    logger.info(f"📊 Database Statistics:")
    logger.info(f"   Total messages: {stats['total_messages']}")
    logger.info(f"   By source: {stats['by_source']}")
    logger.info(f"   By platform: {stats['by_platform']}")
    logger.info(f"   By sentiment: {stats['by_sentiment']}")
    logger.info(f"   By category: {stats['by_category']}")
    logger.info(f"   Processed: {stats['by_processed']}")
    logger.info(f"   Recent (24h): {stats['recent_messages_24h']}")
    
    # Save statistics to file
    with open('unified_database_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"📁 Database created at: {unified_db.db_path}")
    logger.info(f"📊 Statistics saved to: unified_database_stats.json")

if __name__ == "__main__":
    main()
