"""
Message Processor - Main Integration Script

This script fetches messages from the unified_messages.db database,
classifies them using the message classifier, and posts them to
appropriate Slack channels.
"""

import os
import sys
import sqlite3
import json
import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import argparse

# Apply SSL bypass for corporate networks
try:
    from ssl_bypass_fix import apply_ssl_bypass
    apply_ssl_bypass()
except ImportError:
    pass

# Import our custom modules
from message_classifier import MessageClassifier, ClassificationResult
from slack_poster import SlackPoster, PostResult

# Load environment variables
from dotenv import load_dotenv
load_dotenv('config/env.local')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('message_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class MessageRecord:
    """Represents a message record from the database"""
    id: str
    source: str
    platform: str
    content: str
    title: Optional[str]
    author: str
    author_id: Optional[str]
    timestamp: str
    url: Optional[str]
    subreddit: Optional[str]
    channel_name: Optional[str]
    rating: Optional[int]
    processed: bool
    created_at: str
    raw_data: Optional[str]


class MessageProcessor:
    """Main processor for handling message classification and Slack posting"""
    
    def __init__(self, db_path: str = "unified_messages.db"):
        """
        Initialize the message processor
        
        Args:
            db_path: Path to the unified messages database
        """
        self.db_path = db_path
        self.classifier = MessageClassifier()
        self.slack_poster = None
        self.processed_count = 0
        self.error_count = 0
        
        # Initialize Slack poster
        try:
            self.slack_poster = SlackPoster()
            logger.info("Slack poster initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Slack poster: {e}")
            self.slack_poster = None
    
    def get_unprocessed_messages(self, limit: Optional[int] = None) -> List[MessageRecord]:
        """
        Fetch unprocessed messages from the database
        
        Args:
            limit: Maximum number of messages to fetch (None for all messages)
            
        Returns:
            List of MessageRecord objects
        """
        messages = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Query for unprocessed messages
                if limit is not None:
                    query = """
                        SELECT id, source, platform, content, title, author, author_id,
                               timestamp, url, subreddit, channel_name, rating, processed,
                               created_at, raw_data
                        FROM messages 
                        WHERE processed = FALSE 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    """
                    cursor.execute(query, (limit,))
                else:
                    query = """
                        SELECT id, source, platform, content, title, author, author_id,
                               timestamp, url, subreddit, channel_name, rating, processed,
                               created_at, raw_data
                        FROM messages 
                        WHERE processed = FALSE 
                        ORDER BY created_at ASC
                    """
                    cursor.execute(query)
                
                rows = cursor.fetchall()
                
                for row in rows:
                    message = MessageRecord(
                        id=row[0],
                        source=row[1],
                        platform=row[2],
                        content=row[3],
                        title=row[4],
                        author=row[5],
                        author_id=row[6],
                        timestamp=row[7],
                        url=row[8],
                        subreddit=row[9],
                        channel_name=row[10],
                        rating=row[11],
                        processed=bool(row[12]),
                        created_at=row[13],
                        raw_data=row[14]
                    )
                    messages.append(message)
                
                logger.info(f"Fetched {len(messages)} unprocessed messages")
                
        except sqlite3.Error as e:
            logger.error(f"Database error fetching messages: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching messages: {e}")
        
        return messages
    
    def classify_message(self, message: MessageRecord) -> ClassificationResult:
        """
        Classify a message using the classifier
        
        Args:
            message: MessageRecord to classify
            
        Returns:
            ClassificationResult with category mappings
        """
        # Combine title and content for classification
        full_text = ""
        if message.title:
            full_text += f"{message.title}\n"
        full_text += message.content
        
        return self.classifier.classify_message(full_text)
    
    def create_source_info(self, message: MessageRecord) -> Dict:
        """
        Create source information dictionary for Slack posting
        
        Args:
            message: MessageRecord to extract source info from
            
        Returns:
            Dictionary with source information
        """
        source_info = {
            "source": message.source,
            "author": message.author,
            "platform": message.platform,
            "timestamp": message.timestamp,
            "message_id": message.id
        }
        
        # Add platform-specific information
        if message.subreddit:
            source_info["subreddit"] = message.subreddit
        
        if message.channel_name:
            source_info["channel"] = message.channel_name
        
        if message.url:
            source_info["url"] = message.url
        
        if message.rating:
            source_info["rating"] = message.rating
        
        return source_info
    
    async def process_single_message(self, message: MessageRecord) -> Tuple[bool, Optional[str]]:
        """
        Process a single message: classify and post to Slack
        
        Args:
            message: MessageRecord to process
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Classify the message
            classification = self.classify_message(message)
            logger.info(f"Classified message {message.id}: {classification.level_1_category} -> {classification.level_2_category}")
            
            # Create source info
            source_info = self.create_source_info(message)
            
            # Post to Slack if we have a valid channel
            if self.slack_poster and classification.slack_channel:
                # Combine title and content for the full message
                full_message = ""
                if message.title:
                    full_message += f"**{message.title}**\n\n"
                full_message += message.content
                
                result = await self.slack_poster.post_classified_message(
                    full_message, 
                    {
                        "level_1_category": classification.level_1_category,
                        "level_2_category": classification.level_2_category,
                        "slack_channel": classification.slack_channel,
                        "jira_ticket": classification.jira_ticket
                    },
                    source_info
                )
                
                if result.success:
                    logger.info(f"Successfully posted message {message.id} to {classification.slack_channel}")
                else:
                    logger.error(f"Failed to post message {message.id} to Slack: {result.error}")
                    return False, f"Slack posting failed: {result.error}"
            else:
                if not self.slack_poster:
                    logger.warning("Slack poster not available, skipping Slack posting")
                if not classification.slack_channel:
                    logger.warning(f"No Slack channel for message {message.id}, classification: {classification.level_2_category}")
            
            # Mark message as processed in database
            self.mark_message_processed(message.id, classification)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            return False, str(e)
    
    def mark_message_processed(self, message_id: str, classification: ClassificationResult):
        """
        Mark a message as processed in the database
        
        Args:
            message_id: ID of the message to mark as processed
            classification: Classification result to store
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update the message with classification results
                update_query = """
                    UPDATE messages 
                    SET processed = TRUE,
                        category = ?,
                        sentiment = ?,
                        updated_at = ?
                    WHERE id = ?
                """
                
                cursor.execute(update_query, (
                    classification.level_1_category,
                    "neutral",  # We could enhance this with sentiment analysis
                    datetime.now(timezone.utc).isoformat(),
                    message_id
                ))
                
                conn.commit()
                logger.debug(f"Marked message {message_id} as processed")
                
        except sqlite3.Error as e:
            logger.error(f"Database error marking message {message_id} as processed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error marking message {message_id} as processed: {e}")
    
    async def process_batch(self, messages: List[MessageRecord]) -> Dict:
        """
        Process a batch of messages
        
        Args:
            messages: List of MessageRecord objects to process
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {
            "total": len(messages),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        logger.info(f"Processing batch of {len(messages)} messages")
        
        for message in messages:
            try:
                success, error = await self.process_single_message(message)
                
                if success:
                    stats["successful"] += 1
                    self.processed_count += 1
                else:
                    stats["failed"] += 1
                    self.error_count += 1
                    stats["errors"].append({
                        "message_id": message.id,
                        "error": error
                    })
                
                # Rate limiting - small delay between messages
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Unexpected error processing message {message.id}: {e}")
                stats["failed"] += 1
                self.error_count += 1
                stats["errors"].append({
                    "message_id": message.id,
                    "error": str(e)
                })
        
        return stats
    
    async def run_processing_cycle(self, batch_size: Optional[int] = None) -> Dict:
        """
        Run a complete processing cycle
        
        Args:
            batch_size: Number of messages to process in this cycle (None for all messages)
            
        Returns:
            Dictionary with processing statistics
        """
        if batch_size is None:
            logger.info("Starting processing cycle for all unprocessed messages")
        else:
            logger.info(f"Starting processing cycle with batch size {batch_size}")
        
        # Fetch unprocessed messages
        messages = self.get_unprocessed_messages(batch_size)
        
        if not messages:
            logger.info("No unprocessed messages found")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }
        
        # Process the batch
        stats = await self.process_batch(messages)
        
        logger.info(f"Processing cycle completed: {stats['successful']}/{stats['total']} successful")
        
        return stats
    
    def get_processing_stats(self) -> Dict:
        """
        Get overall processing statistics
        
        Returns:
            Dictionary with processing statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total message count
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                # Get processed message count
                cursor.execute("SELECT COUNT(*) FROM messages WHERE processed = TRUE")
                processed_messages = cursor.fetchone()[0]
                
                # Get unprocessed message count
                unprocessed_messages = total_messages - processed_messages
                
                return {
                    "total_messages": total_messages,
                    "processed_messages": processed_messages,
                    "unprocessed_messages": unprocessed_messages,
                    "processing_rate": (processed_messages / total_messages * 100) if total_messages > 0 else 0,
                    "session_processed": self.processed_count,
                    "session_errors": self.error_count
                }
                
        except sqlite3.Error as e:
            logger.error(f"Database error getting stats: {e}")
            return {}
    
    async def close(self):
        """Close connections and cleanup"""
        if self.slack_poster:
            await self.slack_poster.close()


async def main():
    """Main function for running the message processor"""
    parser = argparse.ArgumentParser(description="Process and classify messages from unified database")
    parser.add_argument("--db-path", default="unified_messages.db", help="Path to the unified messages database")
    parser.add_argument("--batch-size", type=int, default=None, help="Number of messages to process in one batch (default: all messages)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously, checking for new messages")
    parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for continuous mode")
    parser.add_argument("--stats-only", action="store_true", help="Only show statistics, don't process messages")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = MessageProcessor(args.db_path)
    
    try:
        if args.stats_only:
            # Show statistics only
            stats = processor.get_processing_stats()
            print("\n=== Processing Statistics ===")
            print(f"Total messages: {stats.get('total_messages', 0)}")
            print(f"Processed messages: {stats.get('processed_messages', 0)}")
            print(f"Unprocessed messages: {stats.get('unprocessed_messages', 0)}")
            print(f"Processing rate: {stats.get('processing_rate', 0):.1f}%")
            print(f"Session processed: {stats.get('session_processed', 0)}")
            print(f"Session errors: {stats.get('session_errors', 0)}")
            return
        
        if args.continuous:
            # Continuous mode
            logger.info(f"Starting continuous processing mode (interval: {args.interval}s)")
            while True:
                try:
                    stats = await processor.run_processing_cycle(args.batch_size)
                    logger.info(f"Cycle completed: {stats['successful']}/{stats['total']} successful")
                    
                    if stats['total'] == 0:
                        logger.info("No messages to process, waiting...")
                    
                    await asyncio.sleep(args.interval)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping...")
                    break
                except Exception as e:
                    logger.error(f"Error in continuous mode: {e}")
                    await asyncio.sleep(args.interval)
        else:
            # Single run mode
            stats = await processor.run_processing_cycle(args.batch_size)
            print(f"\n=== Processing Results ===")
            print(f"Total messages: {stats['total']}")
            print(f"Successful: {stats['successful']}")
            print(f"Failed: {stats['failed']}")
            print(f"Skipped: {stats['skipped']}")
            
            if stats['errors']:
                print(f"\nErrors:")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error['message_id']}: {error['error']}")
                if len(stats['errors']) > 5:
                    print(f"  ... and {len(stats['errors']) - 5} more errors")
    
    finally:
        await processor.close()


if __name__ == "__main__":
    asyncio.run(main())

