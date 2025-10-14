"""
Slack Reply System for all-feedforward Channel

This module handles automatic replies to messages in the all-feedforward channel
based on sentiment analysis. It replies in the same message thread with appropriate
responses for positive/neutral and negative feedback.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Import existing modules
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from enhanced_message_classifier import EnhancedMessageClassifier

# Load environment variables
load_dotenv('config/env.local')

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """Sentiment classification"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class ReplyResult:
    """Result of posting a reply"""
    success: bool
    message_ts: Optional[str] = None
    error: Optional[str] = None
    original_message_ts: Optional[str] = None
    jira_ticket: Optional[str] = None


class SentimentAnalyzer:
    """Analyze sentiment of messages using keyword-based approach"""
    
    def __init__(self):
        # Positive sentiment keywords
        self.positive_keywords = [
            'love', 'great', 'awesome', 'amazing', 'perfect', 'excellent', 'good', 
            'thanks', 'thank you', 'wonderful', 'fantastic', 'brilliant', 'outstanding',
            'helpful', 'useful', 'satisfied', 'happy', 'pleased', 'impressed',
            'recommend', 'best', 'top', 'exceeded', 'surpassed', 'delighted'
        ]
        
        # Negative sentiment keywords
        self.negative_keywords = [
            'hate', 'terrible', 'awful', 'horrible', 'bad', 'worst', 'disappointed', 
            'frustrated', 'angry', 'annoyed', 'upset', 'disgusted', 'displeased',
            'broken', 'bug', 'error', 'issue', 'problem', 'complaint', 'concern',
            'unhappy', 'unsatisfied', 'poor', 'worst', 'fail', 'failed', 'failure',
            'slow', 'crashed', 'freeze', 'glitch', 'malfunction', 'defective'
        ]
        
        # Neutral/contextual keywords that might indicate issues
        self.issue_keywords = [
            'issue', 'problem', 'bug', 'error', 'not working', 'broken', 'help',
            'support', 'question', 'how to', 'unable to', 'cannot', 'can\'t',
            'trouble', 'difficulty', 'confused', 'unclear', 'need help'
        ]
    
    def analyze_sentiment(self, message: str) -> Tuple[Sentiment, float, str]:
        """
        Analyze sentiment of a message
        
        Args:
            message: The message content to analyze
            
        Returns:
            Tuple of (sentiment, confidence, reasoning)
        """
        if not message:
            return Sentiment.NEUTRAL, 0.0, "Empty message"
        
        message_lower = message.lower()
        
        # Count positive and negative keywords
        positive_count = sum(1 for word in self.positive_keywords if word in message_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in message_lower)
        issue_count = sum(1 for word in self.issue_keywords if word in message_lower)
        
        # Calculate confidence based on keyword matches
        total_keywords = positive_count + negative_count
        if total_keywords == 0:
            # If no sentiment keywords but has issue keywords, classify as negative
            if issue_count > 0:
                return Sentiment.NEGATIVE, 0.6, f"Contains {issue_count} issue-related keywords"
            else:
                return Sentiment.NEUTRAL, 0.3, "No clear sentiment indicators"
        
        # Determine sentiment based on keyword counts
        if positive_count > negative_count:
            confidence = min(positive_count / (positive_count + negative_count), 1.0)
            reasoning = f"Positive keywords: {positive_count}, Negative keywords: {negative_count}"
            return Sentiment.POSITIVE, confidence, reasoning
        elif negative_count > positive_count:
            confidence = min(negative_count / (positive_count + negative_count), 1.0)
            reasoning = f"Negative keywords: {negative_count}, Positive keywords: {positive_count}"
            return Sentiment.NEGATIVE, confidence, reasoning
        else:
            # Equal counts or mixed sentiment
            if issue_count > 0:
                return Sentiment.NEGATIVE, 0.5, f"Mixed sentiment but contains {issue_count} issue keywords"
            else:
                return Sentiment.NEUTRAL, 0.4, f"Mixed sentiment: {positive_count} positive, {negative_count} negative keywords"


