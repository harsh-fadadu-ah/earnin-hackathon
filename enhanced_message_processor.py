"""
Enhanced Message Processor with Reply System Integration

This module extends the existing message processor to include automatic replies
to messages in the all-feedforward channel based on sentiment analysis.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Import existing modules
from message_processor import MessageProcessor, MessageRecord
from slack_reply_system import SlackReplySystem, Sentiment, ReplyResult

logger = logging.getLogger(__name__)


class EnhancedMessageProcessor(MessageProcessor):
    """Enhanced message processor with reply system integration"""
    
    def __init__(self, db_path: str = "unified_messages.db", slack_poster=None):
        """
        Initialize the enhanced message processor
        
        Args:
            db_path: Path to the unified messages database
            slack_poster: SlackPoster instance for posting to team channels
        """
        super().__init__(db_path, slack_poster)
        
        # Initialize the reply system
        self.reply_system = SlackReplySystem()
        self.reply_system_enabled = True
        
        logger.info("Enhanced Message Processor initialized with reply system")
    
    async def process_single_message_with_reply(self, message: MessageRecord) -> Tuple[bool, Optional[str], Optional[ReplyResult]]:
        """
        Process a single message: classify, post to team channels, and reply if from all-feedforward
        
        Args:
            message: MessageRecord to process
            
        Returns:
            Tuple of (success, error_message, reply_result)
        """
        try:
            # First, do the normal processing (classify and post to team channels)
            success, error = await self.process_single_message(message)
            
            reply_result = None
            
            # If this message is from the all-feedforward channel, also reply to it
            if (success and self.reply_system_enabled and 
                message.channel_name == "all-feedforward" and 
                message.source == "slack"):
                
                logger.info(f"Message {message.id} is from all-feedforward channel, processing for reply")
                
                # Create a mock Slack message dict for the reply system
                slack_message = {
                    "ts": str(int(datetime.fromisoformat(message.timestamp).timestamp())),
                    "text": message.content,
                    "user": message.author_id or "unknown",
                    "bot_id": None,
                    "subtype": None,
                    "thread_ts": None
                }
                
                # Process the message for reply
                reply_result = await self.reply_system.process_message(slack_message)
                
                if reply_result and reply_result.success:
                    logger.info(f"Successfully replied to message {message.id} in all-feedforward channel")
                elif reply_result:
                    logger.error(f"Failed to reply to message {message.id}: {reply_result.error}")
            
            return success, error, reply_result
            
        except Exception as e:
            logger.error(f"Error processing message {message.id} with reply: {e}")
            return False, str(e), None
    
    async def process_batch_with_replies(self, limit: Optional[int] = None) -> Dict:
        """
        Process a batch of messages with reply functionality
        
        Args:
            limit: Maximum number of messages to process
            
        Returns:
            Dictionary with processing results including reply statistics
        """
        logger.info(f"Processing batch of messages with reply system (limit: {limit})")
        
        # Get unprocessed messages
        messages = self.get_unprocessed_messages(limit)
        if not messages:
            logger.info("No unprocessed messages found")
            return {
                "total_messages": 0,
                "processed_successfully": 0,
                "failed_processing": 0,
                "replies_posted": 0,
                "reply_failures": 0,
                "jira_tickets_generated": 0
            }
        
        logger.info(f"Found {len(messages)} unprocessed messages")
        
        # Process each message
        results = {
            "total_messages": len(messages),
            "processed_successfully": 0,
            "failed_processing": 0,
            "replies_posted": 0,
            "reply_failures": 0,
            "jira_tickets_generated": 0,
            "messages": []
        }
        
        for message in messages:
            try:
                success, error, reply_result = await self.process_single_message_with_reply(message)
                
                message_result = {
                    "id": message.id,
                    "content": message.content[:100] + "..." if len(message.content) > 100 else message.content,
                    "source": message.source,
                    "channel": message.channel_name,
                    "processed": success,
                    "error": error,
                    "reply_posted": False,
                    "jira_ticket": None
                }
                
                if success:
                    results["processed_successfully"] += 1
                    
                    # Mark as processed in database
                    self.mark_message_processed(message.id)
                    
                    # Handle reply result
                    if reply_result:
                        if reply_result.success:
                            results["replies_posted"] += 1
                            message_result["reply_posted"] = True
                            if reply_result.jira_ticket:
                                results["jira_tickets_generated"] += 1
                                message_result["jira_ticket"] = reply_result.jira_ticket
                        else:
                            results["reply_failures"] += 1
                            message_result["reply_error"] = reply_result.error
                else:
                    results["failed_processing"] += 1
                
                results["messages"].append(message_result)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {e}")
                results["failed_processing"] += 1
                results["messages"].append({
                    "id": message.id,
                    "error": str(e),
                    "processed": False
                })
        
        logger.info(f"Batch processing complete: {results['processed_successfully']} successful, "
                   f"{results['failed_processing']} failed, {results['replies_posted']} replies posted")
        
        return results
    
    async def run_continuous_processing_with_replies(self, check_interval: int = 60, batch_size: int = 10):
        """
        Run continuous processing with reply functionality
        
        Args:
            check_interval: Seconds between processing batches
            batch_size: Number of messages to process in each batch
        """
        logger.info(f"Starting continuous processing with replies (interval: {check_interval}s, batch_size: {batch_size})")
        
        while True:
            try:
                # Process a batch of messages
                results = await self.process_batch_with_replies(limit=batch_size)
                
                if results["total_messages"] > 0:
                    logger.info(f"Processed {results['processed_successfully']} messages, "
                               f"posted {results['replies_posted']} replies, "
                               f"generated {results['jira_tickets_generated']} JIRA tickets")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Continuous processing stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous processing: {e}")
                await asyncio.sleep(check_interval)  # Wait before retrying
    
    def enable_reply_system(self):
        """Enable the reply system"""
        self.reply_system_enabled = True
        logger.info("Reply system enabled")
    
    def disable_reply_system(self):
        """Disable the reply system"""
        self.reply_system_enabled = False
        logger.info("Reply system disabled")
    
    async def close(self):
        """Close all connections"""
        await self.reply_system.close()
        if self.slack_poster:
            await self.slack_poster.close()


# Convenience functions
async def process_recent_messages_with_replies(limit: int = 50) -> Dict:
    """
    Process recent messages with reply functionality
    
    Args:
        limit: Maximum number of messages to process
        
    Returns:
        Dictionary with processing results
    """
    from slack_poster import SlackPoster
    
    # Initialize components
    slack_poster = SlackPoster()
    processor = EnhancedMessageProcessor(slack_poster=slack_poster)
    
    try:
        results = await processor.process_batch_with_replies(limit=limit)
        return results
    finally:
        await processor.close()


async def start_continuous_processing_with_replies(check_interval: int = 60, batch_size: int = 10):
    """
    Start continuous processing with reply functionality
    
    Args:
        check_interval: Seconds between processing batches
        batch_size: Number of messages to process in each batch
    """
    from slack_poster import SlackPoster
    
    # Initialize components
    slack_poster = SlackPoster()
    processor = EnhancedMessageProcessor(slack_poster=slack_poster)
    
    try:
        await processor.run_continuous_processing_with_replies(check_interval, batch_size)
    finally:
        await processor.close()


if __name__ == "__main__":
    # Test the enhanced processor
    import asyncio
    
    async def test_enhanced_processor():
        """Test function for the enhanced processor"""
        try:
            print("Testing Enhanced Message Processor with Reply System...")
            
            # Test processing recent messages
            results = await process_recent_messages_with_replies(limit=5)
            
            print(f"📊 Processing Results:")
            print(f"   Total messages: {results['total_messages']}")
            print(f"   Processed successfully: {results['processed_successfully']}")
            print(f"   Failed processing: {results['failed_processing']}")
            print(f"   Replies posted: {results['replies_posted']}")
            print(f"   Reply failures: {results['reply_failures']}")
            print(f"   JIRA tickets generated: {results['jira_tickets_generated']}")
            
            # Show details for each message
            for msg in results['messages']:
                print(f"\n📝 Message {msg['id']}:")
                print(f"   Content: {msg['content']}")
                print(f"   Source: {msg['source']}")
                print(f"   Channel: {msg['channel']}")
                print(f"   Processed: {msg['processed']}")
                if msg.get('reply_posted'):
                    print(f"   ✅ Reply posted")
                    if msg.get('jira_ticket'):
                        print(f"   🎫 JIRA Ticket: {msg['jira_ticket']}")
                if msg.get('error'):
                    print(f"   ❌ Error: {msg['error']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    # Run test
    asyncio.run(test_enhanced_processor())
