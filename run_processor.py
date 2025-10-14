#!/usr/bin/env python3
"""
Simple script to run the message processor

This script provides an easy way to run the message processor with common options.
"""

import asyncio
import sys
import argparse
from message_processor import MessageProcessor


async def main():
    """Main function with simplified interface"""
    parser = argparse.ArgumentParser(description="Run the message processor")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once",
                       help="Run once or continuously")
    parser.add_argument("--count", type=int, default=10,
                       help="Number of messages to process (once mode)")
    parser.add_argument("--interval", type=int, default=300,
                       help="Interval in seconds for continuous mode")
    parser.add_argument("--stats", action="store_true",
                       help="Show statistics only")
    
    args = parser.parse_args()
    
    processor = MessageProcessor()
    
    try:
        if args.stats:
            # Show statistics
            stats = processor.get_processing_stats()
            print("\n📊 Processing Statistics")
            print("=" * 30)
            print(f"Total messages: {stats.get('total_messages', 0)}")
            print(f"Processed: {stats.get('processed_messages', 0)}")
            print(f"Unprocessed: {stats.get('unprocessed_messages', 0)}")
            print(f"Processing rate: {stats.get('processing_rate', 0):.1f}%")
            return
        
        if args.mode == "once":
            # Process messages once
            print(f"🔄 Processing {args.count} messages...")
            stats = await processor.run_processing_cycle(args.count)
            
            print(f"\n✅ Processing Complete")
            print(f"Total: {stats['total']}")
            print(f"Successful: {stats['successful']}")
            print(f"Failed: {stats['failed']}")
            
            if stats['errors']:
                print(f"\n❌ Errors:")
                for error in stats['errors'][:3]:
                    print(f"  - {error['error']}")
        
        elif args.mode == "continuous":
            # Continuous processing
            print(f"🔄 Starting continuous processing (interval: {args.interval}s)")
            print("Press Ctrl+C to stop")
            
            while True:
                try:
                    stats = await processor.run_processing_cycle(50)
                    if stats['total'] > 0:
                        print(f"Processed {stats['successful']}/{stats['total']} messages")
                    else:
                        print("No messages to process")
                    
                    await asyncio.sleep(args.interval)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Stopping...")
                    break
    
    finally:
        await processor.close()


if __name__ == "__main__":
    asyncio.run(main())

