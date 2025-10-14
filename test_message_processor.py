"""
Test Script for Message Processor Integration

This script tests the complete message processing pipeline including
classification and Slack posting functionality.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import List, Dict

# Import our modules
from message_classifier import MessageClassifier, classify_message_simple
from slack_poster import SlackPoster, post_single_message
from message_processor import MessageProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_message_classifier():
    """Test the message classifier with sample messages"""
    print("\n=== Testing Message Classifier ===")
    
    test_messages = [
        "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
        "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
        "I just love how easy it is to see my earnings now, thanks!",
        "There's a bug in the app that prevents me from connecting my bank account.",
        "The security features make me feel safe using this app.",
        "I need help with setting up my account verification.",
        "The tip jar feature is amazing! I love earning extra money.",
        "Why is the app so slow when I try to check my balance?",
        "Great customer support team, they helped me resolve my issue quickly.",
        "I'm concerned about the privacy of my financial data."
    ]
    
    classifier = MessageClassifier()
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message[:50]}...")
        result = classifier.classify_message(message)
        
        print(f"  L1: {result.level_1_category}")
        print(f"  L2: {result.level_2_category}")
        print(f"  Slack: {result.slack_channel}")
        print(f"  JIRA: {result.jira_ticket}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Reasoning: {result.reasoning}")
    
    # Test batch classification
    print(f"\n=== Testing Batch Classification ===")
    batch_results = classifier.classify_batch(test_messages[:5])
    summary = classifier.get_classification_summary(batch_results)
    
    print(f"Total messages: {summary['total_messages']}")
    print(f"Average confidence: {summary['average_confidence']:.2f}")
    print(f"Low confidence count: {summary['low_confidence_count']}")
    print(f"Category distribution: {summary['category_distribution']}")
    print(f"Slack channel distribution: {summary['slack_channel_distribution']}")


async def test_slack_poster():
    """Test the Slack poster functionality"""
    print("\n=== Testing Slack Poster ===")
    
    try:
        poster = SlackPoster()
        
        # Test channel validation
        test_channels = [
            "#help-cashout-experience",
            "#help-earnin-card", 
            "#help-performance-ux",
            "#help-cx",
            "#invalid-channel"
        ]
        
        print("Testing channel validation:")
        for channel in test_channels:
            is_valid = await poster.validate_channel(channel)
            print(f"  {channel}: {'✓' if is_valid else '✗'}")
        
        # Test message posting (only if we have valid channels)
        valid_channels = [ch for ch in test_channels if await poster.validate_channel(ch)]
        
        if valid_channels:
            test_classification = {
                "level_1_category": "Payments and Cash Out",
                "level_2_category": "Cash Out",
                "slack_channel": valid_channels[0],
                "jira_ticket": "JIRA-TEST-001"
            }
            
            test_message = "Test message: My instant cash out took much longer than usual."
            test_source = {
                "source": "Test",
                "author": "test_user",
                "platform": "test",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\nTesting message posting to {valid_channels[0]}:")
            result = await poster.post_classified_message(test_message, test_classification, test_source)
            
            if result.success:
                print(f"  ✓ Message posted successfully: {result.message_ts}")
            else:
                print(f"  ✗ Failed to post message: {result.error}")
        else:
            print("  No valid channels found for testing")
        
        await poster.close()
        
    except Exception as e:
        print(f"  ✗ Slack poster test failed: {e}")


async def test_message_processor():
    """Test the complete message processor"""
    print("\n=== Testing Message Processor ===")
    
    try:
        processor = MessageProcessor("unified_messages.db")
        
        # Test getting processing stats
        stats = processor.get_processing_stats()
        print(f"Database stats:")
        print(f"  Total messages: {stats.get('total_messages', 0)}")
        print(f"  Processed: {stats.get('processed_messages', 0)}")
        print(f"  Unprocessed: {stats.get('unprocessed_messages', 0)}")
        print(f"  Processing rate: {stats.get('processing_rate', 0):.1f}%")
        
        # Test fetching unprocessed messages
        messages = processor.get_unprocessed_messages(limit=5)
        print(f"\nUnprocessed messages found: {len(messages)}")
        
        if messages:
            print("Sample unprocessed messages:")
            for i, msg in enumerate(messages[:3], 1):
                print(f"  {i}. [{msg.source}] {msg.content[:50]}...")
                
                # Test classification
                classification = processor.classify_message(msg)
                print(f"     -> {classification.level_1_category} -> {classification.level_2_category}")
        
        # Test processing a small batch (dry run)
        if messages:
            print(f"\nTesting processing of {min(2, len(messages))} messages...")
            test_messages = messages[:2]
            
            for msg in test_messages:
                success, error = await processor.process_single_message(msg)
                if success:
                    print(f"  ✓ Processed message {msg.id}")
                else:
                    print(f"  ✗ Failed to process message {msg.id}: {error}")
        
        await processor.close()
        
    except Exception as e:
        print(f"  ✗ Message processor test failed: {e}")


def test_classification_examples():
    """Test classification with the exact examples from the prompt"""
    print("\n=== Testing Classification Examples ===")
    
    examples = [
        {
            "message": "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
            "expected_l1": "Payments and Cash Out",
            "expected_l2": "Cash Out",
            "expected_slack": "#help-cashout-experience"
        },
        {
            "message": "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
            "expected_l1": "Product Feedback (Feature/Functionality)",
            "expected_l2": "App UX / Performance",
            "expected_slack": "#help-performance-ux"
        },
        {
            "message": "I just love how easy it is to see my earnings now, thanks!",
            "expected_l1": "General Sentiment",
            "expected_l2": "Non-relevant or Ambiguous",
            "expected_slack": ""
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}: {example['message'][:50]}...")
        
        result = classify_message_simple(example['message'])
        
        print(f"  Expected L1: {example['expected_l1']}")
        print(f"  Actual L1:   {result['level_1_category']}")
        print(f"  L1 Match:    {'✓' if result['level_1_category'] == example['expected_l1'] else '✗'}")
        
        print(f"  Expected L2: {example['expected_l2']}")
        print(f"  Actual L2:   {result['level_2_category']}")
        print(f"  L2 Match:    {'✓' if result['level_2_category'] == example['expected_l2'] else '✗'}")
        
        print(f"  Expected Slack: {example['expected_slack']}")
        print(f"  Actual Slack:   {result['slack_channel']}")
        print(f"  Slack Match:    {'✓' if result['slack_channel'] == example['expected_slack'] else '✗'}")
        
        print(f"  JIRA Ticket: {result['jira_ticket']}")


async def main():
    """Run all tests"""
    print("Starting Message Processor Integration Tests")
    print("=" * 50)
    
    # Test 1: Message Classifier
    test_message_classifier()
    
    # Test 2: Classification Examples
    test_classification_examples()
    
    # Test 3: Slack Poster
    await test_slack_poster()
    
    # Test 4: Message Processor
    await test_message_processor()
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

