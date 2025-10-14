#!/usr/bin/env python3
"""
Run the Enhanced Message Processor with Reply System

This script runs the enhanced message processor that includes automatic replies
to messages in the all-feedforward channel based on sentiment analysis.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from enhanced_message_processor import (
    EnhancedMessageProcessor, 
    process_recent_messages_with_replies, 
    start_continuous_processing_with_replies
)
from slack_poster import SlackPoster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to run the enhanced processor"""
    parser = argparse.ArgumentParser(description='Run Enhanced Message Processor with Reply System')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once',
                       help='Run mode: once (process recent messages) or continuous (monitor for new messages)')
    parser.add_argument('--limit', type=int, default=50,
                       help='Number of recent messages to check (for once mode)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Check interval in seconds (for continuous mode)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of messages to process in each batch (for continuous mode)')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode (validate connection only)')
    parser.add_argument('--disable-replies', action='store_true',
                       help='Disable the reply system (only process and post to team channels)')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Enhanced Message Processor in {args.mode} mode")
    logger.info(f"Reply system: {'disabled' if args.disable_replies else 'enabled'}")
    
    try:
        if args.test:
            # Test mode - just validate connections
            logger.info("Running in test mode - validating connections only")
            
            # Test Slack poster
            try:
                slack_poster = SlackPoster()
                print("✅ Slack poster initialized successfully")
            except Exception as e:
                print(f"❌ Slack poster initialization failed: {e}")
                return 1
            
            # Test reply system
            try:
                processor = EnhancedMessageProcessor(slack_poster=slack_poster)
                if args.disable_replies:
                    processor.disable_reply_system()
                
                if await processor.reply_system.validate_channel_access():
                    print("✅ Reply system connection test successful!")
                else:
                    print("❌ Reply system connection test failed!")
                    return 1
                
                await processor.close()
                print("✅ All connection tests passed!")
                return 0
                
            except Exception as e:
                print(f"❌ Reply system test failed: {e}")
                return 1
        
        elif args.mode == 'once':
            # Process recent messages once
            logger.info(f"Processing recent {args.limit} messages")
            print(f"📝 Processing recent {args.limit} messages...")
            
            results = await process_recent_messages_with_replies(limit=args.limit)
            
            # Display results
            print(f"\n📊 Processing Results:")
            print(f"   Total messages: {results['total_messages']}")
            print(f"   Processed successfully: {results['processed_successfully']}")
            print(f"   Failed processing: {results['failed_processing']}")
            print(f"   Replies posted: {results['replies_posted']}")
            print(f"   Reply failures: {results['reply_failures']}")
            print(f"   JIRA tickets generated: {results['jira_tickets_generated']}")
            
            # Show details for each message
            if results['messages']:
                print(f"\n📝 Message Details:")
                for msg in results['messages']:
                    print(f"\n   Message {msg['id']}:")
                    print(f"     Content: {msg['content']}")
                    print(f"     Source: {msg['source']}")
                    print(f"     Channel: {msg['channel']}")
                    print(f"     Processed: {'✅' if msg['processed'] else '❌'}")
                    if msg.get('reply_posted'):
                        print(f"     Reply: ✅ Posted")
                        if msg.get('jira_ticket'):
                            print(f"     JIRA: 🎫 {msg['jira_ticket']}")
                    if msg.get('error'):
                        print(f"     Error: ❌ {msg['error']}")
            
            return 0
        
        elif args.mode == 'continuous':
            # Continuous processing
            logger.info(f"Starting continuous processing (checking every {args.interval}s, batch size: {args.batch_size})")
            print(f"🔄 Starting continuous processing...")
            print(f"   Check interval: {args.interval}s")
            print(f"   Batch size: {args.batch_size}")
            print(f"   Reply system: {'disabled' if args.disable_replies else 'enabled'}")
            print("Press Ctrl+C to stop")
            
            await start_continuous_processing_with_replies(
                check_interval=args.interval, 
                batch_size=args.batch_size
            )
            return 0
    
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        print("\n👋 Stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error running enhanced processor: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
