#!/usr/bin/env python3
"""
Reddit EarnIn Monitor - Unified Database Version
A continuous monitoring script that fetches new posts related to "earnin" every minute
and stores them in the unified messages database with comprehensive metadata.
"""

import requests
import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import os
import signal
import sys
import ssl
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_monitor_unified.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditEarnInMonitorUnified:
    """Reddit monitor with unified database storage"""
    
    def __init__(self, unified_db_path: str = "unified_messages.db"):
        # Reddit API credentials
        self.client_id = "k3n3Jc9hKlpm0OBC9f5VoA"
        self.client_secret = "GM2yWaXXS7-SCwMq5KUpARLh2bqg2A"
        self.user_agent = "FeedForward"
        
        # Subreddits to monitor
        self.subreddits = [
            "Earnin", "EarninB4B", "EarninBoost", "cashadvanceapps",
            "personalfinance", "EarningOnline", "beermoney", "workonline"
        ]
        
        # Unified database setup
        self.unified_db_path = unified_db_path
        self.init_unified_database()
        
        # Access token for Reddit API
        self.access_token = None
        self.token_expires = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Reddit EarnIn Monitor (Unified Database) initialized successfully")
    
    def init_unified_database(self):
        """Initialize connection to unified database"""
        if not os.path.exists(self.unified_db_path):
            logger.error(f"Unified database {self.unified_db_path} not found!")
            logger.info("Please run create_unified_database.py first to create the unified database")
            sys.exit(1)
        
        # Test connection
        try:
            with sqlite3.connect(self.unified_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages WHERE source = 'reddit'")
                existing_count = cursor.fetchone()[0]
                logger.info(f"Connected to unified database. Found {existing_count} existing Reddit messages")
        except Exception as e:
            logger.error(f"Error connecting to unified database: {e}")
            sys.exit(1)
    
    def get_access_token(self):
        """Get Reddit API access token"""
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token
        
        auth_url = "https://www.reddit.com/api/v1/access_token"
        auth_data = {
            'grant_type': 'client_credentials'
        }
        auth_headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            # Use requests with SSL bypass
            response = requests.post(
                auth_url,
                data=auth_data,
                headers=auth_headers,
                auth=(self.client_id, self.client_secret),
                verify=False,  # SSL bypass
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Set expiration time (usually 1 hour)
                self.token_expires = datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600) - 60)
                logger.info("✅ Reddit access token obtained")
                return self.access_token
            else:
                logger.error(f"❌ Failed to get access token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting access token: {e}")
            return None
    
    def is_earnin_related(self, post: Dict) -> bool:
        """Check if a post is related to Earnin app or organization"""
        earnin_keywords = [
            'earnin', 'earn in', 'earn-in', 'earn.in',
            'earnin app', 'earn in app', 'earn-in app',
            'earnin cash advance', 'earn in cash advance',
            'earnin instant pay', 'earn in instant pay',
            'earnin advance', 'earn in advance',
            'earnin loan', 'earn in loan',
            'earnin payday', 'earn in payday',
            'earnin money', 'earn in money',
            'earnin tips', 'earn in tips',
            'earnin boost', 'earn in boost',
            'earnin lightning', 'earn in lightning',
            'earnin card', 'earn in card',
            'earnin balance shield', 'earn in balance shield',
            'earnin insights', 'earn in insights',
            'earnin tools', 'earn in tools'
        ]
        
        # Combine title and content for checking
        text_to_check = f"{post.get('title', '')} {post.get('selftext', '')}".lower()
        
        # Check if any Earnin keyword is present
        for keyword in earnin_keywords:
            if keyword in text_to_check:
                return True
        
        return False

    def fetch_subreddit_posts(self, subreddit_name: str, limit: int = 10) -> List[Dict]:
        """Fetch posts from a specific subreddit"""
        if not self.get_access_token():
            return []
        
        url = f"https://oauth.reddit.com/r/{subreddit_name}/new"
        headers = {
            'Authorization': f'bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        params = {
            'limit': limit,
            'raw_json': 1
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=False,  # SSL bypass
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for post_data in data['data']['children']:
                    post = post_data['data']
                    post_dict = {
                        'id': post['id'],
                        'title': post['title'],
                        'author': post['author'],
                        'subreddit': post['subreddit'],
                        'url': post['url'],
                        'selftext': post.get('selftext', ''),
                        'score': post['score'],
                        'num_comments': post['num_comments'],
                        'created_utc': post['created_utc'],
                        'permalink': post['permalink'],
                        'is_self': post['is_self'],
                        'over_18': post['over_18']
                    }
                    
                    # Only add posts that are related to Earnin
                    if self.is_earnin_related(post_dict):
                        posts.append(post_dict)
                
                logger.info(f"r/{subreddit_name}: {len(posts)} Earnin-related posts found (from {len(data['data']['children'])} total posts)")
                return posts
            else:
                logger.error(f"❌ Failed to fetch from r/{subreddit_name}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error fetching from r/{subreddit_name}: {e}")
            return []
    
    def search_posts(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for posts across all subreddits"""
        if not self.get_access_token():
            return []
        
        url = "https://oauth.reddit.com/search"
        headers = {
            'Authorization': f'bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        params = {
            'q': query,
            'limit': limit,
            'sort': 'new',
            'raw_json': 1
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=False,  # SSL bypass
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                for post_data in data['data']['children']:
                    post = post_data['data']
                    post_dict = {
                        'id': post['id'],
                        'title': post['title'],
                        'author': post['author'],
                        'subreddit': post['subreddit'],
                        'url': post['url'],
                        'selftext': post.get('selftext', ''),
                        'score': post['score'],
                        'num_comments': post['num_comments'],
                        'created_utc': post['created_utc'],
                        'permalink': post['permalink'],
                        'is_self': post['is_self'],
                        'over_18': post['over_18']
                    }
                    
                    # Only add posts that are related to Earnin
                    if self.is_earnin_related(post_dict):
                        posts.append(post_dict)
                
                logger.info(f"Search results: {len(posts)} Earnin-related posts found (from {len(data['data']['children'])} total posts)")
                return posts
            else:
                logger.error(f"❌ Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def save_posts_to_unified_db(self, posts: List[Dict]) -> int:
        """Save posts to unified database, returning count of new posts"""
        if not posts:
            return 0
        
        new_count = 0
        with sqlite3.connect(self.unified_db_path) as conn:
            cursor = conn.cursor()
            
            for post in posts:
                try:
                    # Check if post already exists
                    cursor.execute("SELECT id FROM messages WHERE id = ?", (f"reddit_{post['id']}",))
                    if cursor.fetchone():
                        continue  # Skip existing posts
                    
                    # Prepare message data for unified database
                    message_data = {
                        'id': f"reddit_{post['id']}",
                        'source': 'reddit',
                        'platform': 'reddit',
                        'content': post['selftext'] or post['title'],
                        'title': post['title'],
                        'author': post['author'],
                        'author_id': post['author'],
                        'timestamp': datetime.fromtimestamp(post['created_utc']).isoformat(),
                        'created_utc': post['created_utc'],
                        'url': post['url'],
                        'permalink': f"https://reddit.com{post['permalink']}",
                        'subreddit': post['subreddit'],
                        'score': post['score'],
                        'num_comments': post['num_comments'],
                        'is_self': bool(post['is_self']),
                        'over_18': bool(post['over_18']),
                        'selftext': post['selftext'],
                        'raw_data': json.dumps(post),
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Insert into unified database
                    cursor.execute("""
                        INSERT INTO messages 
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
                    
                    new_count += 1
                    logger.debug(f"Saved new Reddit post: {post['id']} from r/{post['subreddit']}")
                    
                except Exception as e:
                    logger.error(f"Error saving post {post['id']}: {e}")
            
            conn.commit()
        
        return new_count
    
    def fetch_new_posts(self) -> int:
        """Fetch new posts from all monitored subreddits"""
        logger.info("Starting new posts fetch...")
        
        all_posts = []
        
        # Fetch from each subreddit (only Earnin-related posts)
        for subreddit in self.subreddits:
            posts = self.fetch_subreddit_posts(subreddit, limit=10)  # Reduced limit to 10 recent posts
            all_posts.extend(posts)
        
        # Search for 'earnin' posts (only Earnin-related posts)
        logger.info("Searching for 'earnin' posts across all subreddits...")
        search_posts = self.search_posts('earnin', limit=10)  # Reduced limit to 10 recent posts
        all_posts.extend(search_posts)
        
        # Remove duplicates based on post ID
        unique_posts = {post['id']: post for post in all_posts}.values()
        
        # Save to unified database
        new_count = self.save_posts_to_unified_db(list(unique_posts))
        
        logger.info(f"Fetch completed: {len(unique_posts)} total posts, {new_count} new posts")
        return new_count
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics from the unified database"""
        with sqlite3.connect(self.unified_db_path) as conn:
            cursor = conn.cursor()
            
            # Total Reddit messages
            cursor.execute("SELECT COUNT(*) FROM messages WHERE source = 'reddit'")
            total_reddit = cursor.fetchone()[0]
            
            # Recent Reddit messages (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE source = 'reddit' AND datetime(timestamp) > datetime('now', '-1 day')
            """)
            recent_reddit = cursor.fetchone()[0]
            
            # Messages by subreddit
            cursor.execute("""
                SELECT subreddit, COUNT(*) FROM messages 
                WHERE source = 'reddit' AND subreddit IS NOT NULL 
                GROUP BY subreddit ORDER BY COUNT(*) DESC
            """)
            by_subreddit = dict(cursor.fetchall())
            
            return {
                'total_reddit_messages': total_reddit,
                'recent_reddit_messages_24h': recent_reddit,
                'by_subreddit': by_subreddit
            }
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Reddit EarnIn Monitor (Unified Database)...")
        logger.info(f"Monitoring {len(self.subreddits)} subreddits: {', '.join(self.subreddits)}")
        logger.info(f"Using unified database: {self.unified_db_path}")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                self.fetch_new_posts()
                
                # Show database stats
                stats = self.get_database_stats()
                logger.info(f"📊 Database Stats: {stats['total_reddit_messages']} total Reddit messages, {stats['recent_reddit_messages_24h']} recent")
                
                logger.info("⏳ Waiting 60 seconds for next check...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("🛑 Reddit EarnIn Monitor stopped")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise

if __name__ == "__main__":
    monitor = RedditEarnInMonitorUnified()
    monitor.run()
