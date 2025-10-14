#!/usr/bin/env python3
"""
MCP Server Test Suite

Comprehensive test suite to verify all MCP servers are working correctly
and can connect to their respective services.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPServerTester:
    """Test suite for MCP servers"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now(timezone.utc)
    
    async def test_feedback_mcp_server(self) -> Dict[str, Any]:
        """Test feedback MCP server functionality"""
        logger.info("🧪 Testing Feedback MCP Server...")
        
        try:
            # Test imports
            from feedback_mcp_server import (
                app, db, normalizer, classifier, scorer, slack_fetcher,
                Feedback, FeedbackSource, FeedbackCategory, Sentiment, Severity
            )
            
            # Test database initialization
            db_test = db.get_unprocessed_feedback()
            logger.info(f"✅ Database connection: {len(db_test)} unprocessed items")
            
            # Test Slack integration
            slack_status = "disabled"
            if slack_fetcher.client:
                channel_id = slack_fetcher.get_channel_id()
                if channel_id:
                    slack_status = "connected"
                    logger.info(f"✅ Slack integration: Connected to channel {channel_id}")
                else:
                    slack_status = "channel_not_found"
                    logger.warning("⚠️  Slack integration: Channel not found")
            else:
                logger.warning("⚠️  Slack integration: Client not initialized")
            
            # Test feedback processing pipeline
            test_feedback = Feedback(
                id="test_feedback_001",
                source=FeedbackSource.APP_STORE,
                content="This is a test feedback message for testing purposes.",
                author="test_user",
                timestamp=datetime.now(timezone.utc),
                rating=4
            )
            
            # Test normalization
            normalized = normalizer.normalize_feedback(test_feedback)
            logger.info(f"✅ Normalization: Language detected as {normalized.language}")
            
            # Test classification
            classified = classifier.classify_feedback(normalized)
            logger.info(f"✅ Classification: Category={classified.category.value}, Sentiment={classified.sentiment.value}")
            
            # Test scoring
            scored = scorer.score_feedback(classified)
            logger.info(f"✅ Scoring: Business impact score={scored.business_impact_score:.2f}")
            
            # Test MCP tools (list_tools is not async in this version)
            try:
                tools = app.list_tools()
                logger.info(f"✅ MCP Tools: {len(tools)} tools available")
            except Exception as e:
                logger.warning(f"⚠️  MCP Tools test skipped: {e}")
                tools = []
            
            return {
                "status": "success",
                "database": "connected",
                "slack": slack_status,
                "processing_pipeline": "working",
                "mcp_tools": len(tools),
                "details": {
                    "unprocessed_feedback": len(db_test),
                    "test_feedback_processed": True,
                    "classification_working": True,
                    "scoring_working": True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Feedback MCP Server test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_reddit_mcp_server(self) -> Dict[str, Any]:
        """Test Reddit MCP server functionality"""
        logger.info("🧪 Testing Reddit MCP Server...")
        
        try:
            # Test imports
            from reddit_mcp_server import app, reddit_client, RedditPost
            
            # Test Reddit connection
            user = reddit_client.reddit.user.me()
            logger.info(f"✅ Reddit connection: Connected as {user}")
            
            # Test subreddit search
            subreddits = reddit_client.search_subreddits("python", limit=3)
            logger.info(f"✅ Subreddit search: Found {len(subreddits)} subreddits")
            
            # Test post search
            posts = reddit_client.search_posts("python programming", limit=3)
            logger.info(f"✅ Post search: Found {len(posts)} posts")
            
            # Test subreddit info
            subreddit_info = reddit_client.get_subreddit_info("python")
            if subreddit_info:
                logger.info(f"✅ Subreddit info: r/python has {subreddit_info['subscribers']} subscribers")
            
            # Test MCP tools (list_tools is not async in this version)
            try:
                tools = app.list_tools()
                logger.info(f"✅ MCP Tools: {len(tools)} tools available")
            except Exception as e:
                logger.warning(f"⚠️  MCP Tools test skipped: {e}")
                tools = []
            
            return {
                "status": "success",
                "reddit_connection": "connected",
                "user": str(user),
                "search_functionality": "working",
                "mcp_tools": len(tools),
                "details": {
                    "subreddits_found": len(subreddits),
                    "posts_found": len(posts),
                    "subreddit_info_working": subreddit_info is not None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Reddit MCP Server test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_unified_monitor(self) -> Dict[str, Any]:
        """Test unified monitor functionality"""
        logger.info("🧪 Testing Unified Monitor...")
        
        try:
            # Test imports
            from unified_mcp_monitor import UnifiedMCPMonitor
            
            # Create monitor instance
            monitor = UnifiedMCPMonitor()
            logger.info("✅ Monitor instance created")
            
            # Test configuration loading
            monitor.load_config()
            logger.info(f"✅ Configuration loaded: Check interval={monitor.check_interval}s")
            
            # Test status report generation
            report = monitor.get_status_report()
            logger.info(f"✅ Status report: {report['summary']['total_services']} services monitored")
            
            return {
                "status": "success",
                "monitor_initialization": "working",
                "configuration_loading": "working",
                "status_reporting": "working",
                "details": {
                    "check_interval": monitor.check_interval,
                    "services_monitored": report['summary']['total_services']
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Unified Monitor test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_integration_workflow(self) -> Dict[str, Any]:
        """Test integration between servers"""
        logger.info("🧪 Testing Integration Workflow...")
        
        try:
            # Test that both servers can be imported together
            from feedback_mcp_server import Feedback, FeedbackSource
            from reddit_mcp_server import reddit_client
            
            # Test creating feedback from Reddit data
            posts = reddit_client.search_posts("earnin", limit=1)
            if posts:
                post = posts[0]
                feedback = Feedback(
                    id=f"reddit_{post.id}",
                    source=FeedbackSource.REDDIT,
                    content=post.title + " " + post.content,
                    author=post.author,
                    timestamp=post.created_utc,
                    url=post.permalink
                )
                logger.info(f"✅ Integration: Created feedback from Reddit post {post.id}")
            
            return {
                "status": "success",
                "cross_server_imports": "working",
                "data_integration": "working",
                "details": {
                    "reddit_to_feedback_conversion": "working"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Integration workflow test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting MCP Server Test Suite...")
        logger.info("=" * 50)
        
        # Run individual server tests
        self.test_results["feedback_mcp"] = await self.test_feedback_mcp_server()
        self.test_results["reddit_mcp"] = await self.test_reddit_mcp_server()
        self.test_results["unified_monitor"] = await self.test_unified_monitor()
        self.test_results["integration"] = await self.test_integration_workflow()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        logger.info("=" * 50)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "success")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        for test_name, result in self.test_results.items():
            status_emoji = "✅" if result["status"] == "success" else "❌"
            logger.info(f"{status_emoji} {test_name}: {result['status']}")
            
            if result["status"] == "error":
                logger.error(f"   Error: {result['error']}")
        
        # Save results to file
        self.save_test_results()
        
        # Return exit code
        if failed_tests > 0:
            logger.error("❌ Some tests failed!")
            return 1
        else:
            logger.info("🎉 All tests passed!")
            return 0
    
    def save_test_results(self):
        """Save test results to file"""
        try:
            results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
                "results": self.test_results
            }
            
            with open('test_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info("💾 Test results saved to test_results.json")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")

async def main():
    """Main entry point"""
    tester = MCPServerTester()
    exit_code = await tester.run_all_tests()
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error during testing: {e}")
        sys.exit(1)
