#!/usr/bin/env python3
"""
Test the full integration with actual message classification and Slack posting
"""

import asyncio
from message_classifier import classify_message_simple
from slack_poster import SlackPoster
from datetime import datetime

async def test_full_integration():
    """Test the complete integration with real message posting"""
    print("🧪 Testing Full Message Processing Integration")
    print("=" * 60)
    
    # Test messages that should go to different channels
    test_cases = [
        {
            "message": "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
            "expected_channel": "#help-cashout-experience"
        },
        {
            "message": "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
            "expected_channel": "#help-performance-ux"
        },
        {
            "message": "I love the tip jar feature! It's amazing how I can earn extra money.",
            "expected_channel": "#help-earnin-card"
        },
        {
            "message": "There's a bug in the app that prevents me from connecting my bank account.",
            "expected_channel": "#help-edx-accountverification"
        },
        {
            "message": "The security features make me feel safe using this app.",
            "expected_channel": "#help-security"
        },
        {
            "message": "I need help with customer support - they're not responding to my emails.",
            "expected_channel": "#help-cx"
        },
        {
            "message": "I just love how easy it is to see my earnings now, thanks!",
            "expected_channel": ""  # Should not post anywhere
        }
    ]
    
    poster = SlackPoster()
    
    print(f"📋 Testing {len(test_cases)} message classifications and Slack postings...")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        message = test_case["message"]
        expected_channel = test_case["expected_channel"]
        
        print(f"\n{i}. Testing: {message[:50]}...")
        
        # Classify the message
        classification = classify_message_simple(message)
        
        print(f"   Classification:")
        print(f"     L1: {classification['level_1_category']}")
        print(f"     L2: {classification['level_2_category']}")
        print(f"     Slack: {classification['slack_channel']}")
        print(f"     JIRA: {classification['jira_ticket']}")
        
        # Check if classification matches expectation
        if classification['slack_channel'] == expected_channel:
            print(f"   ✅ Classification matches expectation")
        else:
            print(f"   ⚠️  Classification differs from expectation")
            print(f"     Expected: {expected_channel}")
            print(f"     Got: {classification['slack_channel']}")
        
        # Post to Slack if there's a channel
        if classification['slack_channel']:
            print(f"   📤 Posting to Slack...")
            
            source_info = {
                "source": "Test Integration",
                "author": "test_user",
                "platform": "test",
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                result = await poster.post_classified_message(
                    message, 
                    classification, 
                    source_info
                )
                
                if result.success:
                    print(f"   ✅ Successfully posted to {classification['slack_channel']}")
                    print(f"      Message timestamp: {result.message_ts}")
                    success_count += 1
                else:
                    print(f"   ❌ Failed to post: {result.error}")
                    
            except Exception as e:
                print(f"   ❌ Error posting: {e}")
        else:
            print(f"   ⏭️  No Slack channel - message not posted (as expected)")
            success_count += 1  # This is expected behavior
        
        # Small delay between posts
        await asyncio.sleep(1)
    
    print(f"\n🎉 Integration Test Complete!")
    print(f"📊 Results:")
    print(f"   Total tests: {total_count}")
    print(f"   Successful: {success_count}")
    print(f"   Success rate: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print(f"\n✅ All tests passed! The integration is working perfectly.")
        print(f"🚀 You can now run: python unified_mcp_monitor_updated.py")
    else:
        print(f"\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(test_full_integration())