class JiraTicketGenerator:
    """Generate JIRA ticket numbers for negative feedback"""
    
    def __init__(self):
        self.ticket_counter = 613400  # Starting from a base number
    
    def generate_ticket(self) -> str:
        """Generate a new JIRA ticket number"""
        self.ticket_counter += 1
        return f"JIRA-{self.ticket_counter}"
    
    def get_ticket_for_message(self, message_id: str) -> str:
        """
        Get or generate a JIRA ticket for a specific message
        This ensures the same message always gets the same ticket number
        """
        # In a real implementation, you might want to store this mapping in a database
        # For now, we'll generate based on message ID hash
        import hashlib
        hash_value = int(hashlib.md5(message_id.encode()).hexdigest()[:6], 16)
        ticket_number = 613400 + (hash_value % 1000)  # Generate in range 613401-614400
        return f"JIRA-{ticket_number}"


class SlackReplySystem:
    """Main system for handling automatic replies to all-feedforward channel"""
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize the reply system
        
        Args:
            bot_token: Slack bot token. If None, will try to get from environment
        """
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("Slack bot token is required. Set SLACK_BOT_TOKEN in environment or pass as parameter.")
        
        self.client = AsyncWebClient(token=self.bot_token)
        self.classifier = EnhancedMessageClassifier()
        
        # Channel configuration
        self.target_channel_id = "C09KQHTCGFR"  # all-feedforward channel ID
        self.target_channel_name = "all-feedforward"
        
        # Track processed messages to avoid duplicate replies
        self.processed_messages = set()
        self.processed_messages_file = "processed_messages.txt"
        self.load_processed_messages()
        
        # Reply templates
        self.positive_reply = "Thank you for your kind words! I'm glad you found our app helpful and appreciate your feedback!"
        self.negative_reply_template = "Thank you for your feedback! We're a customer-centric organization and truly appreciate you sharing your concern. We've logged it as {jira_ticket}, and our team is actively working on it. You can track your ticket's progress here: https://jira.example.com/browse/{jira_ticket}."
        self.neutral_reply = "Thank you for your feedback! We appreciate you taking the time to share your thoughts with us."
        
        logger.info(f"SlackReplySystem initialized for channel {self.target_channel_name} ({self.target_channel_id})")
    
    def load_processed_messages(self):
        """Load previously processed messages from file"""
        try:
            if os.path.exists(self.processed_messages_file):
                with open(self.processed_messages_file, 'r') as f:
                    for line in f:
                        message_ts = line.strip()
                        if message_ts:
                            self.processed_messages.add(message_ts)
                logger.info(f"Loaded {len(self.processed_messages)} previously processed messages")
        except Exception as e:
            logger.error(f"Error loading processed messages: {e}")
    
    def save_processed_message(self, message_ts: str):
        """Save a processed message to file"""
        try:
            with open(self.processed_messages_file, 'a') as f:
                f.write(f"{message_ts}\n")
        except Exception as e:
            logger.error(f"Error saving processed message: {e}")
    
    async def validate_channel_access(self) -> bool:
        """Validate that we can access the target channel"""
        try:
            response = await self.client.conversations_info(channel=self.target_channel_id)
            if response.get("ok"):
                channel_info = response["channel"]
                logger.info(f"Successfully validated access to channel: {channel_info.get('name', 'unknown')}")
                return True
            else:
                logger.error(f"Failed to validate channel access: {response.get('error', 'Unknown error')}")
                return False
        except SlackApiError as e:
            logger.error(f"Error validating channel access: {e}")
            return False
    
    async def fetch_recent_messages(self, limit: int = 50) -> List[Dict]:
        """
        Fetch recent messages from the all-feedforward channel
        
        Args:
            limit: Maximum number of messages to fetch
            
        Returns:
            List of message dictionaries
        """
        try:
            response = await self.client.conversations_history(
                channel=self.target_channel_id,
                limit=limit
            )
            
            if response.get("ok"):
                messages = response.get("messages", [])
                logger.info(f"Fetched {len(messages)} messages from {self.target_channel_name}")
                return messages
            else:
                logger.error(f"Failed to fetch messages: {response.get('error', 'Unknown error')}")
                return []
                
        except SlackApiError as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def should_reply_to_message(self, message: Dict) -> bool:
        """
        Determine if we should reply to a message
        
        Args:
            message: Slack message dictionary
            
        Returns:
            True if we should reply, False otherwise
        """
        # Skip if already processed
        message_ts = message.get("ts")
        if message_ts in self.processed_messages:
            return False
        
        # Skip bot messages (but allow our own bot to reply to user messages)
        if message.get("bot_id") or message.get("subtype") == "bot_message":
            return False
        
        # Skip messages without text
        if not message.get("text"):
            return False
        
        # Skip messages from our own bot
        user = message.get("user")
        if user and user.startswith("B"):  # Bot user IDs start with B
            return False
        
        # Allow replies to messages in threads - we want to reply to all user messages
        # regardless of whether they're in threads or not
        
        return True
    
    async def post_reply(self, original_message_ts: str, reply_text: str, jira_ticket: Optional[str] = None) -> ReplyResult:
        """
        Post a reply to a message in the same thread
        
        Args:
            original_message_ts: Timestamp of the original message
            reply_text: Text of the reply
            jira_ticket: JIRA ticket number (for negative feedback)
            
        Returns:
            ReplyResult with success status and details
        """
        try:
            response = await self.client.chat_postMessage(
                channel=self.target_channel_id,
                text=reply_text,
                thread_ts=original_message_ts  # This makes it a reply in the same thread
            )
            
            if response.get("ok"):
                reply_ts = response.get("ts")
                logger.info(f"Successfully posted reply to message {original_message_ts}: {reply_ts}")
                return ReplyResult(
                    success=True,
                    message_ts=reply_ts,
                    original_message_ts=original_message_ts,
                    jira_ticket=jira_ticket
                )
            else:
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Failed to post reply: {error_msg}")
                return ReplyResult(
                    success=False,
                    error=error_msg,
                    original_message_ts=original_message_ts,
                    jira_ticket=jira_ticket
                )
                
        except SlackApiError as e:
            logger.error(f"Slack API error posting reply: {e}")
            return ReplyResult(
                success=False,
                error=f"Slack API error: {e}",
                original_message_ts=original_message_ts,
                jira_ticket=jira_ticket
            )
    
    async def process_message(self, message: Dict) -> Optional[ReplyResult]:
        """
        Process a single message and reply if appropriate
        
        Args:
            message: Slack message dictionary
            
        Returns:
            ReplyResult if a reply was posted, None otherwise
        """
        if not self.should_reply_to_message(message):
            return None
        
        message_ts = message.get("ts")
        message_text = message.get("text", "")
        user = message.get("user", "unknown")
        
        logger.info(f"Processing message from user {user}: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
        
        # Classify the message using the enhanced classifier
        classification = self.classifier.classify_message(message_text)
        logger.info(f"Classification: {classification.level_1_category} -> {classification.level_2_category}")
        logger.info(f"Sentiment: {classification.sentiment} (confidence: {classification.confidence:.2f})")
        logger.info(f"Slack Channel: {classification.slack_channel}")
        logger.info(f"JIRA Ticket: {classification.jira_ticket}")
        
        # Generate reply based on sentiment
        reply_text = None
        jira_ticket = classification.jira_ticket
        
        if classification.sentiment == "positive":
            reply_text = self.positive_reply
            logger.info("Using positive reply template")
        elif classification.sentiment == "negative":
            reply_text = self.negative_reply_template.format(jira_ticket=jira_ticket)
            logger.info(f"Using negative reply template with JIRA ticket: {jira_ticket}")
        else:  # neutral
            reply_text = self.neutral_reply
            logger.info("Using neutral reply template")
        
        if reply_text:
            # Post the reply in thread
            result = await self.post_reply(message_ts, reply_text, jira_ticket)
            
            if result.success:
                # Mark message as processed
                self.processed_messages.add(message_ts)
                self.save_processed_message(message_ts)
                logger.info(f"Successfully replied to message {message_ts}")
                
                # If there's a specific Slack channel for this classification, post there too
                if classification.slack_channel and classification.slack_channel != "":
                    await self.post_to_classification_channel(message_text, classification, user)
            else:
                logger.error(f"Failed to reply to message {message_ts}: {result.error}")
            
            return result
        
        return None
    
    async def post_to_classification_channel(self, original_message: str, classification, user: str) -> bool:
        """
        Post the classified message to the appropriate Slack channel
        
        Args:
            original_message: The original message content
            classification: ClassificationResult object
            user: Original user who sent the message
            
        Returns:
            True if posted successfully, False otherwise
        """
        try:
            # Create a formatted message for the classification channel
            formatted_message = f"""📝 **New Feedback Classification**

