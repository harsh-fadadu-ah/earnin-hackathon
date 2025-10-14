#!/usr/bin/env python3
"""
Reddit EarnIn Monitor

A continuous monitoring script that fetches new posts related to "earnin" every minute
and saves them to a database and JSON files.
"""

import praw
import json
import sqlite3
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import os
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditEarnInMonitor:
    """Continuous Reddit monitor for EarnIn-related posts"""
    
    def __init__(self):
        # Initialize Reddit client
        self.reddit = praw.Reddit(
            client_id="k3n3Jc9hKlpm0OBC9f5VoA",
            client_secret="GM2yWaXXS7-SCwMq5KUpARLh2bqg2A",
            user_agent="FeedForward",
            username="Best_Mirror2588",
            password="Harsh_password"
        )
        
        # Subreddits to monitor
        self.subreddits = [
            "Earnin", "EarninB4B", "EarninBoost", "cashadvanceapps",
            "personalfinance", "EarningOnline", "beermoney", "workonline"
        ]
        
        # Database setup
        self.db_path = "earnin_posts.db"
        self.init_database()
        
        # Monitoring state
        self.running = True
        self.last_check_time = datetime.now()
        self.processed_posts = set()  # Track processed post IDs
        
        # Statistics
        self.stats = {
            "total_posts_found": 0,
            "new_posts_found": 0,
            "monitoring_start_time": datetime.now().isoformat(),
            "last_check": None,
            "checks_performed": 0
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Reddit EarnIn Monitor initialized successfully")
    
    def init_database(self):
        """Initialize SQLite database for storing posts"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create posts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
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
                )
            """)
            
            # Create monitoring stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_time TEXT NOT NULL,
                    posts_found INTEGER DEFAULT 0,
                    new_posts INTEGER DEFAULT 0,
                    subreddits_checked INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0.0
                )
            """)
            
            conn.commit()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def save_post(self, post_data: Dict[str, Any], is_new: bool = True) -> bool:
        """Save post to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO posts 
                    (id, title, content, author, subreddit, score, upvote_ratio, 
                     num_comments, created_utc, url, permalink, is_self, over_18, 
                     flair, domain, fetched_at, is_new)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post_data["id"], post_data["title"], post_data["content"],
                    post_data["author"], post_data["subreddit"], post_data["score"],
                    post_data["upvote_ratio"], post_data["num_comments"],
                    post_data["created_utc"], post_data["url"], post_data["permalink"],
                    post_data["is_self"], post_data["over_18"], post_data["flair"],
                    post_data["domain"], post_data["fetched_at"], is_new
                ))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving post {post_data['id']}: {e}")
            return False
    
    def save_monitoring_stats(self, check_time: datetime, posts_found: int, 
                            new_posts: int, subreddits_checked: int, duration: float):
        """Save monitoring statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO monitoring_stats 
                    (check_time, posts_found, new_posts, subreddits_checked, duration_seconds)
                    VALUES (?, ?, ?, ?, ?)
                """, (check_time.isoformat(), posts_found, new_posts, subreddits_checked, duration))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving monitoring stats: {e}")
    
    def fetch_new_posts(self) -> Dict[str, Any]:
        """Fetch new posts from all monitored subreddits"""
        start_time = datetime.now()
        all_posts = []
        new_posts = []
        subreddit_stats = {}
        
        logger.info("Starting new posts fetch...")
        
        # Check each subreddit
        for subreddit_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = []
                
                # Get recent posts (last 10 posts to catch any new ones)
                for submission in subreddit.new(limit=10):
                    post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    
                    # Only include posts from the last 2 minutes (to catch new posts)
                    if post_time >= self.last_check_time - timedelta(minutes=2):
                        post_data = {
                            "id": submission.id,
                            "title": submission.title,
                            "content": submission.selftext if submission.is_self else "",
                            "author": str(submission.author) if submission.author else "[deleted]",
                            "subreddit": submission.subreddit.display_name,
                            "score": submission.score,
                            "upvote_ratio": submission.upvote_ratio,
                            "num_comments": submission.num_comments,
                            "created_utc": post_time.isoformat(),
                            "url": submission.url,
                            "permalink": f"https://reddit.com{submission.permalink}",
                            "is_self": submission.is_self,
                            "over_18": submission.over_18,
                            "flair": submission.link_flair_text,
                            "domain": submission.domain,
                            "fetched_at": datetime.now().isoformat()
                        }
                        
                        posts.append(post_data)
                        all_posts.append(post_data)
                        
                        # Check if this is a new post
                        if submission.id not in self.processed_posts:
                            new_posts.append(post_data)
                            self.processed_posts.add(submission.id)
                
                subreddit_stats[subreddit_name] = {
                    "posts_found": len(posts),
                    "new_posts": len([p for p in posts if p["id"] not in self.processed_posts])
                }
                
                logger.info(f"r/{subreddit_name}: {len(posts)} posts found, {len([p for p in posts if p['id'] not in self.processed_posts])} new")
                
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                subreddit_stats[subreddit_name] = {"error": str(e)}
        
        # Also search for posts containing "earnin" across all subreddits
        try:
            logger.info("Searching for 'earnin' posts across all subreddits...")
            search_posts = []
            
            for submission in self.reddit.subreddit("all").search("earnin", sort="new", limit=10):
                post_time = datetime.fromtimestamp(submission.created_utc)
                
                # Only include recent posts
                if post_time >= self.last_check_time - timedelta(minutes=2):
                    post_data = {
                        "id": submission.id,
                        "title": submission.title,
                        "content": submission.selftext if submission.is_self else "",
                        "author": str(submission.author) if submission.author else "[deleted]",
                        "subreddit": submission.subreddit.display_name,
                        "score": submission.score,
                        "upvote_ratio": submission.upvote_ratio,
                        "num_comments": submission.num_comments,
                        "created_utc": post_time.isoformat(),
                        "url": submission.url,
                        "permalink": f"https://reddit.com{submission.permalink}",
                        "is_self": submission.is_self,
                        "over_18": submission.over_18,
                        "flair": submission.link_flair_text,
                        "domain": submission.domain,
                        "fetched_at": datetime.now().isoformat()
                    }
                    
                    search_posts.append(post_data)
                    all_posts.append(post_data)
                    
                    if submission.id not in self.processed_posts:
                        new_posts.append(post_data)
                        self.processed_posts.add(submission.id)
            
            subreddit_stats["search_results"] = {
                "posts_found": len(search_posts),
                "new_posts": len([p for p in search_posts if p["id"] not in self.processed_posts])
            }
            
            logger.info(f"Search results: {len(search_posts)} posts found")
            
        except Exception as e:
            logger.error(f"Error searching for 'earnin' posts: {e}")
            subreddit_stats["search_results"] = {"error": str(e)}
        
        # Remove duplicates
        unique_posts = {}
        for post in all_posts:
            unique_posts[post["id"]] = post
        
        unique_new_posts = {}
        for post in new_posts:
            unique_new_posts[post["id"]] = post
        
        # Save new posts to database
        for post in unique_new_posts.values():
            self.save_post(post, is_new=True)
        
        # Update statistics
        duration = (datetime.now() - start_time).total_seconds()
        self.stats["total_posts_found"] += len(unique_posts)
        self.stats["new_posts_found"] += len(unique_new_posts)
        self.stats["last_check"] = datetime.now().isoformat()
        self.stats["checks_performed"] += 1
        
        # Save monitoring stats
        self.save_monitoring_stats(
            datetime.now(), len(unique_posts), len(unique_new_posts), 
            len(self.subreddits), duration
        )
        
        # Save to JSON file for easy access
        self.save_to_json(unique_new_posts.values())
        
        result = {
            "check_time": datetime.now().isoformat(),
            "total_posts_found": len(unique_posts),
            "new_posts_found": len(unique_new_posts),
            "subreddit_stats": subreddit_stats,
            "new_posts": list(unique_new_posts.values()),
            "duration_seconds": duration
        }
        
        logger.info(f"Fetch completed: {len(unique_posts)} total posts, {len(unique_new_posts)} new posts")
        
        return result
    
    def save_to_json(self, posts: List[Dict[str, Any]]):
        """Save posts to JSON file"""
        if not posts:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"earnin_posts_{timestamp}.json"
        
        data = {
            "fetch_timestamp": datetime.now().isoformat(),
            "posts_count": len(posts),
            "posts": list(posts)
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(posts)} new posts to {filename}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def print_stats(self):
        """Print current monitoring statistics"""
        print("\n" + "="*60)
        print("📊 REDDIT EARNIN MONITOR STATISTICS")
        print("="*60)
        print(f"🕐 Monitoring since: {self.stats['monitoring_start_time']}")
        print(f"🔄 Checks performed: {self.stats['checks_performed']}")
        print(f"📝 Total posts found: {self.stats['total_posts_found']}")
        print(f"🆕 New posts found: {self.stats['new_posts_found']}")
        print(f"⏰ Last check: {self.stats['last_check']}")
        print(f"💾 Database: {self.db_path}")
        print("="*60)
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Reddit EarnIn Monitor...")
        logger.info(f"Monitoring {len(self.subreddits)} subreddits: {', '.join(self.subreddits)}")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            while self.running:
                try:
                    # Fetch new posts
                    result = self.fetch_new_posts()
                    
                    # Update last check time
                    self.last_check_time = datetime.now()
                    
                    # Print summary if new posts found
                    if result["new_posts_found"] > 0:
                        print(f"\n🆕 Found {result['new_posts_found']} new EarnIn-related posts!")
                        for post in result["new_posts"][:5]:  # Show first 5
                            print(f"  • {post['title'][:60]}... (r/{post['subreddit']})")
                        if result["new_posts_found"] > 5:
                            print(f"  ... and {result['new_posts_found'] - 5} more")
                    
                    # Print stats every 10 checks
                    if self.stats["checks_performed"] % 10 == 0:
                        self.print_stats()
                    
                    # Wait for next check (60 seconds)
                    logger.info("⏳ Waiting 60 seconds for next check...")
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    logger.info("⏳ Waiting 60 seconds before retry...")
                    time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            self.print_stats()
            logger.info("🛑 Reddit EarnIn Monitor stopped")

def main():
    """Main entry point"""
    print("🚀 Reddit EarnIn Monitor")
    print("=" * 40)
    print("This script will monitor Reddit for new posts related to 'earnin'")
    print("and save them to a database and JSON files every minute.")
    print("Press Ctrl+C to stop monitoring.")
    print("=" * 40)
    
    monitor = RedditEarnInMonitor()
    monitor.run()

if __name__ == "__main__":
    main()

