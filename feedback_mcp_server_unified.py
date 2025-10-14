#!/usr/bin/env python3
"""
Feedback Management MCP Server - Unified Database Version

A comprehensive MCP server for collecting, processing, and managing feedback
from multiple sources using the unified messages database.
"""

import asyncio
import json
import logging
import re
import uuid
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import httpx
import sqlite3
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListResourcesRequest, ListResourcesResult,
    ReadResourceRequest, ReadResourceResult
)

# Slack integration
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    import ssl
    import certifi
    
    # Configure SSL context to use certifi certificates and disable verification if needed
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    WebClient = None
    SlackApiError = Exception
    ssl_context = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("feedback-management-unified")

# Constants
JSON_MIME_TYPE = "application/json"

# Unified database setup
UNIFIED_DB_PATH = "unified_messages.db"

class FeedbackSource(Enum):
    APP_STORE = "app_store"
    PLAY_STORE = "play_store"
    REDDIT = "reddit"
    TWITTER = "twitter"
    EMAIL = "email"
    WEB = "web"
    SLACK = "slack"
    OTHER = "other"

class FeedbackCategory(Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    QUESTION = "question"
    SPAM = "spam"
    OTHER = "other"

class Sentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Feedback:
    id: str
    source: FeedbackSource
    content: str
    author: str
    timestamp: datetime
    url: Optional[str] = None
    rating: Optional[int] = None
    language: Optional[str] = None
    category: Optional[FeedbackCategory] = None
    sentiment: Optional[Sentiment] = None
    severity: Optional[Severity] = None
    business_impact_score: Optional[float] = None
    pii_detected: bool = False
    processed: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

class UnifiedFeedbackDatabase:
    """Unified database interface for feedback management"""
    
    def __init__(self, db_path: str = UNIFIED_DB_PATH):
        self.db_path = db_path
        if not os.path.exists(db_path):
            logger.error(f"Unified database {db_path} not found!")
            logger.info("Please run create_unified_database.py first to create the unified database")
            raise FileNotFoundError(f"Unified database {db_path} not found")
    
    def save_feedback(self, feedback: Feedback) -> bool:
        """Save feedback to unified database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if feedback already exists
                cursor.execute("SELECT id FROM messages WHERE id = ?", (feedback.id,))
                if cursor.fetchone():
                    # Update existing feedback
                    cursor.execute("""
                        UPDATE messages SET
                        content = ?, author = ?, timestamp = ?, url = ?, rating = ?,
                        language = ?, sentiment = ?, category = ?, severity = ?,
                        business_impact_score = ?, pii_detected = ?, processed = ?,
                        updated_at = ?
                        WHERE id = ?
                    """, (
                        feedback.content, feedback.author, feedback.timestamp.isoformat(),
                        feedback.url, feedback.rating, feedback.language,
                        feedback.sentiment.value if feedback.sentiment else None,
                        feedback.category.value if feedback.category else None,
                        feedback.severity.value if feedback.severity else None,
                        feedback.business_impact_score, feedback.pii_detected,
                        feedback.processed, feedback.updated_at.isoformat(), feedback.id
                    ))
                else:
                    # Insert new feedback
                    cursor.execute("""
                        INSERT INTO messages 
                        (id, source, platform, content, author, author_id, timestamp, url, rating,
                         language, sentiment, category, severity, business_impact_score,
                         pii_detected, processed, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        feedback.id, feedback.source.value, self._map_source_to_platform(feedback.source.value),
                        feedback.content, feedback.author, feedback.author, feedback.timestamp.isoformat(),
                        feedback.url, feedback.rating, feedback.language,
                        feedback.sentiment.value if feedback.sentiment else None,
                        feedback.category.value if feedback.category else None,
                        feedback.severity.value if feedback.severity else None,
                        feedback.business_impact_score, feedback.pii_detected,
                        feedback.processed, feedback.created_at.isoformat(), feedback.updated_at.isoformat()
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False
    
    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """Get feedback by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM messages WHERE id = ?", (feedback_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_feedback(row)
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
        return None
    
    def get_unprocessed_feedback(self) -> List[Feedback]:
        """Get all unprocessed feedback"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM messages WHERE processed = FALSE ORDER BY created_at ASC")
                rows = cursor.fetchall()
                return [self._row_to_feedback(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting unprocessed feedback: {e}")
            return []
    
    def get_feedback_by_source(self, source: str) -> List[Feedback]:
        """Get feedback by source"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM messages WHERE source = ? ORDER BY created_at DESC", (source,))
                rows = cursor.fetchall()
                return [self._row_to_feedback(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting feedback by source: {e}")
            return []
    
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
    
    def _row_to_feedback(self, row) -> Feedback:
        """Convert database row to Feedback object"""
        # Get column names
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            columns = [column[1] for column in cursor.fetchall()]
        
        # Create dictionary from row
        row_dict = dict(zip(columns, row))
        
        return Feedback(
            id=row_dict['id'],
            source=FeedbackSource(row_dict['source']),
            content=row_dict['content'],
            author=row_dict['author'],
            timestamp=datetime.fromisoformat(row_dict['timestamp']),
            url=row_dict.get('url'),
            rating=row_dict.get('rating'),
            language=row_dict.get('language'),
            category=FeedbackCategory(row_dict['category']) if row_dict.get('category') else None,
            sentiment=Sentiment(row_dict['sentiment']) if row_dict.get('sentiment') else None,
            severity=Severity(row_dict['severity']) if row_dict.get('severity') else None,
            business_impact_score=row_dict.get('business_impact_score'),
            pii_detected=bool(row_dict.get('pii_detected', False)),
            processed=bool(row_dict.get('processed', False)),
            created_at=datetime.fromisoformat(row_dict['created_at']),
            updated_at=datetime.fromisoformat(row_dict['updated_at'])
        )

# Initialize unified database
db = UnifiedFeedbackDatabase()

class FeedbackNormalizer:
    """Normalize and clean feedback data"""
    
    @staticmethod
    def normalize_feedback(feedback: Feedback) -> Feedback:
        """Normalize feedback content and metadata"""
        # Clean content
        feedback.content = FeedbackNormalizer._clean_content(feedback.content)
        
        # Detect language
        feedback.language = FeedbackNormalizer._detect_language(feedback.content)
        
        # Detect PII
        feedback.pii_detected = FeedbackNormalizer._detect_pii(feedback.content)
        
        # Strip PII if detected
        if feedback.pii_detected:
            feedback.content = FeedbackNormalizer._strip_pii(feedback.content)
        
        return feedback
    
    @staticmethod
    def _clean_content(content: str) -> str:
        """Clean and normalize content"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content.strip())
        # Remove special characters that might cause issues
        content = re.sub(r'[^\w\s\.\,\!\?\-\@\#]', '', content)
        return content
    
    @staticmethod
    def _detect_language(content: str) -> str:
        """Simple language detection (in production, use a proper library)"""
        # Basic English detection
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        words = content.lower().split()
        english_count = sum(1 for word in words if word in english_words)
        
        if english_count > len(words) * 0.1:
            return 'en'
        return 'unknown'
    
    @staticmethod
    def _detect_pii(content: str) -> bool:
        """Detect personally identifiable information"""
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        # Phone pattern
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        # Credit card pattern
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        
        return bool(re.search(email_pattern, content) or 
                   re.search(phone_pattern, content) or 
                   re.search(cc_pattern, content))
    
    @staticmethod
    def _strip_pii(content: str) -> str:
        """Strip PII from content"""
        # Replace email addresses
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', content)
        # Replace phone numbers
        content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', content)
        # Replace credit card numbers
        content = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', content)
        return content

class FeedbackClassifier:
    """Classify feedback into categories, sentiment, and severity"""
    
    def __init__(self):
        # Simple keyword-based classification (in production, use ML models)
        self.category_keywords = {
            FeedbackCategory.BUG: ['bug', 'error', 'crash', 'broken', 'not working', 'issue', 'problem'],
            FeedbackCategory.FEATURE_REQUEST: ['feature', 'add', 'want', 'need', 'suggest', 'request'],
            FeedbackCategory.COMPLAINT: ['hate', 'terrible', 'awful', 'worst', 'disappointed', 'angry'],
            FeedbackCategory.PRAISE: ['love', 'great', 'awesome', 'amazing', 'excellent', 'perfect'],
            FeedbackCategory.QUESTION: ['how', 'what', 'why', 'when', 'where', '?'],
            FeedbackCategory.SPAM: ['buy', 'sell', 'promo', 'discount', 'click here']
        }
        
        self.sentiment_keywords = {
            Sentiment.POSITIVE: ['good', 'great', 'awesome', 'love', 'amazing', 'excellent', 'perfect', 'wonderful'],
            Sentiment.NEGATIVE: ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointed', 'angry']
        }
    
    def classify_feedback(self, feedback: Feedback) -> Feedback:
        """Classify feedback into category, sentiment, and severity"""
        content_lower = feedback.content.lower()
        
        # Classify category
        feedback.category = self._classify_category(content_lower)
        
        # Classify sentiment
        feedback.sentiment = self._classify_sentiment(content_lower)
        
        # Determine severity
        feedback.severity = self._classify_severity(feedback)
        
        return feedback
    
    def _classify_category(self, content: str) -> FeedbackCategory:
        """Classify feedback category"""
        for category, keywords in self.category_keywords.items():
            if any(keyword in content for keyword in keywords):
                return category
        return FeedbackCategory.OTHER
    
    def _classify_sentiment(self, content: str) -> Sentiment:
        """Classify sentiment"""
        positive_count = sum(1 for word in self.sentiment_keywords[Sentiment.POSITIVE] if word in content)
        negative_count = sum(1 for word in self.sentiment_keywords[Sentiment.NEGATIVE] if word in content)
        
        if positive_count > negative_count:
            return Sentiment.POSITIVE
        elif negative_count > positive_count:
            return Sentiment.NEGATIVE
        else:
            return Sentiment.NEUTRAL
    
    def _classify_severity(self, feedback: Feedback) -> Severity:
        """Determine severity based on multiple factors"""
        severity_score = 0
        
        # Rating-based severity (for app store reviews)
        if feedback.rating is not None:
            if feedback.rating <= 2:
                severity_score += 3
            elif feedback.rating == 3:
                severity_score += 1
        
        # Sentiment-based severity
        if feedback.sentiment == Sentiment.NEGATIVE:
            severity_score += 2
        elif feedback.sentiment == Sentiment.POSITIVE:
            severity_score -= 1
        
        # Category-based severity
        if feedback.category == FeedbackCategory.BUG:
            severity_score += 2
        elif feedback.category == FeedbackCategory.COMPLAINT:
            severity_score += 1
        
        # PII detection increases severity
        if feedback.pii_detected:
            severity_score += 1
        
        # Map score to severity
        if severity_score >= 4:
            return Severity.CRITICAL
        elif severity_score >= 2:
            return Severity.HIGH
        elif severity_score >= 1:
            return Severity.MEDIUM
        else:
            return Severity.LOW

class BusinessImpactScorer:
    """Score business impact of feedback"""
    
    def score_feedback(self, feedback: Feedback) -> Feedback:
        """Calculate business impact score"""
        score = 0.0
        
        # Base score from rating
        if feedback.rating is not None:
            score += (5 - feedback.rating) * 0.2  # Lower rating = higher impact
        
        # Sentiment impact
        if feedback.sentiment == Sentiment.NEGATIVE:
            score += 0.3
        elif feedback.sentiment == Sentiment.POSITIVE:
            score -= 0.1
        
        # Category impact
        if feedback.category == FeedbackCategory.BUG:
            score += 0.4
        elif feedback.category == FeedbackCategory.COMPLAINT:
            score += 0.3
        elif feedback.category == FeedbackCategory.FEATURE_REQUEST:
            score += 0.1
        
        # Severity impact
        if feedback.severity == Severity.CRITICAL:
            score += 0.5
        elif feedback.severity == Severity.HIGH:
            score += 0.3
        elif feedback.severity == Severity.MEDIUM:
            score += 0.1
        
        # PII detection increases impact
        if feedback.pii_detected:
            score += 0.2
        
        # Normalize to 0-1 range
        feedback.business_impact_score = min(1.0, max(0.0, score))
        return feedback

# Slack Integration (same as original but using unified database)
class SlackReviewFetcher:
    """Fetch reviews from Slack app-review channel"""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.client = None
        self.last_processed_timestamp = None
        self.auto_process_enabled = os.getenv('AUTO_PROCESS_REVIEWS', 'true').lower() == 'true'
        self.unified_db_path = "unified_messages.db"
        
        logger.info(f"SlackReviewFetcher: SLACK_AVAILABLE={SLACK_AVAILABLE}, bot_token={'***' if self.bot_token else 'None'}")
        
        if SLACK_AVAILABLE and self.bot_token:
            try:
                # Initialize WebClient with SSL context to handle certificate issues
                if ssl_context:
                    self.client = WebClient(token=self.bot_token, ssl=ssl_context)
                else:
                    self.client = WebClient(token=self.bot_token)
                
                # Test the connection
                auth_response = self.client.auth_test()
                logger.info(f"SlackReviewFetcher: Successfully connected as {auth_response['user']}")
            except Exception as e:
                logger.error(f"SlackReviewFetcher: Failed to initialize client: {e}")
                self.client = None
        else:
            logger.warning(f"SlackReviewFetcher: Not initializing client - SLACK_AVAILABLE={SLACK_AVAILABLE}, bot_token={'***' if self.bot_token else 'None'}")
    
    def get_channel_id(self, channel_name: Optional[str] = None) -> Optional[str]:
        """Get channel ID from channel name"""
        if not self.client:
            return None
        
        # Use environment variable or default
        if channel_name is None:
            channel_name = os.getenv('SLACK_REVIEW_CHANNEL', 'app-review')
        
        try:
            response = self.client.conversations_list(types="public_channel,private_channel")
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
        except SlackApiError as e:
            logger.error(f"Error getting channel ID: {e}")
        return None
    
    def fetch_reviews_from_slack(self, channel_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch review messages from Slack channel"""
        if not self.client:
            logger.warning("Slack client not available, returning mock data")
            return self._get_mock_slack_reviews(limit)
        
        logger.info(f"Fetching reviews from Slack channel: {channel_name}")
        
        # Use environment variable or default if not provided
        if channel_name is None:
            channel_name = os.getenv('SLACK_REVIEW_CHANNEL', 'app-review')
        
        channel_id = self.get_channel_id(channel_name)
        if not channel_id:
            logger.error(f"Channel '{channel_name}' not found")
            return []
        
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit
            )
            
            reviews = []
            for message in response["messages"]:
                if message.get("text"):
                    parsed_review = self._parse_slack_message(message)
                    if parsed_review:
                        reviews.append(parsed_review)
            
            return reviews
            
        except SlackApiError as e:
            logger.error(f"Error fetching messages from Slack: {e}")
            logger.warning("Falling back to mock data due to Slack API error")
            return self._get_mock_slack_reviews(limit)
    
    def _parse_slack_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Slack message to extract review information"""
        text = message.get("text", "")
        timestamp = message.get("ts", "")
        user = message.get("user", "unknown")
        
        # Log all messages for debugging
        logger.info(f"📨 Processing Slack message from user {user}: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Parse different review formats
        review_data = None
        
        # App Store review format
        if "App Store" in text or "iOS" in text:
            review_data = self._parse_app_store_review(text, timestamp, user)
            logger.info(f"✅ Parsed as App Store review: {review_data['id'] if review_data else 'Failed'}")
        # Play Store review format  
        elif "Play Store" in text or "Android" in text or "Google Play" in text:
            review_data = self._parse_play_store_review(text, timestamp, user)
            logger.info(f"✅ Parsed as Play Store review: {review_data['id'] if review_data else 'Failed'}")
        else:
            # Process as general Slack message
            review_data = self._parse_general_slack_message(text, timestamp, user)
            logger.info(f"✅ Parsed as general Slack message: {review_data['id'] if review_data else 'Failed'}")
        
        return review_data
    
    def _parse_app_store_review(self, text: str, timestamp: str, user: str) -> Optional[Dict[str, Any]]:
        """Parse App Store review from Slack message"""
        # Extract rating (look for star patterns or rating numbers)
        rating_match = re.search(r'(\d+)\s*stars?|rating[:\s]*(\d+)', text, re.IGNORECASE)
        rating = None
        if rating_match:
            rating = int(rating_match.group(1) or rating_match.group(2))
        
        # Extract review content (remove metadata)
        content = text
        # Remove common prefixes
        prefixes_to_remove = [
            r'App Store.*?:',
            r'iOS.*?:',
            r'Rating.*?:',
            r'User.*?:',
            r'Review.*?:'
        ]
        
        for prefix in prefixes_to_remove:
            content = re.sub(prefix, '', content, flags=re.IGNORECASE)
        
        content = content.strip()
        
        return {
            "id": f"slack_appstore_{timestamp}_{user}",
            "source": "app_store",
            "content": content,
            "author": user,
            "rating": rating,
            "timestamp": datetime.fromtimestamp(float(timestamp)).isoformat(),
            "url": f"slack://channel?team=T&id=C&message={timestamp}",
            "platform": "slack"
        }
    
    def _parse_play_store_review(self, text: str, timestamp: str, user: str) -> Optional[Dict[str, Any]]:
        """Parse Play Store review from Slack message"""
        # Extract rating
        rating_match = re.search(r'(\d+)\s*stars?|rating[:\s]*(\d+)', text, re.IGNORECASE)
        rating = None
        if rating_match:
            rating = int(rating_match.group(1) or rating_match.group(2))
        
        # Extract review content
        content = text
        prefixes_to_remove = [
            r'Play Store.*?:',
            r'Google Play.*?:',
            r'Android.*?:',
            r'Rating.*?:',
            r'User.*?:',
            r'Review.*?:'
        ]
        
        for prefix in prefixes_to_remove:
            content = re.sub(prefix, '', content, flags=re.IGNORECASE)
        
        content = content.strip()
        
        return {
            "id": f"slack_playstore_{timestamp}_{user}",
            "source": "play_store", 
            "content": content,
            "author": user,
            "rating": rating,
            "timestamp": datetime.fromtimestamp(float(timestamp)).isoformat(),
            "url": f"slack://channel?team=T&id=C&message={timestamp}",
            "platform": "slack"
        }
    
    def _parse_general_slack_message(self, text: str, timestamp: str, user: str) -> Optional[Dict[str, Any]]:
        """Parse general Slack message as feedback"""
        # Clean the content
        content = text.strip()
        
        # Skip empty messages or system messages
        if not content or content.startswith('<!') or content.startswith('<@'):
            return None
        
        return {
            "id": f"slack_general_{timestamp}_{user}",
            "source": "slack",
            "content": content,
            "author": user,
            "rating": None,  # No rating for general messages
            "timestamp": datetime.fromtimestamp(float(timestamp)).isoformat(),
            "url": f"slack://channel?team=T&id=C&message={timestamp}",
            "platform": "slack"
        }
    
    def _get_mock_slack_reviews(self, limit: int) -> List[Dict[str, Any]]:
        """Get mock Slack reviews for testing"""
        mock_reviews = [
            {
                "id": f"slack_appstore_mock_{i}",
                "source": "app_store",
                "content": f"Mock App Store review from Slack {i}: Great app, love the new features!",
                "author": f"slack_user_{i}",
                "rating": 4 if i % 2 == 0 else 2,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": f"slack://channel?message=mock_{i}",
                "platform": "slack"
            }
            for i in range(min(limit, 5))
        ]
        
        mock_reviews.extend([
            {
                "id": f"slack_playstore_mock_{i}",
                "source": "play_store",
                "content": f"Mock Play Store review from Slack {i}: App crashes sometimes, needs fixing.",
                "author": f"slack_user_{i+5}",
                "rating": 2 if i % 2 == 0 else 5,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": f"slack://channel?message=mock_{i+5}",
                "platform": "slack"
            }
            for i in range(min(limit, 5))
        ])
        
        return mock_reviews
    
    def get_last_processed_timestamp(self) -> Optional[str]:
        """Get the timestamp of the most recently processed Slack message from the database"""
        try:
            import sqlite3
            with sqlite3.connect(self.unified_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp FROM messages 
                    WHERE source = 'slack' 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    return result[0]
        except Exception as e:
            logger.error(f"Error getting last processed timestamp: {e}")
        return None
    
    def get_last_processed_message_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the most recently processed Slack message"""
        try:
            import sqlite3
            with sqlite3.connect(self.unified_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, content, author FROM messages 
                    WHERE source = 'slack' 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'timestamp': result[1],
                        'content': result[2][:100] + '...' if len(result[2]) > 100 else result[2],
                        'author': result[3]
                    }
        except Exception as e:
            logger.error(f"Error getting last processed message info: {e}")
        return None
    
    def fetch_new_slack_messages(self, channel_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch only new Slack messages that haven't been processed yet"""
        if not self.client:
            logger.warning("Slack client not available, returning empty list")
            return []
        
        # Get the last processed timestamp from database
        last_timestamp = self.get_last_processed_timestamp()
        
        # Use environment variable or default if not provided
        if channel_name is None:
            channel_name = os.getenv('SLACK_REVIEW_CHANNEL', 'app-review')
        
        channel_id = self.get_channel_id(channel_name)
        if not channel_id:
            logger.error(f"Channel '{channel_name}' not found")
            return []
        
        try:
            # Build parameters for fetching messages
            params = {
                "channel": channel_id,
                "limit": limit
            }
            
            # If we have a last processed timestamp, only fetch messages after that
            if last_timestamp:
                # Convert ISO timestamp to Slack timestamp format
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                    slack_timestamp = str(dt.timestamp())
                    params["oldest"] = slack_timestamp
                    
                    # Get info about the last processed message for logging
                    last_msg_info = self.get_last_processed_message_info()
                    if last_msg_info:
                        logger.info(f"Fetching Slack messages after: {last_timestamp} (last: {last_msg_info['content']})")
                    else:
                        logger.info(f"Fetching Slack messages after timestamp: {last_timestamp}")
                except Exception as e:
                    logger.warning(f"Could not parse last timestamp {last_timestamp}: {e}")
            else:
                logger.info("No previous Slack messages found, fetching all recent messages")
            
            response = self.client.conversations_history(**params)
            
            new_messages = []
            for message in response["messages"]:
                if message.get("text"):
                    parsed_review = self._parse_slack_message(message)
                    if parsed_review:
                        new_messages.append(parsed_review)
            
            logger.info(f"Found {len(new_messages)} new Slack messages since last check")
            return new_messages
            
        except SlackApiError as e:
            logger.error(f"Error fetching new messages from Slack: {e}")
            return []
    
    def auto_process_new_reviews(self, channel_name: Optional[str] = None) -> int:
        """Automatically process new reviews and return count of processed items"""
        if not self.auto_process_enabled:
            return 0
        
        # First try to fetch only new messages using timestamp filtering
        new_reviews = self.fetch_new_slack_messages(channel_name, limit=50)
        
        # If timestamp filtering didn't work or returned no results, fall back to full fetch with deduplication
        if not new_reviews:
            logger.info("No new messages found via timestamp filtering, checking for any new messages...")
            all_reviews = self.fetch_reviews_from_slack(channel_name, limit=50)
            if not all_reviews:
                return 0
            
            # Filter out messages that already exist in the database
            new_reviews = []
            for review_data in all_reviews:
                # Check if this message already exists in the database
                existing_feedback = db.get_feedback(review_data["id"])
                if not existing_feedback:
                    new_reviews.append(review_data)
                else:
                    logger.debug(f"Skipping existing message: {review_data['id']}")
        
        if not new_reviews:
            logger.info("No new Slack messages found")
            return 0
        
        processed_count = 0
        for review_data in new_reviews:
            # Determine source
            if review_data["source"] == "app_store":
                source = FeedbackSource.APP_STORE
            elif review_data["source"] == "play_store":
                source = FeedbackSource.PLAY_STORE
            elif review_data["source"] == "slack":
                source = FeedbackSource.SLACK
            else:
                continue  # Skip unrecognized messages
            
            feedback = Feedback(
                id=review_data["id"],
                source=source,
                content=review_data["content"],
                author=review_data["author"],
                timestamp=datetime.fromisoformat(review_data["timestamp"]),
                url=review_data["url"],
                rating=review_data["rating"]
            )
            
            # Normalize, classify, and score
            feedback = normalizer.normalize_feedback(feedback)
            feedback = classifier.classify_feedback(feedback)
            feedback = scorer.score_feedback(feedback)
            feedback.processed = True
            feedback.updated_at = datetime.now(timezone.utc)
            
            # Save to unified database
            if db.save_feedback(feedback):
                processed_count += 1
                logger.info(f"Auto-processed new review: {feedback.id}")
        
        if processed_count > 0:
            logger.info(f"✅ Auto-processed {processed_count} new Slack messages")
        else:
            logger.info("ℹ️ No new Slack messages to process")
        
        return processed_count

# Initialize components
normalizer = FeedbackNormalizer()
classifier = FeedbackClassifier()
scorer = BusinessImpactScorer()
slack_fetcher = SlackReviewFetcher()

# MCP Tools Implementation (same as original but using unified database)

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_unified_database_stats",
            description="Get comprehensive statistics from the unified messages database",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="fetch_slack_messages_unified",
            description="Fetch all messages from a Slack channel and save to unified database",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "Slack channel name to fetch from", "default": "all-feedforward"},
                    "limit": {"type": "integer", "description": "Maximum number of messages to fetch", "default": 50}
                }
            }
        ),
        Tool(
            name="process_feedback_queue_unified",
            description="Process all unprocessed feedback in the unified database queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "batch_size": {"type": "integer", "description": "Number of feedback items to process (null for all)", "default": None}
                }
            }
        ),
        Tool(
            name="get_messages_by_source",
            description="Get messages from the unified database by source",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source to filter by (reddit, slack, app_store, play_store, twitter)"},
                    "limit": {"type": "integer", "description": "Maximum number of messages to return", "default": 50}
                },
                "required": ["source"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "get_unified_database_stats":
            return get_unified_database_stats(arguments)
        elif name == "fetch_slack_messages_unified":
            return fetch_slack_messages_unified(arguments)
        elif name == "process_feedback_queue_unified":
            return process_feedback_queue_unified(arguments)
        elif name == "get_messages_by_source":
            return get_messages_by_source(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")]
        )

# Tool implementations

def get_unified_database_stats(arguments: Dict[str, Any]) -> CallToolResult:
    """Get comprehensive database statistics"""
    stats = db.get_database_stats()
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Unified Database Statistics:\n{json.dumps(stats, indent=2)}"
        )]
    )

