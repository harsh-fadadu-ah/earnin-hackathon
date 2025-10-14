#!/usr/bin/env python3
"""
Feedback Results Viewer
A simple script to view feedback processing results
"""

import sqlite3
import json
from datetime import datetime
from feedback_mcp_server import db, get_metrics

def view_feedback_results():
    """Display feedback processing results"""
    print('📊 FEEDBACK MANAGEMENT RESULTS')
    print('=' * 60)
    
    # Get database statistics
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    
    # Total counts
    cursor.execute('SELECT COUNT(*) FROM feedbacks')
    total_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM feedbacks WHERE processed = 1')
    processed_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM feedbacks WHERE processed = 0')
    unprocessed_count = cursor.fetchone()[0]
    
    # Source breakdown
    cursor.execute('SELECT source, COUNT(*) FROM feedbacks GROUP BY source')
    source_counts = cursor.fetchall()
    
    # Category breakdown
    cursor.execute('SELECT category, COUNT(*) FROM feedbacks WHERE category IS NOT NULL GROUP BY category')
    category_counts = cursor.fetchall()
    
    # Sentiment breakdown
    cursor.execute('SELECT sentiment, COUNT(*) FROM feedbacks WHERE sentiment IS NOT NULL GROUP BY sentiment')
    sentiment_counts = cursor.fetchall()
    
    # Severity breakdown
    cursor.execute('SELECT severity, COUNT(*) FROM feedbacks WHERE severity IS NOT NULL GROUP BY severity')
    severity_counts = cursor.fetchall()
    
    # Recent feedback
    cursor.execute('SELECT * FROM feedbacks ORDER BY created_at DESC LIMIT 5')
    recent_feedback = cursor.fetchall()
    
    conn.close()
    
    # Display results
    print(f'\\n📈 SUMMARY STATISTICS:')
    print(f'Total Feedback: {total_count}')
    print(f'Processed: {processed_count}')
    print(f'Unprocessed: {unprocessed_count}')
    print(f'Processing Rate: {(processed_count/total_count*100):.1f}%' if total_count > 0 else 'Processing Rate: 0%')
    
    print(f'\\n📊 BY SOURCE:')
    for source, count in source_counts:
        print(f'  {source.replace("_", " ").title()}: {count}')
    
    print(f'\\n📋 BY CATEGORY:')
    for category, count in category_counts:
        print(f'  {category.replace("_", " ").title()}: {count}')
    
    print(f'\\n😊 BY SENTIMENT:')
    for sentiment, count in sentiment_counts:
        print(f'  {sentiment.title()}: {count}')
    
    print(f'\\n⚠️ BY SEVERITY:')
    for severity, count in severity_counts:
        print(f'  {severity.title()}: {count}')
    
    print(f'\\n📝 RECENT FEEDBACK (Last 5):')
    print('-' * 80)
    for i, row in enumerate(recent_feedback, 1):
        feedback_id, source, content, author, timestamp, url, rating, language, category, sentiment, severity, business_impact_score, pii_detected, processed, created_at, updated_at = row
        
        print(f'\\n{i}. {source.replace("_", " ").title()} Review')
        print(f'   Content: {content[:100]}...')
        print(f'   Rating: {rating} stars' if rating else '   Rating: N/A')
        print(f'   Category: {category or "Not classified"}')
        print(f'   Sentiment: {sentiment or "Not analyzed"}')
        print(f'   Severity: {severity or "Not assessed"}')
        print(f'   Impact Score: {business_impact_score:.2f}' if business_impact_score else '   Impact Score: N/A')
        print(f'   Processed: {"✅ Yes" if processed else "❌ No"}')
        print(f'   Date: {created_at[:19]}')
    
    # Get system metrics
    print(f'\\n🎯 SYSTEM METRICS:')
    try:
        result = get_metrics({'timeframe': 'week'})
        metrics = json.loads(result.content[0].text.split('Metrics for week: ')[1])
        print(f'   Total Feedback: {metrics["total_feedback"]}')
        print(f'   Processed: {metrics["processed_feedback"]}')
        print(f'   Pending: {metrics["pending_feedback"]}')
        print(f'   Avg Sentiment: {metrics["avg_sentiment"]}')
        print(f'   Top Categories: {", ".join(metrics["top_categories"])}')
        print(f'   Response Time: {metrics["response_time_avg"]}')
        print(f'   Resolution Rate: {metrics["resolution_rate"]}')
    except Exception as e:
        print(f'   Error getting metrics: {e}')

def view_unprocessed_feedback():
    """View unprocessed feedback"""
    print('\\n🔄 UNPROCESSED FEEDBACK:')
    print('-' * 40)
    
    unprocessed = db.get_unprocessed_feedback()
    
    if not unprocessed:
        print('✅ No unprocessed feedback!')
        return
    
    for i, feedback in enumerate(unprocessed, 1):
        print(f'\\n{i}. ID: {feedback.id}')
        print(f'   Source: {feedback.source.value}')
        print(f'   Content: {feedback.content[:100]}...')
        print(f'   Author: {feedback.author}')
        print(f'   Rating: {feedback.rating} stars' if feedback.rating else '   Rating: N/A')
        print(f'   Created: {feedback.created_at}')

if __name__ == '__main__':
    view_feedback_results()
    view_unprocessed_feedback()
    
    print(f'\\n🚀 To run the MCP server: python3.11 feedback_mcp_server.py')
    print(f'📊 To view results again: python3.11 view_results.py')
    print(f'🧪 To run tests: python3.11 test_server.py')
