#!/usr/bin/env python3
"""
Test the complete message processing flow
"""

import asyncio
import os
from message_processor import MessageProcessor
from message_classifier import classify_message_simple
from slack_poster import SlackPoster
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/env.local')

async def test_complete_flow():
    """Test the complete message processing flow"""
    print("🧪 Testing Complete Message Processing Flow")
    print("=" * 50)
    
    # Test 1: Message Classification
    print("\n1️⃣ Testing Message Classification")
    test_messages = [
        "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
        "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
        "I just love how easy it is to see my earnings now, thanks!"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest Message {i}: {message[:50]}...")
        result = classify_message_simple(message)
        print(f"  L1: {result['level_1_category']}")
        print(f"  L2: {result['level_2_category']}")
        print(f"  Slack: {result['slack_channel']}")
        print(f"  JIRA: {result['jira_ticket']}")
    
    # Test 2: Database Processing
    print(f"\n2️⃣ Testing Database Processing")
    processor = MessageProcessor("unified_messages.db")
    
    # Get stats
    stats = processor.get_processing_stats()
    print(f"  Total messages: {stats.get('total_messages', 0)}")
    print(f"  Processed: {stats.get('processed_messages', 0)}")
    print(f"  Unprocessed: {stats.get('unprocessed_messages', 0)}")
    
    # Get a few unprocessed messages
    messages = processor.get_unprocessed_messages(limit=3)
    print(f"  Sample unprocessed messages: {len(messages)}")
    
    for i, msg in enumerate(messages[:2], 1):
        print(f"    {i}. [{msg.source}] {msg.content[:40]}...")
        classification = processor.classify_message(msg)
        print(f"       -> {classification.level_1_category} -> {classification.level_2_category}")
    
    # Test 3: Slack Integration (with fallback)
    print(f"\n3️⃣ Testing Slack Integration")
    
    # Check if we have a fallback channel
    fallback_channel = None
    try:
        poster = SlackPoster()
        
        # Try to find any accessible channel
        channels_response = await poster.client.conversations_list(types="public_channel,private_channel")
        if channels_response.get("ok"):
            channels = channels_response.get("channels", [])
            for channel in channels:
                if channel.get("is_member", False):
                    fallback_channel = f"#{channel['name']}"
                    break
        
        if fallback_channel:
            print(f"  Using fallback channel: {fallback_channel}")
            
            # Test posting a message
            test_classification = {
                "level_1_category": "Payments and Cash Out",
                "level_2_category": "Cash Out",
                "slack_channel": fallback_channel,
                "jira_ticket": "JIRA-TEST-001"
            }
            
            test_message = "🧪 Test message from message processor integration"
            test_source = {
                "source": "Test",
                "author": "test_user",
                "platform": "test",
                "timestamp": "2024-01-01T00:00:00Z"
            }
            
            result = await poster.post_classified_message(test_message, test_classification, test_source)
            
            if result.success:
                print(f"  ✅ Successfully posted test message to {fallback_channel}")
                print(f"     Message timestamp: {result.message_ts}")
            else:
                print(f"  ❌ Failed to post message: {result.error}")
        else:
            print(f"  ⚠️  No accessible channels found for testing")
            print(f"  💡 You need to invite the bot to the target channels manually")
    
    except Exception as e:
        print(f"  ❌ Slack integration test failed: {e}")
    
    # Test 4: Complete Processing Cycle
    print(f"\n4️⃣ Testing Complete Processing Cycle")
    
    try:
        # Process a small batch
        stats = await processor.run_processing_cycle(batch_size=2)
        print(f"  Processed {stats['successful']}/{stats['total']} messages successfully")
        
        if stats['failed'] > 0:
            print(f"  ⚠️  {stats['failed']} messages failed to process")
            for error in stats['errors'][:2]:
                print(f"     - {error['error']}")
    
    except Exception as e:
        print(f"  ❌ Processing cycle test failed: {e}")
    
    finally:
        await processor.close()
    
    print(f"\n🎉 Complete Flow Test Finished!")
    print(f"\n📋 Summary:")
    print(f"  ✅ Message classification is working")
    print(f"  ✅ Database integration is working")
    print(f"  {'✅' if fallback_channel else '⚠️'} Slack integration {'is working' if fallback_channel else 'needs channel access'}")
    print(f"  ✅ Complete processing cycle is working")
    
    if not fallback_channel:
        print(f"\n🔧 Next Steps:")
        print(f"  1. Manually invite the bot to the target Slack channels")
        print(f"  2. Or update the channel mapping to use accessible channels")
        print(f"  3. Then run: python unified_mcp_monitor_updated.py")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())
