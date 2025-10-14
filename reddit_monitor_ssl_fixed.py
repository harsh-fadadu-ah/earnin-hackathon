#!/usr/bin/env python3
"""
Reddit EarnIn Monitor - SSL Fixed Version
A continuous monitoring script that fetches new posts related to "earnin" every minute
with SSL bypass for corporate networks.
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
        logging.FileHandler('reddit_monitor_ssl_fixed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditEarnInMonitorSSLFixed:
    """Reddit monitor with SSL bypass for corporate networks"""
    
    def __init__(self):
        # Reddit API credentials
        self.client_id = "k3n3Jc9hKlpm0OBC9f5VoA"
        self.client_secret = "GM2yWaXXS7-SCwMq5KUpARLh2bqg2A"
        self.user_agent = "FeedForward"
        
        # Subreddits to monitor
        self.subreddits = [
            "Earnin", "EarninB4B", "EarninBoost", "cashadvanceapps",
            "personalfinance", "EarningOnline", "beermoney", "workonline"
        ]
        
        # Database setup
        self.db_path = "earnin_posts_ssl_fixed.db"
        self.init_database()
        
        # Access token for Reddit API
        self.access_token = None
        self.token_expires = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Reddit EarnIn Monitor (SSL Fixed) initialized successfully")
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                title TEXT,
                author TEXT,
                subreddit TEXT,
                url TEXT,
                selftext TEXT,
                score INTEGER,
                num_comments INTEGER,
                created_utc REAL,
                permalink TEXT,
                is_self BOOLEAN,
                over_18 BOOLEAN,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
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
                    posts.append({
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
                    })
                
                logger.info(f"r/{subreddit_name}: {len(posts)} posts found")
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
                    posts.append({
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
                    })
                
                logger.info(f"Search results: {len(posts)} posts found")
                return posts
            else:
                logger.error(f"❌ Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def save_posts_to_db(self, posts: List[Dict]) -> int:
        """Save posts to database, returning count of new posts"""
        if not posts:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_count = 0
        for post in posts:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO posts 
                    (id, title, author, subreddit, url, selftext, score, num_comments, 
                     created_utc, permalink, is_self, over_18)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post['id'], post['title'], post['author'], post['subreddit'],
                    post['url'], post['selftext'], post['score'], post['num_comments'],
                    post['created_utc'], post['permalink'], post['is_self'], post['over_18']
                ))
                
                if cursor.rowcount > 0:
                    new_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving post {post['id']}: {e}")
        
        conn.commit()
        conn.close()
        
        return new_count
    
    def fetch_new_posts(self) -> int:
        """Fetch new posts from all monitored subreddits"""
        logger.info("Starting new posts fetch...")
        
        all_posts = []
        
        # Fetch from each subreddit
        for subreddit in self.subreddits:
            posts = self.fetch_subreddit_posts(subreddit, limit=10)
            all_posts.extend(posts)
        
        # Search for 'earnin' posts
        logger.info("Searching for 'earnin' posts across all subreddits...")
        search_posts = self.search_posts('earnin', limit=10)
        all_posts.extend(search_posts)
        
        # Remove duplicates based on post ID
        unique_posts = {post['id']: post for post in all_posts}.values()
        
        # Save to database
        new_count = self.save_posts_to_db(list(unique_posts))
        
        logger.info(f"Fetch completed: {len(unique_posts)} total posts, {new_count} new posts")
        return new_count
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        sys.exit(0)
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Reddit EarnIn Monitor (SSL Fixed)...")
        logger.info(f"Monitoring {len(self.subreddits)} subreddits: {', '.join(self.subreddits)}")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                self.fetch_new_posts()
                logger.info("⏳ Waiting 60 seconds for next check...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("🛑 Reddit EarnIn Monitor stopped")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise

if __name__ == "__main__":
    monitor = RedditEarnInMonitorSSLFixed()
    monitor.run()

