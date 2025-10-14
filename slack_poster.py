"""
Slack Integration Module for Posting Classified Messages

This module handles posting classified messages to appropriate Slack channels
based on the classification results.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import aiohttp
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv('env.local')

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage:
    """Represents a message to be posted to Slack"""
    channel: str
    text: str
    blocks: Optional[List[Dict]] = None
    attachments: Optional[List[Dict]] = None
    thread_ts: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class PostResult:
    """Result of posting a message to Slack"""
    success: bool
    message_ts: Optional[str] = None
    error: Optional[str] = None
    channel: Optional[str] = None
    jira_ticket: Optional[str] = None


class SlackPoster:
    """Handles posting messages to Slack channels"""
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Slack poster
        
        Args:
            bot_token: Slack bot token. If None, will try to get from environment
        """
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        if not self.bot_token:
            raise ValueError("Slack bot token is required. Set SLACK_BOT_TOKEN in environment or pass as parameter.")
        
        self.client = AsyncWebClient(token=self.bot_token)
        self.rate_limit_delay = 1.0  # Delay between requests to avoid rate limits
        
        # Channel validation cache
        self._channel_cache = {}
        
    async def validate_channel(self, channel: str) -> bool:
        """
        Validate if a channel exists and is accessible
        
        Args:
            channel: Channel name or ID (e.g., "#help-cashout-experience" or "C1234567890")
            
        Returns:
            True if channel is valid and accessible, False otherwise
        """
        if not channel:
            return False
            
        # Check cache first
        if channel in self._channel_cache:
            return self._channel_cache[channel]
        
        try:
            # Remove # if present for API call
            channel_id = channel.lstrip('#')
            
            # Try to get channel info
            response = await self.client.conversations_info(channel=channel_id)
            
            is_valid = response.get("ok", False)
            self._channel_cache[channel] = is_valid
            
            return is_valid
            
        except SlackApiError as e:
            # If channel validation fails, assume it's valid if it looks like a channel ID
            if channel.startswith('C') and len(channel) > 8:
                logger.info(f"Channel validation failed for {channel}, but assuming valid (channel ID format)")
                self._channel_cache[channel] = True
                return True
            else:
                logger.warning(f"Channel validation failed for {channel}: {e}")
                self._channel_cache[channel] = False
                return False
        except Exception as e:
            logger.error(f"Unexpected error validating channel {channel}: {e}")
            self._channel_cache[channel] = False
            return False
    
    async def get_channel_id(self, channel: str) -> Optional[str]:
        """
        Get the channel ID for a channel name
        
        Args:
            channel: Channel name (e.g., "#help-cashout-experience")
            
        Returns:
            Channel ID if found, None otherwise
        """
        if not channel:
            return None
            
        try:
            # Remove # if present
            channel_name = channel.lstrip('#')
            
            # List all channels and find the one we want
            response = await self.client.conversations_list(types="public_channel,private_channel")
            
            if response.get("ok"):
                for ch in response["channels"]:
                    if ch["name"] == channel_name:
                        return ch["id"]
            
            return None
            
        except SlackApiError as e:
            logger.error(f"Error getting channel ID for {channel}: {e}")
            return None
    
    def create_message_blocks(self, original_message: str, classification: Dict, 
                            source_info: Optional[Dict] = None) -> List[Dict]:
        """
        Create rich message blocks for Slack
        
        Args:
            original_message: The original message content
            classification: Classification result dictionary
            source_info: Additional source information (author, platform, etc.)
            
        Returns:
            List of Slack block elements
        """
        blocks = []
        
        # Header block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📝 New Feedback - {classification.get('jira_ticket', 'N/A')}"
            }
        })
        
        # Classification info
        classification_text = f"*Category:* {classification.get('level_1_category', 'N/A')}\n"
        classification_text += f"*Sub-category:* {classification.get('level_2_category', 'N/A')}\n"
        classification_text += f"*JIRA Ticket:* {classification.get('jira_ticket', 'N/A')}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": classification_text
            }
        })
        
        # Source information
        if source_info:
            source_text = f"*Source:* {source_info.get('source', 'Unknown')}\n"
            if source_info.get('author'):
                source_text += f"*Author:* {source_info.get('author')}\n"
            if source_info.get('platform'):
                source_text += f"*Platform:* {source_info.get('platform')}\n"
            if source_info.get('timestamp'):
                source_text += f"*Time:* {source_info.get('timestamp')}"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": source_text
                }
            })
        
        # Original message
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Original Message:*\n```{original_message[:1000]}```"  # Limit length
            }
        })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View JIRA"
                    },
                    "url": f"https://your-domain.atlassian.net/browse/{classification.get('jira_ticket', '')}",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Mark as Processed"
                    },
                    "action_id": "mark_processed",
                    "value": classification.get('jira_ticket', '')
                }
            ]
        })
        
        return blocks
    
    async def post_message(self, slack_message: SlackMessage) -> PostResult:
        """
        Post a message to Slack
        
        Args:
            slack_message: SlackMessage object containing message details
            
        Returns:
            PostResult with success status and details
        """
        try:
            # Validate channel
            if not await self.validate_channel(slack_message.channel):
                return PostResult(
                    success=False,
                    error=f"Invalid or inaccessible channel: {slack_message.channel}",
                    channel=slack_message.channel
                )
            
            # Prepare message data
            message_data = {
                "channel": slack_message.channel,
                "text": slack_message.text
            }
            
            if slack_message.blocks:
                message_data["blocks"] = json.dumps(slack_message.blocks)
            
            if slack_message.attachments:
                message_data["attachments"] = json.dumps(slack_message.attachments)
            
            if slack_message.thread_ts:
                message_data["thread_ts"] = slack_message.thread_ts
            
            # Post the message
            response = await self.client.chat_postMessage(**message_data)
            
            if response.get("ok"):
                return PostResult(
                    success=True,
                    message_ts=response["ts"],
                    channel=slack_message.channel,
                    jira_ticket=slack_message.metadata.get("jira_ticket") if slack_message.metadata else None
                )
            else:
                return PostResult(
                    success=False,
                    error=f"Slack API error: {response.get('error', 'Unknown error')}",
                    channel=slack_message.channel
                )
                
        except SlackApiError as e:
            logger.error(f"Slack API error posting to {slack_message.channel}: {e}")
            return PostResult(
                success=False,
                error=f"Slack API error: {e}",
                channel=slack_message.channel
            )
        except Exception as e:
            logger.error(f"Unexpected error posting to {slack_message.channel}: {e}")
            return PostResult(
                success=False,
                error=f"Unexpected error: {e}",
                channel=slack_message.channel
            )
    
    async def post_classified_message(self, original_message: str, classification: Dict, 
                                    source_info: Optional[Dict] = None) -> PostResult:
        """
        Post a classified message to the appropriate Slack channel
        
        Args:
            original_message: The original message content
            classification: Classification result dictionary
            source_info: Additional source information
            
        Returns:
            PostResult with success status and details
        """
        channel = classification.get('slack_channel', '')
        
        if not channel:
            return PostResult(
                success=False,
                error="No Slack channel specified in classification",
                jira_ticket=classification.get('jira_ticket')
            )
        
        # Create rich message blocks
        blocks = self.create_message_blocks(original_message, classification, source_info)
        
        # Create Slack message
        slack_message = SlackMessage(
            channel=channel,
            text=f"New feedback classified as {classification.get('level_1_category', 'Unknown')}",
            blocks=blocks,
            metadata={
                "jira_ticket": classification.get('jira_ticket'),
                "classification": classification
            }
        )
        
        # Post the message
        return await self.post_message(slack_message)
    
    async def post_batch_messages(self, messages: List[Tuple[str, Dict, Optional[Dict]]]) -> List[PostResult]:
        """
        Post multiple classified messages to Slack
        
        Args:
            messages: List of tuples containing (original_message, classification, source_info)
            
        Returns:
            List of PostResult objects
        """
        results = []
        
        for original_message, classification, source_info in messages:
            result = await self.post_classified_message(original_message, classification, source_info)
            results.append(result)
            
            # Rate limiting
            if len(results) < len(messages):  # Don't delay after the last message
                await asyncio.sleep(self.rate_limit_delay)
        
        return results
    
    async def update_message_status(self, channel: str, message_ts: str, 
                                  status: str, jira_ticket: Optional[str] = None) -> bool:
        """
        Update a message with processing status
        
        Args:
            channel: Channel where the message was posted
            message_ts: Timestamp of the original message
            status: New status (e.g., "processed", "escalated")
            jira_ticket: JIRA ticket ID if available
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            status_text = f"✅ Status: {status.title()}"
            if jira_ticket:
                status_text += f" | JIRA: {jira_ticket}"
            
            response = await self.client.chat_postMessage(
                channel=channel,
                text=status_text,
                thread_ts=message_ts
            )
            
            return response.get("ok", False)
            
        except SlackApiError as e:
            logger.error(f"Error updating message status: {e}")
            return False
    
    async def get_channel_members(self, channel: str) -> List[str]:
        """
        Get list of members in a channel
        
        Args:
            channel: Channel name or ID
            
        Returns:
            List of user IDs in the channel
        """
        try:
            channel_id = channel.lstrip('#')
            response = await self.client.conversations_members(channel=channel_id)
            
            if response.get("ok"):
                return response.get("members", [])
            
            return []
            
        except SlackApiError as e:
            logger.error(f"Error getting channel members for {channel}: {e}")
            return []
    
    async def close(self):
        """Close the Slack client connection"""
        # AsyncWebClient doesn't have a close method
        pass


# Convenience functions for simple usage
async def post_single_message(message: str, classification: Dict, 
                            source_info: Optional[Dict] = None) -> PostResult:
    """
    Post a single classified message to Slack
    
    Args:
        message: Original message content
        classification: Classification result
        source_info: Source information
        
    Returns:
        PostResult with success status
    """
    poster = SlackPoster()
    try:
        result = await poster.post_classified_message(message, classification, source_info)
        return result
    finally:
        await poster.close()


async def post_batch_messages(messages: List[Tuple[str, Dict, Optional[Dict]]]) -> List[PostResult]:
    """
    Post multiple classified messages to Slack
    
    Args:
        messages: List of (message, classification, source_info) tuples
        
    Returns:
        List of PostResult objects
    """
    poster = SlackPoster()
    try:
        results = await poster.post_batch_messages(messages)
        return results
    finally:
        await poster.close()


if __name__ == "__main__":
    # Test the Slack poster
    import asyncio
    
    async def test_slack_poster():
        """Test function for Slack poster"""
        try:
            poster = SlackPoster()
            
            # Test channel validation
            test_channel = "#help-cashout-experience"
            is_valid = await poster.validate_channel(test_channel)
            print(f"Channel {test_channel} is valid: {is_valid}")
            
            # Test posting a message
            test_classification = {
                "level_1_category": "Payments and Cash Out",
                "level_2_category": "Cash Out",
                "slack_channel": "#help-cashout-experience",
                "jira_ticket": "JIRA-123456"
            }
            
            test_message = "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!"
            test_source = {
                "source": "Reddit",
                "author": "test_user",
                "platform": "reddit",
                "timestamp": datetime.now().isoformat()
            }
            
            result = await poster.post_classified_message(test_message, test_classification, test_source)
            print(f"Post result: {result}")
            
            # AsyncWebClient doesn't have a close method
            pass
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    asyncio.run(test_slack_poster())