def fetch_slack_messages_unified(arguments: Dict[str, Any]) -> CallToolResult:
    """Fetch all messages from a Slack channel and save to unified database"""
    channel_name = arguments.get("channel_name", os.getenv('SLACK_REVIEW_CHANNEL', 'all-feedforward'))
    limit = arguments.get("limit", 50)
    
    # Fetch all messages from Slack channel
    slack_messages = slack_fetcher.fetch_reviews_from_slack(channel_name, limit)
    
    # Save to unified database
    saved_count = 0
    app_store_count = 0
    play_store_count = 0
    general_count = 0
    
    for message_data in slack_messages:
        # Determine source
        if message_data["source"] == "app_store":
            source = FeedbackSource.APP_STORE
            app_store_count += 1
        elif message_data["source"] == "play_store":
            source = FeedbackSource.PLAY_STORE
            play_store_count += 1
        elif message_data["source"] == "slack":
            source = FeedbackSource.SLACK
            general_count += 1
        else:
            continue  # Skip unrecognized messages
        
        feedback = Feedback(
            id=message_data["id"],
            source=source,
            content=message_data["content"],
            author=message_data["author"],
            timestamp=datetime.fromisoformat(message_data["timestamp"]),
            url=message_data["url"],
            rating=message_data["rating"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} messages from Slack channel '{channel_name}' to unified database: {app_store_count} App Store, {play_store_count} Play Store, {general_count} general messages"
        )]
    )

