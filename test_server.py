#!/usr/bin/env python3
"""
Test script for Feedback Management MCP Server
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.insert(0, '.')

from feedback_mcp_server import (
    FeedbackDatabase, FeedbackNormalizer, FeedbackClassifier, 
    BusinessImpactScorer, Feedback, FeedbackSource, FeedbackCategory, 
    Sentiment, Severity
)

async def test_database():
    """Test database operations"""
    print("Testing database operations...")
    
    db = FeedbackDatabase("test_feedback.db")
    
    # Create test feedback
    feedback = Feedback(
        id="test_1",
        source=FeedbackSource.APP_STORE,
        content="This app is great! Love the new features.",
        author="test_user",
        timestamp=datetime.now(timezone.utc),
        rating=5
    )
    
    # Save feedback
    success = db.save_feedback(feedback)
    print(f"✅ Save feedback: {success}")
    
    # Retrieve feedback
    retrieved = db.get_feedback("test_1")
    print(f"✅ Retrieve feedback: {retrieved is not None}")
    
    # Get unprocessed feedback
    unprocessed = db.get_unprocessed_feedback()
    print(f"✅ Unprocessed feedback count: {len(unprocessed)}")
    
    return True

def test_normalizer():
    """Test feedback normalizer"""
    print("Testing feedback normalizer...")
    
    normalizer = FeedbackNormalizer()
    
    # Test feedback with PII
    feedback = Feedback(
        id="test_2",
        source=FeedbackSource.EMAIL,
        content="Hi, my email is john.doe@example.com and my phone is 555-123-4567. The app crashed yesterday.",
        author="john_doe",
        timestamp=datetime.now(timezone.utc)
    )
    
    # Normalize feedback
    normalized = normalizer.normalize_feedback(feedback)
    
    print(f"✅ PII detected: {normalized.pii_detected}")
    print(f"✅ Language detected: {normalized.language}")
    print(f"✅ Content cleaned: {'[EMAIL]' in normalized.content and '[PHONE]' in normalized.content}")
    
    return True

def test_classifier():
    """Test feedback classifier"""
    print("Testing feedback classifier...")
    
    classifier = FeedbackClassifier()
    
    # Test different types of feedback
    test_cases = [
        ("The app keeps crashing when I try to login", FeedbackCategory.BUG, Sentiment.NEGATIVE),
        ("I love this app! It's amazing!", FeedbackCategory.PRAISE, Sentiment.POSITIVE),
        ("Can you add dark mode?", FeedbackCategory.FEATURE_REQUEST, Sentiment.NEUTRAL),
        ("This is terrible, worst app ever", FeedbackCategory.COMPLAINT, Sentiment.NEGATIVE),
    ]
    
    for content, expected_category, expected_sentiment in test_cases:
        feedback = Feedback(
            id=f"test_{hash(content)}",
            source=FeedbackSource.APP_STORE,
            content=content,
            author="test_user",
            timestamp=datetime.now(timezone.utc)
        )
        
        classified = classifier.classify_feedback(feedback)
        
        category_match = classified.category == expected_category
        sentiment_match = classified.sentiment == expected_sentiment
        
        print(f"✅ '{content[:30]}...' - Category: {category_match}, Sentiment: {sentiment_match}")
    
    return True

def test_scorer():
    """Test business impact scorer"""
    print("Testing business impact scorer...")
    
    scorer = BusinessImpactScorer()
    
    # Test high impact feedback
    high_impact = Feedback(
        id="test_high",
        source=FeedbackSource.APP_STORE,
        content="App crashes on startup, completely unusable",
        author="user1",
        timestamp=datetime.now(timezone.utc),
        rating=1
    )
    
    # Test low impact feedback
    low_impact = Feedback(
        id="test_low",
        source=FeedbackSource.APP_STORE,
        content="Great app, love it!",
        author="user2",
        timestamp=datetime.now(timezone.utc),
        rating=5
    )
    
    # Score feedback
    high_scored = scorer.score_feedback(high_impact)
    low_scored = scorer.score_feedback(low_impact)
    
    print(f"✅ High impact score: {high_scored.business_impact_score:.2f}")
    print(f"✅ Low impact score: {low_scored.business_impact_score:.2f}")
    print(f"✅ Scoring logic: {high_scored.business_impact_score > low_scored.business_impact_score}")
    
    return True

async def test_tools():
    """Test MCP tools"""
    print("Testing MCP tools...")
    
    from feedback_mcp_server import (
        fetch_appstore_reviews, fetch_playstore_reviews, fetch_slack_reviews,
        reddit_search_stream, twitter_search_stream,
        classify_feedback, score_business_impact, get_metrics, check_new_reviews
    )
    
    # Test App Store reviews from Slack
    result = fetch_appstore_reviews({"channel_name": "app-review", "limit": 5})
    print(f"✅ App Store fetch from Slack: {result.content[0].text}")
    
    # Test Play Store reviews from Slack
    result = fetch_playstore_reviews({"channel_name": "app-review", "limit": 5})
    print(f"✅ Play Store fetch from Slack: {result.content[0].text}")
    
    # Test combined Slack reviews
    result = fetch_slack_reviews({"channel_name": "app-review", "limit": 10})
    print(f"✅ Combined Slack reviews: {result.content[0].text}")
    
    # Test Reddit search
    result = reddit_search_stream({"query": "test app", "limit": 5})
    print(f"✅ Reddit search: {result.content[0].text}")
    
    # Test Twitter search
    result = twitter_search_stream({"query": "test app", "limit": 5})
    print(f"✅ Twitter search: {result.content[0].text}")
    
    # Test classification (need to have feedback in DB first)
    db = FeedbackDatabase("test_feedback.db")
    unprocessed = db.get_unprocessed_feedback()
    if unprocessed:
        result = classify_feedback({"feedback_id": unprocessed[0].id})
        print(f"✅ Classification: {result.content[0].text}")
    
    # Test metrics
    result = get_metrics({"timeframe": "week"})
    print(f"✅ Metrics: {result.content[0].text}")
    
    # Test new review checking
    result = check_new_reviews({"channel_name": "app-review", "auto_process": False})
    print(f"✅ New review check: {result.content[0].text}")
    
    return True

async def main():
    """Run all tests"""
    print("🧪 Testing Feedback Management MCP Server")
    print("=" * 50)
    
    tests = [
        ("Database Operations", test_database()),
        ("Feedback Normalizer", test_normalizer()),
        ("Feedback Classifier", test_classifier()),
        ("Business Impact Scorer", test_scorer()),
        ("MCP Tools", test_tools()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Server is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