**Category:** {classification.level_1_category} -> {classification.level_2_category}
**JIRA Ticket:** {classification.jira_ticket}
**Sentiment:** {classification.sentiment.title()}
**Original User:** <@{user}>

**Original Message:**
> {original_message}

**Reasoning:** {classification.reasoning}"""

            # Post to the classification channel
            response = await self.client.chat_postMessage(
                channel=classification.slack_channel,
                text=formatted_message,
                blocks=[
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📝 New Feedback - {classification.jira_ticket}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Category:* {classification.level_1_category}\n*Sub-category:* {classification.level_2_category}\n*JIRA Ticket:* {classification.jira_ticket}\n*Sentiment:* {classification.sentiment.title()}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Original User:* <@{user}>\n*Source:* all-feedforward channel"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Original Message:*\n```{original_message[:1000]}```"
                        }
                    }
                ]
            )
            
            if response.get("ok"):
                logger.info(f"Successfully posted to classification channel: {classification.slack_channel}")
                return True
            else:
                logger.error(f"Failed to post to classification channel: {response.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting to classification channel: {e}")
            return False
    
    async def process_recent_messages(self, limit: int = 50) -> List[ReplyResult]:
        """
        Process recent messages and reply to appropriate ones
        
        Args:
            limit: Maximum number of recent messages to check
            
        Returns:
            List of ReplyResult objects for messages that were replied to
        """
        logger.info(f"Processing recent messages from {self.target_channel_name}")
        
        # Validate channel access first
        if not await self.validate_channel_access():
            logger.error("Cannot access target channel, aborting")
            return []
        
        # Fetch recent messages
        messages = await self.fetch_recent_messages(limit)
        if not messages:
            logger.info("No messages found to process")
            return []
        
        # Process each message
        results = []
        for message in messages:
            try:
                result = await self.process_message(message)
                if result:
                    results.append(result)
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error processing message {message.get('ts', 'unknown')}: {e}")
        
        logger.info(f"Processed {len(messages)} messages, posted {len(results)} replies")
        return results
    
    async def run_continuous_monitoring(self, check_interval: int = 60):
        """
        Run continuous monitoring of the channel for new messages
        
        Args:
            check_interval: Seconds between checks for new messages
        """
        logger.info(f"Starting continuous monitoring of {self.target_channel_name} (checking every {check_interval}s)")
        
        while True:
            try:
                await self.process_recent_messages(limit=20)  # Check last 20 messages
                await asyncio.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(check_interval)  # Wait before retrying
    
    async def close(self):
        """Close the Slack client connection"""
        # AsyncWebClient doesn't have a close method
        pass


# Convenience functions for simple usage
async def reply_to_recent_messages(limit: int = 50) -> List[ReplyResult]:
    """
    Reply to recent messages in the all-feedforward channel
    
    Args:
        limit: Maximum number of recent messages to check
        
    Returns:
        List of ReplyResult objects for messages that were replied to
    """
    reply_system = SlackReplySystem()
    try:
        results = await reply_system.process_recent_messages(limit)
        return results
    finally:
        await reply_system.close()


async def start_monitoring(check_interval: int = 60):
    """
    Start continuous monitoring of the all-feedforward channel
    
    Args:
        check_interval: Seconds between checks for new messages
    """
    reply_system = SlackReplySystem()
    try:
        await reply_system.run_continuous_monitoring(check_interval)
    finally:
        await reply_system.close()


if __name__ == "__main__":
    # Test the reply system
    import asyncio
    
    async def test_reply_system():
        """Test function for the reply system"""
        try:
            reply_system = SlackReplySystem()
            
            # Test channel access
            if await reply_system.validate_channel_access():
                print("✅ Successfully connected to all-feedforward channel")
                
                # Process recent messages
                results = await reply_system.process_recent_messages(limit=10)
                print(f"📝 Processed messages and posted {len(results)} replies")
                
                for result in results:
                    if result.success:
                        print(f"✅ Reply posted: {result.message_ts} (JIRA: {result.jira_ticket})")
                    else:
                        print(f"❌ Reply failed: {result.error}")
            else:
                print("❌ Failed to connect to all-feedforward channel")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Run test
    asyncio.run(test_reply_system())
