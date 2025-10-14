#!/usr/bin/env python3
"""
Test script to verify Slack message deduplication is working correctly
"""

import logging
from feedback_mcp_server_unified import slack_fetcher, db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_deduplication():
    """Test the deduplication functionality"""
    logger.info("🧪 Testing Slack message deduplication...")
    
    # Get initial count
    initial_stats = db.get_database_stats()
    initial_slack_count = initial_stats['by_source'].get('slack', 0)
    logger.info(f"Initial Slack messages in database: {initial_slack_count}")
    
    # Run auto-processing twice
    logger.info("Running auto-processing (first time)...")
    count1 = slack_fetcher.auto_process_new_reviews()
    logger.info(f"First run processed: {count1} messages")
    
    logger.info("Running auto-processing (second time)...")
    count2 = slack_fetcher.auto_process_new_reviews()
    logger.info(f"Second run processed: {count2} messages")
    
    # Get final count
    final_stats = db.get_database_stats()
    final_slack_count = final_stats['by_source'].get('slack', 0)
    logger.info(f"Final Slack messages in database: {final_slack_count}")
    
    # Verify deduplication worked
    if count2 == 0:
        logger.info("✅ Deduplication working correctly - no duplicate messages processed")
    else:
        logger.warning(f"⚠️ Deduplication may not be working - processed {count2} messages on second run")
    
    # Show the difference
    new_messages = final_slack_count - initial_slack_count
    logger.info(f"Total new messages added: {new_messages}")
    
    if new_messages == count1:
        logger.info("✅ Message count matches - deduplication working correctly")
    else:
        logger.warning(f"⚠️ Message count mismatch - expected {count1}, got {new_messages}")

if __name__ == "__main__":
    test_deduplication()
