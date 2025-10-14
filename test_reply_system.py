#!/usr/bin/env python3
"""
Test the Slack Reply System

This script tests the reply system functionality without actually posting to Slack.
It simulates message processing and sentiment analysis.
"""

import asyncio
import sys
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from slack_reply_system import SentimentAnalyzer, JiraTicketGenerator, Sentiment


def test_sentiment_analysis():
    """Test the sentiment analysis functionality"""
    print("🧪 Testing Sentiment Analysis")
    print("=" * 50)
    
    analyzer = SentimentAnalyzer()
    
    test_messages = [
        "I love this app! It's amazing and so helpful!",
        "This app is terrible. It keeps crashing and I can't cash out my money.",
        "The app is okay, but I have a question about how to use the tip jar feature.",
        "Thank you for the great service! You guys are awesome!",
        "I'm having issues with the cash out feature. It's not working properly.",
        "The app works fine, no complaints here.",
        "This is the worst app ever. I hate it and want my money back!",
        "Can you help me with setting up my bank account?",
        "Perfect! Everything works exactly as expected.",
        "There's a bug in the notification system that needs to be fixed."
    ]
    
    for i, message in enumerate(test_messages, 1):
        sentiment, confidence, reasoning = analyzer.analyze_sentiment(message)
        
        print(f"\nTest {i}: {message}")
        print(f"   Sentiment: {sentiment.value}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Reasoning: {reasoning}")
        
        # Determine expected reply
        if sentiment == Sentiment.POSITIVE or sentiment == Sentiment.NEUTRAL:
            expected_reply = "Thank you for your kind words! I'm glad you found our app helpful and appreciate your feedback!"
        else:
            expected_reply = "Thank you for your feedback! We're a customer-centric organization and truly appreciate you sharing your concern. We've logged it as system JIRA-XXXXXX, and our team is actively working on it. You can track your ticket's progress here: https://jira.example.com/browse/JIRA-XXXXXX."
        
        print(f"   Expected Reply: {expected_reply[:100]}...")


def test_jira_ticket_generation():
    """Test the JIRA ticket generation functionality"""
    print("\n\n🎫 Testing JIRA Ticket Generation")
    print("=" * 50)
    
    generator = JiraTicketGenerator()
    
    # Test generating tickets for different message IDs
    test_message_ids = [
        "msg_001",
        "msg_002", 
        "msg_003",
        "msg_001",  # Same as first one - should get same ticket
        "msg_004"
    ]
    
    for msg_id in test_message_ids:
        ticket = generator.get_ticket_for_message(msg_id)
        print(f"Message ID: {msg_id} -> JIRA Ticket: {ticket}")
    
    # Test generating multiple tickets
    print(f"\nGenerating 5 new tickets:")
    for i in range(5):
        ticket = generator.generate_ticket()
        print(f"   Ticket {i+1}: {ticket}")


def test_reply_templates():
    """Test the reply templates"""
    print("\n\n📝 Testing Reply Templates")
    print("=" * 50)
    
    positive_reply = "Thank you for your kind words! I'm glad you found our app helpful and appreciate your feedback!"
    negative_reply_template = "Thank you for your feedback! We're a customer-centric organization and truly appreciate you sharing your concern. We've logged it as system {jira_ticket}, and our team is actively working on it. You can track your ticket's progress here: https://jira.example.com/browse/{jira_ticket}."
    
    print("Positive/Neutral Reply Template:")
    print(f"   {positive_reply}")
    
    print("\nNegative Reply Template (with JIRA ticket):")
    test_ticket = "JIRA-613401"
    negative_reply = negative_reply_template.format(jira_ticket=test_ticket)
    print(f"   {negative_reply}")
    
    print(f"\nJIRA Ticket used: {test_ticket}")
    print(f"JIRA URL: https://jira.example.com/browse/{test_ticket}")


async def test_slack_connection():
    """Test Slack connection (without posting)"""
    print("\n\n🔗 Testing Slack Connection")
    print("=" * 50)
    
    try:
        from slack_reply_system import SlackReplySystem
        
        reply_system = SlackReplySystem()
        
        # Test channel access validation
        print("Testing channel access validation...")
        if await reply_system.validate_channel_access():
            print("✅ Successfully connected to all-feedforward channel")
        else:
            print("❌ Failed to connect to all-feedforward channel")
        
        # Test fetching recent messages (without processing)
        print("\nTesting message fetching...")
        messages = await reply_system.fetch_recent_messages(limit=5)
        print(f"✅ Fetched {len(messages)} recent messages")
        
        if messages:
            print("Sample message structure:")
            sample_msg = messages[0]
            print(f"   Timestamp: {sample_msg.get('ts', 'N/A')}")
            print(f"   User: {sample_msg.get('user', 'N/A')}")
            print(f"   Text: {sample_msg.get('text', 'N/A')[:100]}...")
        
        await reply_system.close()
        
    except Exception as e:
        print(f"❌ Slack connection test failed: {e}")


def main():
    """Run all tests"""
    print("🚀 Testing Slack Reply System")
    print("=" * 60)
    
    # Test sentiment analysis
    test_sentiment_analysis()
    
    # Test JIRA ticket generation
    test_jira_ticket_generation()
    
    # Test reply templates
    test_reply_templates()
    
    # Test Slack connection
    print("\n\nTesting Slack connection...")
    asyncio.run(test_slack_connection())
    
    print("\n\n✅ All tests completed!")
    print("\nTo run the actual reply system:")
    print("   python run_reply_system.py --test")
    print("   python run_reply_system.py --mode once --limit 10")
    print("   python run_enhanced_processor.py --test")
    print("   python run_enhanced_processor.py --mode once --limit 10")


if __name__ == "__main__":
    main()
