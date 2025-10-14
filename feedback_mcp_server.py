#!/usr/bin/env python3
"""
Feedback Management MCP Server

A comprehensive MCP server for collecting, processing, and managing feedback
from multiple sources including App Store, Google Play, Reddit, Twitter, and other channels.
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
    
    # Configure SSL context to use certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())
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
app = Server("feedback-management")

# Constants
JSON_MIME_TYPE = "application/json"

# Database setup
DB_PATH = "feedback.db"

class FeedbackSource(Enum):
    APP_STORE = "app_store"
    PLAY_STORE = "play_store"
    REDDIT = "reddit"
    TWITTER = "twitter"
    EMAIL = "email"
    WEB = "web"
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

class FeedbackDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create feedbacks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    url TEXT,
                    rating INTEGER,
                    language TEXT,
                    category TEXT,
                    sentiment TEXT,
                    severity TEXT,
                    business_impact_score REAL,
                    pii_detected BOOLEAN DEFAULT FALSE,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create authors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authors (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    email TEXT,
                    platform TEXT,
                    reputation_score REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create threads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    feedback_id TEXT,
                    platform TEXT,
                    thread_url TEXT,
                    status TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (feedback_id) REFERENCES feedbacks (id)
                )
            """)
            
            conn.commit()
    
    def save_feedback(self, feedback: Feedback) -> bool:
        """Save feedback to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO feedbacks 
                    (id, source, content, author, timestamp, url, rating, language,
                     category, sentiment, severity, business_impact_score, pii_detected,
                     processed, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback.id, feedback.source.value, feedback.content, feedback.author,
                    feedback.timestamp.isoformat(), feedback.url, feedback.rating,
                    feedback.language, feedback.category.value if feedback.category else None,
                    feedback.sentiment.value if feedback.sentiment else None,
                    feedback.severity.value if feedback.severity else None,
                    feedback.business_impact_score, feedback.pii_detected,
                    feedback.processed, feedback.created_at.isoformat(),
                    feedback.updated_at.isoformat()
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
                cursor.execute("SELECT * FROM feedbacks WHERE id = ?", (feedback_id,))
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
                cursor.execute("SELECT * FROM feedbacks WHERE processed = FALSE ORDER BY created_at ASC")
                rows = cursor.fetchall()
                return [self._row_to_feedback(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting unprocessed feedback: {e}")
            return []
    
    def _row_to_feedback(self, row) -> Feedback:
        """Convert database row to Feedback object"""
        return Feedback(
            id=row[0], source=FeedbackSource(row[1]), content=row[2], author=row[3],
            timestamp=datetime.fromisoformat(row[4]), url=row[5], rating=row[6],
            language=row[7], 
            category=FeedbackCategory(row[8]) if row[8] else None,
            sentiment=Sentiment(row[9]) if row[9] else None,
            severity=Severity(row[10]) if row[10] else None,
            business_impact_score=row[11], pii_detected=bool(row[12]),
            processed=bool(row[13]), created_at=datetime.fromisoformat(row[14]),
            updated_at=datetime.fromisoformat(row[15])
        )

# Initialize database
db = FeedbackDatabase()

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

# Slack Integration
class SlackReviewFetcher:
    """Fetch reviews from Slack app-review channel"""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.client = None
        self.last_processed_timestamp = None
        self.auto_process_enabled = os.getenv('AUTO_PROCESS_REVIEWS', 'true').lower() == 'true'
        if SLACK_AVAILABLE and self.bot_token:
            # Initialize WebClient with SSL context to handle certificate issues
            if ssl_context:
                self.client = WebClient(token=self.bot_token, ssl=ssl_context)
            else:
                self.client = WebClient(token=self.bot_token)
    
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
            return self._get_mock_slack_reviews(limit)
    
    def _parse_slack_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Slack message to extract review information"""
        text = message.get("text", "")
        timestamp = message.get("ts", "")
        user = message.get("user", "unknown")
        
        # Parse different review formats
        review_data = None
        
        # App Store review format
        if "App Store" in text or "iOS" in text:
            review_data = self._parse_app_store_review(text, timestamp, user)
        # Play Store review format  
        elif "Play Store" in text or "Android" in text or "Google Play" in text:
            review_data = self._parse_play_store_review(text, timestamp, user)
        
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
    
    def check_for_new_reviews(self, channel_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check for new reviews since last processed timestamp"""
        if not self.client or not self.auto_process_enabled:
            return []
        
        # Use environment variable or default if not provided
        if channel_name is None:
            channel_name = os.getenv('SLACK_REVIEW_CHANNEL', 'app-review')
        
        channel_id = self.get_channel_id(channel_name)
        if not channel_id:
            return []
        
        try:
            # Get messages since last processed timestamp
            params = {
                "channel": channel_id,
                "limit": 50
            }
            
            if self.last_processed_timestamp:
                params["oldest"] = self.last_processed_timestamp
            
            response = self.client.conversations_history(**params)
            
            new_reviews = []
            latest_timestamp = self.last_processed_timestamp
            
            for message in response["messages"]:
                if message.get("text"):
                    parsed_review = self._parse_slack_message(message)
                    if parsed_review:
                        new_reviews.append(parsed_review)
                        # Update latest timestamp
                        message_ts = float(message.get("ts", 0))
                        if not latest_timestamp or message_ts > latest_timestamp:
                            latest_timestamp = message_ts
            
            # Update last processed timestamp
            if latest_timestamp:
                self.last_processed_timestamp = latest_timestamp
            
            return new_reviews
            
        except SlackApiError as e:
            logger.error(f"Error checking for new reviews: {e}")
            return []
    
    def auto_process_new_reviews(self, channel_name: Optional[str] = None) -> int:
        """Automatically process new reviews and return count of processed items"""
        if not self.auto_process_enabled:
            return 0
        
        new_reviews = self.check_for_new_reviews(channel_name)
        if not new_reviews:
            return 0
        
        processed_count = 0
        for review_data in new_reviews:
            # Determine source
            if review_data["source"] == "app_store":
                source = FeedbackSource.APP_STORE
            elif review_data["source"] == "play_store":
                source = FeedbackSource.PLAY_STORE
            else:
                continue  # Skip non-review messages
            
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
            
            # Save to database
            if db.save_feedback(feedback):
                processed_count += 1
                logger.info(f"Auto-processed new review: {feedback.id}")
        
        if processed_count > 0:
            logger.info(f"Auto-processed {processed_count} new reviews")
        
        return processed_count

# Initialize components
normalizer = FeedbackNormalizer()
classifier = FeedbackClassifier()
scorer = BusinessImpactScorer()
slack_fetcher = SlackReviewFetcher()

# MCP Tools Implementation

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="fetch_appstore_reviews",
            description="Fetch App Store reviews from Slack app-review channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "Slack channel name to fetch from", "default": "app-review"},
                    "limit": {"type": "integer", "description": "Maximum number of reviews to fetch", "default": 50}
                }
            }
        ),
        Tool(
            name="fetch_playstore_reviews",
            description="Fetch Play Store reviews from Slack app-review channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "Slack channel name to fetch from", "default": "app-review"},
                    "limit": {"type": "integer", "description": "Maximum number of reviews to fetch", "default": 50}
                }
            }
        ),
        Tool(
            name="fetch_slack_reviews",
            description="Fetch all app reviews (App Store and Play Store) from Slack app-review channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "Slack channel name to fetch from", "default": "app-review"},
                    "limit": {"type": "integer", "description": "Maximum number of reviews to fetch", "default": 50}
                }
            }
        ),
        Tool(
            name="reddit_search_stream",
            description="Search for mentions on Reddit",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "subreddit": {"type": "string", "description": "Specific subreddit to search"},
                    "limit": {"type": "integer", "description": "Maximum number of posts to fetch", "default": 25}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="twitter_search_stream",
            description="Search for mentions on Twitter/X",
            inputSchema={
                "type": "object",
                               "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Maximum number of tweets to fetch", "default": 25}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="url_scrape_feed",
            description="Scrape feedback from a URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to scrape"},
                    "selector": {"type": "string", "description": "CSS selector for feedback content"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="classify_feedback",
            description="Classify feedback into category, sentiment, and severity",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to classify"}
                },
                "required": ["feedback_id"]
            }
        ),
        Tool(
            name="score_business_impact",
            description="Score the business impact of feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to score"}
                },
                "required": ["feedback_id"]
            }
        ),
        Tool(
            name="route_to_team",
            description="Route feedback to appropriate team based on classification",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to route"}
                },
                "required": ["feedback_id"]
            }
        ),
        Tool(
            name="create_ticket_or_thread",
            description="Create a ticket or thread for feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to create ticket for"},
                    "platform": {"type": "string", "description": "Platform to create ticket on (slack, jira, asana)"},
                    "channel": {"type": "string", "description": "Channel or project to create ticket in"}
                },
                "required": ["feedback_id", "platform"]
            }
        ),
        Tool(
            name="generate_reply",
            description="Generate a reply for feedback",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to reply to"},
                    "tone": {"type": "string", "description": "Tone for the reply (professional, friendly, apologetic)"},
                    "platform": {"type": "string", "description": "Platform to generate reply for"}
                },
                "required": ["feedback_id"]
            }
        ),
        Tool(
            name="post_reply",
            description="Post a reply to the original platform",
            inputSchema={
                "type": "object",
                "properties": {
                    "feedback_id": {"type": "string", "description": "ID of feedback to reply to"},
                    "reply_content": {"type": "string", "description": "Content of the reply"},
                    "platform": {"type": "string", "description": "Platform to post reply on"}
                },
                "required": ["feedback_id", "reply_content", "platform"]
            }
        ),
        Tool(
            name="process_feedback_queue",
            description="Process all unprocessed feedback in the queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "batch_size": {"type": "integer", "description": "Number of feedback items to process", "default": 10}
                }
            }
        ),
        Tool(
            name="get_metrics",
            description="Get feedback metrics and dashboard data",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string", "description": "Timeframe for metrics (day, week, month)", "default": "week"},
                    "source": {"type": "string", "description": "Filter by source (optional)"}
                }
            }
        ),
        Tool(
            name="check_new_reviews",
            description="Check for new reviews and automatically process them",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_name": {"type": "string", "description": "Slack channel name to check", "default": "app-review"},
                    "auto_process": {"type": "boolean", "description": "Automatically process new reviews", "default": true}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "fetch_appstore_reviews":
            return fetch_appstore_reviews(arguments)
        elif name == "fetch_playstore_reviews":
            return fetch_playstore_reviews(arguments)
        elif name == "fetch_slack_reviews":
            return fetch_slack_reviews(arguments)
        elif name == "reddit_search_stream":
            return reddit_search_stream(arguments)
        elif name == "twitter_search_stream":
            return twitter_search_stream(arguments)
        elif name == "url_scrape_feed":
            return url_scrape_feed(arguments)
        elif name == "classify_feedback":
            return classify_feedback(arguments)
        elif name == "score_business_impact":
            return score_business_impact(arguments)
        elif name == "route_to_team":
            return route_to_team(arguments)
        elif name == "create_ticket_or_thread":
            return create_ticket_or_thread(arguments)
        elif name == "generate_reply":
            return generate_reply(arguments)
        elif name == "post_reply":
            return post_reply(arguments)
        elif name == "process_feedback_queue":
            return process_feedback_queue(arguments)
        elif name == "get_metrics":
            return get_metrics(arguments)
        elif name == "check_new_reviews":
            return check_new_reviews(arguments)
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

def fetch_appstore_reviews(arguments: Dict[str, Any]) -> CallToolResult:
    """Fetch App Store reviews from Slack app-review channel"""
    channel_name = arguments.get("channel_name", os.getenv('SLACK_REVIEW_CHANNEL', 'app-review'))
    limit = arguments.get("limit", 50)
    
    # Fetch reviews from Slack channel
    slack_reviews = slack_fetcher.fetch_reviews_from_slack(channel_name, limit)
    
    # Filter for App Store reviews only
    app_store_reviews = [review for review in slack_reviews if review["source"] == "app_store"]
    
    # Save to database
    saved_count = 0
    for review_data in app_store_reviews:
        feedback = Feedback(
            id=review_data["id"],
            source=FeedbackSource.APP_STORE,
            content=review_data["content"],
            author=review_data["author"],
            timestamp=datetime.fromisoformat(review_data["timestamp"]),
            url=review_data["url"],
            rating=review_data["rating"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} App Store reviews from Slack channel '{channel_name}'"
        )]
    )

def fetch_playstore_reviews(arguments: Dict[str, Any]) -> CallToolResult:
    """Fetch Play Store reviews from Slack app-review channel"""
    channel_name = arguments.get("channel_name", os.getenv('SLACK_REVIEW_CHANNEL', 'app-review'))
    limit = arguments.get("limit", 50)
    
    # Fetch reviews from Slack channel
    slack_reviews = slack_fetcher.fetch_reviews_from_slack(channel_name, limit)
    
    # Filter for Play Store reviews only
    play_store_reviews = [review for review in slack_reviews if review["source"] == "play_store"]
    
    # Save to database
    saved_count = 0
    for review_data in play_store_reviews:
        feedback = Feedback(
            id=review_data["id"],
            source=FeedbackSource.PLAY_STORE,
            content=review_data["content"],
            author=review_data["author"],
            timestamp=datetime.fromisoformat(review_data["timestamp"]),
            url=review_data["url"],
            rating=review_data["rating"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} Play Store reviews from Slack channel '{channel_name}'"
        )]
    )

def fetch_slack_reviews(arguments: Dict[str, Any]) -> CallToolResult:
    """Fetch all app reviews (App Store and Play Store) from Slack app-review channel"""
    channel_name = arguments.get("channel_name", os.getenv('SLACK_REVIEW_CHANNEL', 'app-review'))
    limit = arguments.get("limit", 50)
    
    # Fetch all reviews from Slack channel
    slack_reviews = slack_fetcher.fetch_reviews_from_slack(channel_name, limit)
    
    # Save to database
    saved_count = 0
    app_store_count = 0
    play_store_count = 0
    
    for review_data in slack_reviews:
        # Determine source
        if review_data["source"] == "app_store":
            source = FeedbackSource.APP_STORE
            app_store_count += 1
        elif review_data["source"] == "play_store":
            source = FeedbackSource.PLAY_STORE
            play_store_count += 1
        else:
            continue  # Skip non-review messages
        
        feedback = Feedback(
            id=review_data["id"],
            source=source,
            content=review_data["content"],
            author=review_data["author"],
            timestamp=datetime.fromisoformat(review_data["timestamp"]),
            url=review_data["url"],
            rating=review_data["rating"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} reviews from Slack channel '{channel_name}': {app_store_count} App Store, {play_store_count} Play Store"
        )]
    )

def reddit_search_stream(arguments: Dict[str, Any]) -> CallToolResult:
    """Search Reddit for mentions"""
    query = arguments["query"]
    subreddit = arguments.get("subreddit")
    limit = arguments.get("limit", 25)
    
    # Mock implementation - in production, use Reddit API
    mock_posts = [
        {
            "id": f"reddit_{i}",
            "content": f"Mock Reddit post about {query} {i}",
            "author": f"redditor{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": f"https://reddit.com/r/{subreddit or 'all'}/post/{i}",
            "subreddit": subreddit or "all"
        }
        for i in range(min(limit, 5))
    ]
    
    # Save to database
    saved_count = 0
    for post_data in mock_posts:
        feedback = Feedback(
            id=post_data["id"],
            source=FeedbackSource.REDDIT,
            content=post_data["content"],
            author=post_data["author"],
            timestamp=datetime.fromisoformat(post_data["timestamp"]),
            url=post_data["url"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} Reddit posts for query '{query}'"
        )]
    )

def twitter_search_stream(arguments: Dict[str, Any]) -> CallToolResult:
    """Search Twitter/X for mentions"""
    query = arguments["query"]
    limit = arguments.get("limit", 25)
    
    # Mock implementation - in production, use Twitter API
    mock_tweets = [
        {
            "id": f"twitter_{i}",
            "content": f"Mock tweet about {query} {i}",
            "author": f"user{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": f"https://twitter.com/user{i}/status/{i}"
        }
        for i in range(min(limit, 5))
    ]
    
    # Save to database
    saved_count = 0
    for tweet_data in mock_tweets:
        feedback = Feedback(
            id=tweet_data["id"],
            source=FeedbackSource.TWITTER,
            content=tweet_data["content"],
            author=tweet_data["author"],
            timestamp=datetime.fromisoformat(tweet_data["timestamp"]),
            url=tweet_data["url"]
        )
        
        # Normalize and save
        feedback = normalizer.normalize_feedback(feedback)
        if db.save_feedback(feedback):
            saved_count += 1
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Fetched and saved {saved_count} Twitter posts for query '{query}'"
        )]
    )

def url_scrape_feed(arguments: Dict[str, Any]) -> CallToolResult:
    """Scrape feedback from URL"""
    url = arguments["url"]
    
    # Mock implementation - in production, use web scraping library
    mock_content = f"Mock scraped content from {url}"
    
    feedback = Feedback(
        id=f"scraped_{uuid.uuid4().hex[:8]}",
        source=FeedbackSource.WEB,
        content=mock_content,
        author="anonymous",
        timestamp=datetime.now(timezone.utc),
        url=url
    )
    
    # Normalize and save
    feedback = normalizer.normalize_feedback(feedback)
    saved = db.save_feedback(feedback)
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Scraped and saved content from {url}" if saved else f"Failed to save content from {url}"
        )]
    )

def classify_feedback(arguments: Dict[str, Any]) -> CallToolResult:
    """Classify feedback"""
    feedback_id = arguments["feedback_id"]
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Classify the feedback
    feedback = classifier.classify_feedback(feedback)
    
    # Save updated feedback
    db.save_feedback(feedback)
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Classified feedback {feedback_id}: Category={feedback.category.value}, Sentiment={feedback.sentiment.value}, Severity={feedback.severity.value}"
        )]
    )

def score_business_impact(arguments: Dict[str, Any]) -> CallToolResult:
    """Score business impact"""
    feedback_id = arguments["feedback_id"]
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Score the feedback
    feedback = scorer.score_feedback(feedback)
    
    # Save updated feedback
    db.save_feedback(feedback)
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Scored feedback {feedback_id}: Business Impact Score={feedback.business_impact_score:.2f}"
        )]
    )

def route_to_team(arguments: Dict[str, Any]) -> CallToolResult:
    """Route feedback to appropriate team"""
    feedback_id = arguments["feedback_id"]
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Simple routing logic
    if feedback.category == FeedbackCategory.BUG:
        team = "Engineering"
    elif feedback.category == FeedbackCategory.FEATURE_REQUEST:
        team = "Product"
    elif feedback.category == FeedbackCategory.COMPLAINT:
        team = "Customer Success"
    else:
        team = "General"
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Routed feedback {feedback_id} to {team} team"
        )]
    )

def create_ticket_or_thread(arguments: Dict[str, Any]) -> CallToolResult:
    """Create ticket or thread"""
    feedback_id = arguments["feedback_id"]
    channel = arguments.get("channel", "general")
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Mock ticket creation
    ticket_id = f"ticket_{uuid.uuid4().hex[:8]}"
    platform = arguments.get("platform", "general")
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Created {platform} ticket {ticket_id} in {channel} for feedback {feedback_id}"
        )]
    )

def generate_reply(arguments: Dict[str, Any]) -> CallToolResult:
    """Generate reply for feedback"""
    feedback_id = arguments["feedback_id"]
    tone = arguments.get("tone", "professional")
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Mock reply generation
    reply_templates = {
        "professional": "Thank you for your feedback. We appreciate you taking the time to share your thoughts.",
        "friendly": "Hey! Thanks for reaching out. We'd love to help you out!",
        "apologetic": "We sincerely apologize for the inconvenience. We're working to resolve this issue."
    }
    
    reply = reply_templates.get(tone, reply_templates["professional"])
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Generated {tone} reply for feedback {feedback_id}: {reply}"
        )]
    )

def post_reply(arguments: Dict[str, Any]) -> CallToolResult:
    """Post reply to original platform"""
    feedback_id = arguments["feedback_id"]
    reply_content = arguments["reply_content"]
    platform = arguments["platform"]
    
    feedback = db.get_feedback(feedback_id)
    if not feedback:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Feedback {feedback_id} not found")]
        )
    
    # Mock reply posting
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Posted reply to {platform} for feedback {feedback_id}: {reply_content[:50]}..."
        )]
    )

def process_feedback_queue(arguments: Dict[str, Any]) -> CallToolResult:
    """Process all unprocessed feedback"""
    batch_size = arguments.get("batch_size", 10)
    
    unprocessed = db.get_unprocessed_feedback()
    processed_count = 0
    
    for feedback in unprocessed[:batch_size]:
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
            text=f"Processed {processed_count} feedback items from the queue"
        )]
    )

def get_metrics(arguments: Dict[str, Any]) -> CallToolResult:
    """Get feedback metrics"""
    timeframe = arguments.get("timeframe", "week")
    
    # Mock metrics - in production, query database for real metrics
    metrics = {
        "total_feedback": 150,
        "processed_feedback": 120,
        "pending_feedback": 30,
        "avg_sentiment": "neutral",
        "top_categories": ["bug", "feature_request", "complaint"],
        "response_time_avg": "2.5 hours",
        "resolution_rate": "85%"
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Metrics for {timeframe}: {json.dumps(metrics, indent=2)}"
        )]
    )

def check_new_reviews(arguments: Dict[str, Any]) -> CallToolResult:
    """Check for new reviews and automatically process them"""
    channel_name = arguments.get("channel_name", os.getenv('SLACK_REVIEW_CHANNEL', 'app-review'))
    auto_process = arguments.get("auto_process", True)
    
    if auto_process:
        # Automatically process new reviews
        processed_count = slack_fetcher.auto_process_new_reviews(channel_name)
        
        if processed_count > 0:
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"✅ Found and processed {processed_count} new reviews from channel '{channel_name}'"
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"ℹ️ No new reviews found in channel '{channel_name}'"
                )]
            )
    else:
        # Just check for new reviews without processing
        new_reviews = slack_fetcher.check_for_new_reviews(channel_name)
        
        if new_reviews:
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"📋 Found {len(new_reviews)} new reviews in channel '{channel_name}'. Use auto_process=true to process them."
                )]
            )
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"ℹ️ No new reviews found in channel '{channel_name}'"
                )]
            )

# Resources

@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="company-context",
            name="Company Context",
            description="Company taxonomies, SLAs, known issues, and release notes",
            mimeType=JSON_MIME_TYPE
        ),
        Resource(
            uri="education-content",
            name="Education Content",
            description="How-tos, FAQ, and policy links for customer education",
            mimeType=JSON_MIME_TYPE
        ),
        Resource(
            uri="feedback-database",
            name="Feedback Database",
            description="Access to the feedback database for queries and analysis",
            mimeType=JSON_MIME_TYPE
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read resource content"""
    if uri == "company-context":
        context = {
            "taxonomies": {
                "categories": ["bug", "feature_request", "complaint", "praise", "question"],
                "severities": ["low", "medium", "high", "critical"],
                "sentiments": ["positive", "negative", "neutral"]
            },
            "slas": {
                "critical": "1 hour",
                "high": "4 hours",
                "medium": "24 hours",
                "low": "72 hours"
            },
            "known_issues": [
                "Login timeout issue - tracking in JIRA-1234",
                "Payment processing delay - resolved in v2.1.3"
            ],
            "release_notes": {
                "v2.1.3": "Fixed payment processing issues",
                "v2.1.2": "Improved login performance"
            }
        }
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(context, indent=2))]
        )
    
    elif uri == "education-content":
        content = {
            "faqs": [
                {
                    "question": "How do I reset my password?",
                    "answer": "Click 'Forgot Password' on the login screen and follow the instructions."
                },
                {
                    "question": "How do I contact support?",
                    "answer": "You can reach us at support@company.com or through the in-app chat."
                }
            ],
            "how_tos": [
                "Getting Started Guide",
                "Account Setup Tutorial",
                "Advanced Features Walkthrough"
            ],
            "policies": [
                "Privacy Policy",
                "Terms of Service",
                "Refund Policy"
            ]
        }
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(content, indent=2))]
        )
    
    elif uri == "feedback-database":
        # Get database statistics
        stats = {
            "total_feedback": len(db.get_unprocessed_feedback()) + 100,  # Mock total
            "unprocessed": len(db.get_unprocessed_feedback()),
            "sources": ["app_store", "play_store", "reddit", "twitter", "web"],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(stats, indent=2))]
        )
    
    else:
        return ReadResourceResult(
            contents=[TextContent(type="text", text=f"Resource {uri} not found")]
        )

async def background_review_checker():
    """Background task to automatically check for new reviews"""
    check_interval = int(os.getenv('REVIEW_CHECK_INTERVAL', '60'))  # Check every 60 seconds by default
    
    while True:
        try:
            if slack_fetcher.auto_process_enabled:
                processed_count = slack_fetcher.auto_process_new_reviews()
                if processed_count > 0:
                    logger.info(f"Background task processed {processed_count} new reviews")
        except Exception as e:
            logger.error(f"Error in background review checker: {e}")
        
        await asyncio.sleep(check_interval)

async def main():
    """Main entry point"""
    # Start background task for automatic review processing
    if os.getenv('AUTO_PROCESS_REVIEWS', 'true').lower() == 'true':
        asyncio.create_task(background_review_checker())
        logger.info("Background review checker started")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="feedback-management",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