def process_feedback_queue_unified(arguments: Dict[str, Any]) -> CallToolResult:
    """Process all unprocessed feedback in the unified database"""
    batch_size = arguments.get("batch_size", None)
    
    unprocessed = db.get_unprocessed_feedback()
    processed_count = 0
    
    # Process all unprocessed feedback if batch_size is None, otherwise limit to batch_size
    feedback_to_process = unprocessed if batch_size is None else unprocessed[:batch_size]
    for feedback in feedback_to_process:
        # Classify
        feedback = classifier.classify_feedback(feedback)
        
        # Score
        feedback = scorer.score_feedback(feedback)
        
        # Mark as processed
        feedback.processed = True
        feedback.updated_at = datetime.now(timezone.utc)
        
        # Save
        if db.save_feedback(feedback):
            processed_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Processed {processed_count} feedback items from the unified database queue"
        )]
    )

def get_messages_by_source(arguments: Dict[str, Any]) -> CallToolResult:
    """Get messages from the unified database by source"""
    source = arguments["source"]
    limit = arguments.get("limit", 50)
    
    messages = db.get_feedback_by_source(source)
    
    # Limit results
    messages = messages[:limit]
    
    # Format results
    result_text = f"Found {len(messages)} messages from {source}:\n\n"
    for i, msg in enumerate(messages, 1):
        result_text += f"{i}. ID: {msg.id}\n"
        result_text += f"   Author: {msg.author}\n"
        result_text += f"   Content: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}\n"
        result_text += f"   Timestamp: {msg.timestamp}\n"
        if msg.rating:
            result_text += f"   Rating: {msg.rating}\n"
        if msg.sentiment:
            result_text += f"   Sentiment: {msg.sentiment.value}\n"
        if msg.category:
            result_text += f"   Category: {msg.category.value}\n"
        result_text += "\n"
    
    return CallToolResult(
        content=[TextContent(type="text", text=result_text)]
    )

# Resources

@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="unified-database",
            name="Unified Messages Database",
            description="Access to the unified messages database with all Reddit, Slack, and other platform messages",
            mimeType=JSON_MIME_TYPE
        ),
        Resource(
            uri="database-stats",
            name="Database Statistics",
            description="Comprehensive statistics about the unified messages database",
            mimeType=JSON_MIME_TYPE
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read resource content"""
    if uri == "unified-database":
        # Get database statistics
        stats = db.get_database_stats()
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(stats, indent=2))]
        )
    
    elif uri == "database-stats":
        # Get detailed database statistics
        stats = db.get_database_stats()
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(stats, indent=2))]
        )
    
    else:
        return ReadResourceResult(
            contents=[TextContent(type="text", text=f"Resource {uri} not found")]
        )

async def main():
    """Main entry point"""
    logger.info("🚀 Starting Feedback Management MCP Server (Unified Database)...")
    logger.info(f"Using unified database: {UNIFIED_DB_PATH}")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="feedback-management-unified",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
