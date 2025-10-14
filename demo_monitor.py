#!/usr/bin/env python3
"""
Demo script to show how the Reddit EarnIn Monitor works
"""

import sqlite3
import json
from datetime import datetime, timedelta

def show_database_stats():
    """Show current database statistics"""
    try:
        with sqlite3.connect("earnin_posts.db") as conn:
            cursor = conn.cursor()
            
            # Get total posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]
            
            # Get new posts (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor.execute("SELECT COUNT(*) FROM posts WHERE fetched_at > ?", (yesterday,))
            recent_posts = cursor.fetchone()[0]
            
            # Get posts by subreddit
            cursor.execute("""
                SELECT subreddit, COUNT(*) as count 
                FROM posts 
                GROUP BY subreddit 
                ORDER BY count DESC
            """)
            subreddit_stats = cursor.fetchall()
            
            # Get monitoring stats
            cursor.execute("""
                SELECT COUNT(*) as checks, 
                       SUM(posts_found) as total_found,
                       SUM(new_posts) as total_new
                FROM monitoring_stats
            """)
            monitoring_stats = cursor.fetchone()
            
            print("📊 REDDIT EARNIN MONITOR DATABASE STATISTICS")
            print("=" * 50)
            print(f"📝 Total posts in database: {total_posts}")
            print(f"🆕 Recent posts (24h): {recent_posts}")
            print(f"🔄 Monitoring checks performed: {monitoring_stats[0] or 0}")
            print(f"📈 Total posts found: {monitoring_stats[1] or 0}")
            print(f"🆕 Total new posts: {monitoring_stats[2] or 0}")
            
            if subreddit_stats:
                print(f"\n📋 Posts by subreddit:")
                for subreddit, count in subreddit_stats:
                    print(f"  r/{subreddit}: {count} posts")
            
            # Show recent posts
            cursor.execute("""
                SELECT title, subreddit, author, created_utc, fetched_at
                FROM posts 
                ORDER BY fetched_at DESC 
                LIMIT 5
            """)
            recent_posts = cursor.fetchall()
            
            if recent_posts:
                print(f"\n📰 Recent posts:")
                for i, (title, subreddit, author, created_utc, fetched_at) in enumerate(recent_posts, 1):
                    print(f"  {i}. {title[:50]}...")
                    print(f"     r/{subreddit} | u/{author}")
                    print(f"     Posted: {created_utc}")
                    print(f"     Fetched: {fetched_at}")
                    print()
            else:
                print(f"\n📰 No posts found yet. The monitor is waiting for new EarnIn-related posts...")
            
    except Exception as e:
        print(f"❌ Error reading database: {e}")

def show_monitoring_status():
    """Show current monitoring status"""
    print("🔍 REDDIT EARNIN MONITOR STATUS")
    print("=" * 40)
    
    # Check if monitor is running
    import subprocess
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'reddit_earnin_monitor.py' in result.stdout:
            print("✅ Monitor is RUNNING")
        else:
            print("❌ Monitor is NOT running")
    except:
        print("❓ Could not check monitor status")
    
    # Check log file
    try:
        with open('reddit_monitor.log', 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                print(f"📝 Last log entry: {last_line}")
    except FileNotFoundError:
        print("📝 No log file found")
    except Exception as e:
        print(f"📝 Error reading log: {e}")

def show_instructions():
    """Show usage instructions"""
    print("\n🚀 HOW TO USE THE REDDIT EARNIN MONITOR")
    print("=" * 50)
    print("1. Start the monitor:")
    print("   ./start_monitor.sh")
    print("   OR")
    print("   python3 reddit_earnin_monitor.py")
    print()
    print("2. The monitor will:")
    print("   • Check 8 EarnIn-related subreddits every minute")
    print("   • Search for 'earnin' posts across all Reddit")
    print("   • Save new posts to earnin_posts.db")
    print("   • Create JSON files for each monitoring cycle")
    print("   • Log all activities to reddit_monitor.log")
    print()
    print("3. Stop the monitor:")
    print("   Press Ctrl+C in the terminal where it's running")
    print()
    print("4. View collected data:")
    print("   • Database: sqlite3 earnin_posts.db")
    print("   • Logs: tail -f reddit_monitor.log")
    print("   • JSON files: ls earnin_posts_*.json")
    print()
    print("5. Monitor subreddits:")
    print("   • r/Earnin - Main EarnIn community")
    print("   • r/EarninB4B - Boost for Boost requests")
    print("   • r/EarninBoost - EarnIn Boost community")
    print("   • r/cashadvanceapps - Cash advance discussions")
    print("   • r/personalfinance - Financial discussions")
    print("   • r/EarningOnline - Online earning opportunities")
    print("   • r/beermoney - Side income opportunities")
    print("   • r/workonline - Online work opportunities")

if __name__ == "__main__":
    print("🔍 Reddit EarnIn Monitor Demo")
    print("=" * 30)
    
    show_monitoring_status()
    print()
    show_database_stats()
    show_instructions()
    
    print("\n" + "=" * 50)
    print("The monitor is designed to run continuously and will")
    print("automatically detect and save new EarnIn-related posts")
    print("as they appear on Reddit every minute.")
    print("=" * 50)

