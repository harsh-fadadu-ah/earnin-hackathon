#!/usr/bin/env python3
"""
Unified Messages Database Viewer

A comprehensive tool to view, search, and analyze messages from the unified database.
Provides both command-line interface and interactive exploration capabilities.
"""

import sqlite3
import json
import argparse
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import os

class UnifiedDatabaseViewer:
    """Viewer for the unified messages database"""
    
    def __init__(self, db_path: str = "unified_messages.db"):
        self.db_path = db_path
        if not os.path.exists(db_path):
            print(f"❌ Database {db_path} not found!")
            print("Please run create_unified_database.py first to create the unified database")
            sys.exit(1)
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Messages by source
            cursor.execute("SELECT source, COUNT(*) FROM messages GROUP BY source ORDER BY COUNT(*) DESC")
            by_source = dict(cursor.fetchall())
            
            # Messages by platform
            cursor.execute("SELECT platform, COUNT(*) FROM messages GROUP BY platform ORDER BY COUNT(*) DESC")
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
            
            # Messages by subreddit (for Reddit messages)
            cursor.execute("""
                SELECT subreddit, COUNT(*) FROM messages 
                WHERE source = 'reddit' AND subreddit IS NOT NULL 
                GROUP BY subreddit ORDER BY COUNT(*) DESC
            """)
            by_subreddit = dict(cursor.fetchall())
            
            # Messages by channel (for Slack messages)
            cursor.execute("""
                SELECT channel_name, COUNT(*) FROM messages 
                WHERE source = 'slack' AND channel_name IS NOT NULL 
                GROUP BY channel_name ORDER BY COUNT(*) DESC
            """)
            by_channel = dict(cursor.fetchall())
            
            return {
                'total_messages': total_messages,
                'by_source': by_source,
                'by_platform': by_platform,
                'by_sentiment': by_sentiment,
                'by_category': by_category,
                'by_processed': by_processed,
                'recent_messages_24h': recent_messages,
                'by_subreddit': by_subreddit,
                'by_channel': by_channel,
                'database_path': self.db_path,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
    
    def search_messages(self, query: str = None, source: str = None, platform: str = None, 
                       sentiment: str = None, category: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search messages with various filters"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build query
            where_conditions = []
            params = []
            
            if query:
                where_conditions.append("(content LIKE ? OR title LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])
            
            if source:
                where_conditions.append("source = ?")
                params.append(source)
            
            if platform:
                where_conditions.append("platform = ?")
                params.append(platform)
            
            if sentiment:
                where_conditions.append("sentiment = ?")
                params.append(sentiment)
            
            if category:
                where_conditions.append("category = ?")
                params.append(category)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            sql = f"""
                SELECT id, source, platform, content, title, author, timestamp, url, 
                       subreddit, channel_name, score, rating, sentiment, category, 
                       severity, business_impact_score, processed, created_at
                FROM messages 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            messages = []
            for row in rows:
                messages.append({
                    'id': row[0],
                    'source': row[1],
                    'platform': row[2],
                    'content': row[3],
                    'title': row[4],
                    'author': row[5],
                    'timestamp': row[6],
                    'url': row[7],
                    'subreddit': row[8],
                    'channel_name': row[9],
                    'score': row[10],
                    'rating': row[11],
                    'sentiment': row[12],
                    'category': row[13],
                    'severity': row[14],
                    'business_impact_score': row[15],
                    'processed': bool(row[16]),
                    'created_at': row[17]
                })
            
            return messages
    
    def get_message_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Get column names
            cursor.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Create dictionary from row
            message_dict = dict(zip(columns, row))
            
            # Parse JSON fields
            if message_dict.get('raw_data'):
                try:
                    message_dict['raw_data'] = json.loads(message_dict['raw_data'])
                except:
                    pass
            
            if message_dict.get('tags'):
                try:
                    message_dict['tags'] = json.loads(message_dict['tags'])
                except:
                    pass
            
            if message_dict.get('hashtags'):
                try:
                    message_dict['hashtags'] = json.loads(message_dict['hashtags'])
                except:
                    pass
            
            if message_dict.get('mentions'):
                try:
                    message_dict['mentions'] = json.loads(message_dict['mentions'])
                except:
                    pass
            
            return message_dict
    
    def get_recent_messages(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages from the last N hours"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, source, platform, content, title, author, timestamp, 
                       subreddit, channel_name, sentiment, category, processed
                FROM messages 
                WHERE datetime(timestamp) > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
                LIMIT ?
            """.format(hours), (limit,))
            
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    'id': row[0],
                    'source': row[1],
                    'platform': row[2],
                    'content': row[3][:100] + '...' if len(row[3]) > 100 else row[3],
                    'title': row[4],
                    'author': row[5],
                    'timestamp': row[6],
                    'subreddit': row[7],
                    'channel_name': row[8],
                    'sentiment': row[9],
                    'category': row[10],
                    'processed': bool(row[11])
                })
            
            return messages
    
    def export_to_json(self, output_file: str, source: str = None, limit: int = None):
        """Export messages to JSON file"""
        messages = self.search_messages(source=source, limit=limit or 1000)
        
        export_data = {
            'export_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_messages': len(messages),
            'filters': {
                'source': source,
                'limit': limit
            },
            'messages': messages
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(messages)} messages to {output_file}")
    
    def print_stats(self):
        """Print database statistics in a formatted way"""
        stats = self.get_database_stats()
        
        print("📊 UNIFIED MESSAGES DATABASE STATISTICS")
        print("=" * 50)
        print(f"📁 Database: {stats['database_path']}")
        print(f"📅 Last Updated: {stats['last_updated']}")
        print()
        
        print(f"📈 TOTAL MESSAGES: {stats['total_messages']}")
        print(f"🕐 Recent (24h): {stats['recent_messages_24h']}")
        print()
        
        print("📊 BY SOURCE:")
        for source, count in stats['by_source'].items():
            print(f"   {source}: {count}")
        print()
        
        print("🖥️  BY PLATFORM:")
        for platform, count in stats['by_platform'].items():
            print(f"   {platform}: {count}")
        print()
        
        if stats['by_sentiment']:
            print("😊 BY SENTIMENT:")
            for sentiment, count in stats['by_sentiment'].items():
                print(f"   {sentiment}: {count}")
            print()
        
        if stats['by_category']:
            print("🏷️  BY CATEGORY:")
            for category, count in stats['by_category'].items():
                print(f"   {category}: {count}")
            print()
        
        print("⚙️  PROCESSING STATUS:")
        processed = stats['by_processed'].get(1, 0)
        unprocessed = stats['by_processed'].get(0, 0)
        print(f"   Processed: {processed}")
        print(f"   Unprocessed: {unprocessed}")
        print()
        
        if stats['by_subreddit']:
            print("🔴 REDDIT SUBREDDITS:")
            for subreddit, count in stats['by_subreddit'].items():
                print(f"   r/{subreddit}: {count}")
            print()
        
        if stats['by_channel']:
            print("💬 SLACK CHANNELS:")
            for channel, count in stats['by_channel'].items():
                print(f"   #{channel}: {count}")
            print()
    
    def print_messages(self, messages: List[Dict[str, Any]], detailed: bool = False):
        """Print messages in a formatted way"""
        if not messages:
            print("No messages found.")
            return
        
        print(f"📋 FOUND {len(messages)} MESSAGES")
        print("=" * 50)
        
        for i, msg in enumerate(messages, 1):
            print(f"\n{i}. ID: {msg['id']}")
            print(f"   Source: {msg['source']} | Platform: {msg['platform']}")
            print(f"   Author: {msg['author']}")
            print(f"   Timestamp: {msg['timestamp']}")
            
            if msg.get('title'):
                print(f"   Title: {msg['title']}")
            
            content = msg['content']
            if not detailed and len(content) > 200:
                content = content[:200] + "..."
            print(f"   Content: {content}")
            
            if msg.get('subreddit'):
                print(f"   Subreddit: r/{msg['subreddit']}")
            
            if msg.get('channel_name'):
                print(f"   Channel: #{msg['channel_name']}")
            
            if msg.get('score') is not None:
                print(f"   Score: {msg['score']}")
            
            if msg.get('rating') is not None:
                print(f"   Rating: {msg['rating']}/5")
            
            if msg.get('sentiment'):
                print(f"   Sentiment: {msg['sentiment']}")
            
            if msg.get('category'):
                print(f"   Category: {msg['category']}")
            
            if msg.get('severity'):
                print(f"   Severity: {msg['severity']}")
            
            if msg.get('business_impact_score') is not None:
                print(f"   Business Impact: {msg['business_impact_score']:.2f}")
            
            print(f"   Processed: {'✅' if msg.get('processed') else '❌'}")
            
            if msg.get('url'):
                print(f"   URL: {msg['url']}")
            
            if i < len(messages):
                print("-" * 30)

