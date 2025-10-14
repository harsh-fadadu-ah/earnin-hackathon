#!/usr/bin/env python3
"""
Run the Slack Reply System

This script runs the automatic reply system for the all-feedforward channel.
It can be run once to process recent messages or continuously to monitor for new ones.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from slack_reply_system import SlackReplySystem, reply_to_recent_messages, start_monitoring

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('slack_reply_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main function to run the reply system"""
    parser = argparse.ArgumentParser(description='Run Slack Reply System for all-feedforward channel')
    parser.add_argument('--mode', choices=['once', 'continuous'], default='once',
                       help='Run mode: once (process recent messages) or continuous (monitor for new messages)')
    parser.add_argument('--limit', type=int, default=50,
                       help='Number of recent messages to check (for once mode)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Check interval in seconds (for continuous mode)')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode (validate connection only)')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Slack Reply System in {args.mode} mode")
    logger.info(f"Target channel: all-feedforward (C09KQHTCGFR)")
    
    try:
        if args.test:
            # Test mode - just validate connection
            logger.info("Running in test mode - validating connection only")
            reply_system = SlackReplySystem()
            
            if await reply_system.validate_channel_access():
                logger.info("✅ Successfully connected to all-feedforward channel")
                print("✅ Connection test successful!")
            else:
                logger.error("❌ Failed to connect to all-feedforward channel")
                print("❌ Connection test failed!")
                return 1
            
            await reply_system.close()
            return 0
        
        elif args.mode == 'once':
            # Process recent messages once
            logger.info(f"Processing recent {args.limit} messages")
            results = await reply_to_recent_messages(limit=args.limit)
            
            logger.info(f"Processed messages and posted {len(results)} replies")
            print(f"📝 Processed {len(results)} messages and posted replies")
            
            for result in results:
                if result.success:
                    logger.info(f"✅ Reply posted: {result.message_ts} (JIRA: {result.jira_ticket})")
                    print(f"✅ Reply posted to message {result.original_message_ts}")
                    if result.jira_ticket:
                        print(f"   JIRA Ticket: {result.jira_ticket}")
                else:
                    logger.error(f"❌ Reply failed: {result.error}")
                    print(f"❌ Reply failed: {result.error}")
            
            return 0
        
        elif args.mode == 'continuous':
            # Continuous monitoring
            logger.info(f"Starting continuous monitoring (checking every {args.interval}s)")
            print(f"🔄 Starting continuous monitoring (checking every {args.interval}s)")
            print("Press Ctrl+C to stop")
            
            await start_monitoring(check_interval=args.interval)
            return 0
    
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        print("\n👋 Stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error running reply system: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
