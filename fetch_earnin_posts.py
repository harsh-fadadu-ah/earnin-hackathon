#!/usr/bin/env python3
"""
Fetch all new posts from subreddits related to "earnin"
"""

import praw
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

def fetch_earnin_posts():
    """Fetch all new posts from subreddits related to 'earnin'"""
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id="k3n3Jc9hKlpm0OBC9f5VoA",
        client_secret="GM2yWaXXS7-SCwMq5KUpARLh2bqg2A",
        user_agent="FeedForward",
        username="Best_Mirror2588",
        password="Harsh_password"
    )
    
    # Subreddits related to "earnin" (from our search results)
    earnin_subreddits = [
        "Earnin",           # Main EarnIn subreddit
        "EarninB4B",        # EarnIn Boost for Boost
        "EarninBoost",      # EarnIn Boost
        "cashadvanceapps",  # Cash advance apps
        "personalfinance",  # Personal finance (has EarnIn discussions)
        "EarningOnline",    # Earning online
        "beermoney",        # Beer money
        "workonline"        # Work online
    ]
    
    all_posts = []
    subreddit_stats = {}
    
    print("🚀 Fetching new posts from EarnIn-related subreddits...")
    print("=" * 60)
    
    for subreddit_name in earnin_subreddits:
        try:
            print(f"\n📋 Checking r/{subreddit_name}...")
            subreddit = reddit.subreddit(subreddit_name)
            
            # Get subreddit info
            subreddit_info = {
                "name": subreddit.display_name,
                "title": subreddit.title,
                "subscribers": subreddit.subscribers,
                "description": subreddit.description[:200] if subreddit.description else "No description"
            }
            
            # Get new posts (last 24 hours)
            posts = []
            cutoff_time = datetime.now() - timedelta(days=1)
            
            for submission in subreddit.new(limit=50):
                post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                
                # Only include posts from the last 24 hours
                if post_time >= cutoff_time:
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
                        "domain": submission.domain
                    }
                    posts.append(post_data)
            
            subreddit_stats[subreddit_name] = {
                "info": subreddit_info,
                "new_posts_count": len(posts),
                "posts": posts
            }
            
            all_posts.extend(posts)
            
            print(f"  ✅ Found {len(posts)} new posts in r/{subreddit_name}")
            
        except Exception as e:
            print(f"  ❌ Error fetching from r/{subreddit_name}: {e}")
            subreddit_stats[subreddit_name] = {
                "error": str(e),
                "new_posts_count": 0,
                "posts": []
            }
    
    # Also search for posts containing "earnin" across all subreddits
    print(f"\n🔍 Searching for posts containing 'earnin' across all subreddits...")
    try:
        search_posts = []
        for submission in reddit.subreddit("all").search("earnin", sort="new", limit=25):
            post_time = datetime.fromtimestamp(submission.created_utc)
            cutoff_time = datetime.now() - timedelta(days=1)
            
            # Only include recent posts
            if post_time >= cutoff_time:
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
                    "domain": submission.domain
                }
                search_posts.append(post_data)
        
        subreddit_stats["search_results"] = {
            "query": "earnin",
            "new_posts_count": len(search_posts),
            "posts": search_posts
        }
        
        all_posts.extend(search_posts)
        print(f"  ✅ Found {len(search_posts)} new posts containing 'earnin'")
        
    except Exception as e:
        print(f"  ❌ Error searching for 'earnin' posts: {e}")
        subreddit_stats["search_results"] = {
            "error": str(e),
            "new_posts_count": 0,
            "posts": []
        }
    
    # Remove duplicates based on post ID
    unique_posts = {}
    for post in all_posts:
        unique_posts[post["id"]] = post
    
    final_posts = list(unique_posts.values())
    
    # Sort by creation time (newest first)
    final_posts.sort(key=lambda x: x["created_utc"], reverse=True)
    
    # Create summary
    summary = {
        "fetch_timestamp": datetime.now().isoformat(),
        "total_unique_posts": len(final_posts),
        "subreddits_checked": len(earnin_subreddits),
        "subreddit_stats": subreddit_stats,
        "posts": final_posts
    }
    
    # Save to JSON file
    output_file = "earnin_posts.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Summary:")
    print(f"  Total unique posts found: {len(final_posts)}")
    print(f"  Subreddits checked: {len(earnin_subreddits)}")
    print(f"  Data saved to: {output_file}")
    
    # Display recent posts
    print(f"\n📰 Recent EarnIn-related posts:")
    print("-" * 60)
    
    for i, post in enumerate(final_posts[:10], 1):
        print(f"{i}. {post['title'][:80]}...")
        print(f"   r/{post['subreddit']} | u/{post['author']} | {post['score']} points | {post['num_comments']} comments")
        print(f"   Created: {post['created_utc']}")
        print(f"   URL: {post['permalink']}")
        if post['content']:
            print(f"   Content: {post['content'][:100]}...")
        print()
    
    return summary

if __name__ == "__main__":
    print("🚀 Fetching all new EarnIn-related posts from Reddit...")
    print("=" * 60)
    
    try:
        results = fetch_earnin_posts()
        print("\n✅ Successfully fetched EarnIn-related posts!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