def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description="Unified Messages Database Viewer")
    parser.add_argument("--db", default="unified_messages.db", help="Database file path")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--recent", type=int, metavar="HOURS", help="Show recent messages from last N hours")
    parser.add_argument("--search", metavar="QUERY", help="Search messages by content")
    parser.add_argument("--source", help="Filter by source (reddit, slack, app_store, play_store, twitter)")
    parser.add_argument("--platform", help="Filter by platform")
    parser.add_argument("--sentiment", help="Filter by sentiment (positive, negative, neutral)")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of results")
    parser.add_argument("--detailed", action="store_true", help="Show detailed message information")
    parser.add_argument("--export", metavar="FILE", help="Export messages to JSON file")
    parser.add_argument("--message-id", help="Get detailed information about a specific message")
    
    args = parser.parse_args()
    
    viewer = UnifiedDatabaseViewer(args.db)
    
    if args.stats:
        viewer.print_stats()
    
    elif args.message_id:
        message = viewer.get_message_details(args.message_id)
        if message:
            print("📄 MESSAGE DETAILS")
            print("=" * 50)
            print(json.dumps(message, indent=2, default=str))
        else:
            print(f"❌ Message {args.message_id} not found")
    
    elif args.recent:
        messages = viewer.get_recent_messages(args.recent, args.limit)
        viewer.print_messages(messages, args.detailed)
    
    elif args.export:
        viewer.export_to_json(args.export, args.source, args.limit)
    
    else:
        # Search messages
        messages = viewer.search_messages(
            query=args.search,
            source=args.source,
            platform=args.platform,
            sentiment=args.sentiment,
            category=args.category,
            limit=args.limit
        )
        viewer.print_messages(messages, args.detailed)

if __name__ == "__main__":
    main()
