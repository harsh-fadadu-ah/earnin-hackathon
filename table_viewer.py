#!/usr/bin/env python3
"""
Table Viewer for Feedback Database
Displays data in a nice table format
"""

import sqlite3
import sys
from tabulate import tabulate

def view_table(limit=None, columns=None):
    """View feedback data in table format"""
    try:
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        
        # Build query
        if columns:
            column_str = ", ".join(columns)
        else:
            column_str = "*"
        
        query = f"SELECT {column_str} FROM feedbacks"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get column names
        if columns:
            headers = columns
        else:
            headers = [description[0] for description in cursor.description]
        
        # Display table
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal rows: {len(rows)}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except ImportError:
        print("tabulate not installed. Install with: pip install tabulate")
        print("Or use the SQLite command line method instead.")

def view_summary_table():
    """View summary statistics in table format"""
    try:
        conn = sqlite3.connect('feedback.db')
        cursor = conn.cursor()
        
        # Source summary
        cursor.execute('SELECT source, COUNT(*) as count FROM feedbacks GROUP BY source ORDER BY count DESC')
        source_data = cursor.fetchall()
        
        print("📊 FEEDBACK BY SOURCE:")
        print(tabulate(source_data, headers=["Source", "Count"], tablefmt="grid"))
        
        # Category summary
        cursor.execute('SELECT category, COUNT(*) as count FROM feedbacks WHERE category IS NOT NULL GROUP BY category ORDER BY count DESC')
        category_data = cursor.fetchall()
        
        print("\n📋 FEEDBACK BY CATEGORY:")
        print(tabulate(category_data, headers=["Category", "Count"], tablefmt="grid"))
        
        # Sentiment summary
        cursor.execute('SELECT sentiment, COUNT(*) as count FROM feedbacks WHERE sentiment IS NOT NULL GROUP BY sentiment ORDER BY count DESC')
        sentiment_data = cursor.fetchall()
        
        print("\n😊 FEEDBACK BY SENTIMENT:")
        print(tabulate(sentiment_data, headers=["Sentiment", "Count"], tablefmt="grid"))
        
        # Severity summary
        cursor.execute('SELECT severity, COUNT(*) as count FROM feedbacks WHERE severity IS NOT NULL GROUP BY severity ORDER BY count DESC')
        severity_data = cursor.fetchall()
        
        print("\n⚠️ FEEDBACK BY SEVERITY:")
        print(tabulate(severity_data, headers=["Severity", "Count"], tablefmt="grid"))
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except ImportError:
        print("tabulate not installed. Install with: pip install tabulate")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "summary":
            view_summary_table()
        elif sys.argv[1] == "recent":
            view_table(limit=10, columns=["id", "source", "content", "author", "rating", "category", "sentiment", "severity"])
        else:
            try:
                limit = int(sys.argv[1])
                view_table(limit=limit)
            except ValueError:
                print("Usage: python3 table_viewer.py [number|summary|recent]")
    else:
        view_table(limit=20)
        
    print(f'\n💡 USAGE:')
    print(f'  python3 table_viewer.py              # View first 20 rows')
    print(f'  python3 table_viewer.py 50           # View first 50 rows')
    print(f'  python3 table_viewer.py summary      # View summary tables')
    print(f'  python3 table_viewer.py recent       # View recent feedback')
