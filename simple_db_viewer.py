#!/usr/bin/env python3
"""
Simple Database Viewer
A lightweight script to view feedback database without external dependencies
"""

import sqlite3
import json
from datetime import datetime

def view_database():
    """View the feedback database contents"""
    print('📊 FEEDBACK DATABASE VIEWER')
    print('=' * 60)
    
    try:
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        
        # Get table information
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'\n📋 TABLES: {[table[0] for table in tables]}')
        
        # Get total counts
        cursor.execute('SELECT COUNT(*) FROM feedbacks')
        total_feedback = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM feedbacks WHERE processed = 1')
        processed_feedback = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM authors')
        total_authors = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM threads')
        total_threads = cursor.fetchone()[0]
        
        print(f'\n📈 SUMMARY:')
        print(f'  Total Feedback: {total_feedback}')
        print(f'  Processed: {processed_feedback}')
        print(f'  Unprocessed: {total_feedback - processed_feedback}')
        print(f'  Authors: {total_authors}')
        print(f'  Threads: {total_threads}')
        
        # Source breakdown
        cursor.execute('SELECT source, COUNT(*) FROM feedbacks GROUP BY source ORDER BY COUNT(*) DESC')
        source_counts = cursor.fetchall()
        
        print(f'\n📊 BY SOURCE:')
        for source, count in source_counts:
            print(f'  {source.replace("_", " ").title()}: {count}')
        
        # Category breakdown
        cursor.execute('SELECT category, COUNT(*) FROM feedbacks WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC')
        category_counts = cursor.fetchall()
        
        if category_counts:
            print(f'\n📋 BY CATEGORY:')
            for category, count in category_counts:
                print(f'  {category.replace("_", " ").title()}: {count}')
        
        # Sentiment breakdown
        cursor.execute('SELECT sentiment, COUNT(*) FROM feedbacks WHERE sentiment IS NOT NULL GROUP BY sentiment ORDER BY COUNT(*) DESC')
        sentiment_counts = cursor.fetchall()
        
        if sentiment_counts:
            print(f'\n😊 BY SENTIMENT:')
            for sentiment, count in sentiment_counts:
                print(f'  {sentiment.title()}: {count}')
        
        # Severity breakdown
        cursor.execute('SELECT severity, COUNT(*) FROM feedbacks WHERE severity IS NOT NULL GROUP BY severity ORDER BY COUNT(*) DESC')
        severity_counts = cursor.fetchall()
        
        if severity_counts:
            print(f'\n⚠️ BY SEVERITY:')
            for severity, count in severity_counts:
                print(f'  {severity.title()}: {count}')
        
        # Recent feedback
        cursor.execute('SELECT id, source, content, author, rating, category, sentiment, severity, processed, created_at FROM feedbacks ORDER BY created_at DESC LIMIT 10')
        recent_feedback = cursor.fetchall()
        
        print(f'\n📝 RECENT FEEDBACK (Last 10):')
        print('-' * 80)
        for i, row in enumerate(recent_feedback, 1):
            feedback_id, source, content, author, rating, category, sentiment, severity, processed, created_at = row
            
            print(f'\n{i}. {source.replace("_", " ").title()} Review')
            print(f'   ID: {feedback_id}')
            print(f'   Content: {content[:80]}...' if len(content) > 80 else f'   Content: {content}')
            print(f'   Author: {author}')
            print(f'   Rating: {rating} stars' if rating else '   Rating: N/A')
            print(f'   Category: {category or "Not classified"}')
            print(f'   Sentiment: {sentiment or "Not analyzed"}')
            print(f'   Severity: {severity or "Not assessed"}')
            print(f'   Processed: {"✅ Yes" if processed else "❌ No"}')
            print(f'   Date: {created_at[:19]}')
        
        # Show some sample authors
        cursor.execute('SELECT id, username, email, platform, reputation_score FROM authors LIMIT 5')
        authors = cursor.fetchall()
        
        if authors:
            print(f'\n👥 SAMPLE AUTHORS:')
            print('-' * 40)
            for author in authors:
                author_id, username, email, platform, reputation = author
                print(f'  {username or "Unknown"} ({platform or "Unknown"})')
                print(f'    ID: {author_id}')
                print(f'    Email: {email or "N/A"}')
                print(f'    Reputation: {reputation or "N/A"}')
                print()
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def view_specific_feedback(feedback_id=None):
    """View specific feedback by ID"""
    if not feedback_id:
        print("Please provide a feedback ID")
        return
    
    try:
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM feedbacks WHERE id = ?', (feedback_id,))
        feedback = cursor.fetchone()
        
        if feedback:
            print(f'\n📝 FEEDBACK DETAILS: {feedback_id}')
            print('-' * 50)
            print(f'ID: {feedback[0]}')
            print(f'Source: {feedback[1]}')
            print(f'Content: {feedback[2]}')
            print(f'Author: {feedback[3]}')
            print(f'Timestamp: {feedback[4]}')
            print(f'URL: {feedback[5] or "N/A"}')
            print(f'Rating: {feedback[6] or "N/A"}')
            print(f'Language: {feedback[7] or "N/A"}')
            print(f'Category: {feedback[8] or "N/A"}')
            print(f'Sentiment: {feedback[9] or "N/A"}')
            print(f'Severity: {feedback[10] or "N/A"}')
            print(f'Business Impact: {feedback[11] or "N/A"}')
            print(f'PII Detected: {feedback[12]}')
            print(f'Processed: {feedback[13]}')
            print(f'Created: {feedback[14]}')
            print(f'Updated: {feedback[15]}')
        else:
            print(f"Feedback with ID '{feedback_id}' not found")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # View specific feedback
        feedback_id = sys.argv[1]
        view_specific_feedback(feedback_id)
    else:
        # View all database
        view_database()
        
    print(f'\n💡 USAGE:')
    print(f'  python3 simple_db_viewer.py              # View all data')
    print(f'  python3 simple_db_viewer.py <feedback_id> # View specific feedback')
