#!/usr/bin/env python3
"""
Unified MCP Server Monitor - Updated Version

A comprehensive monitoring system that coordinates all MCP servers and ensures
they check for new posts/messages every minute using the unified database.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Apply SSL bypass for corporate networks
try:
    from ssl_bypass_fix import apply_ssl_bypass
    apply_ssl_bypass()
except ImportError:
    pass

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_monitor_updated.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MonitorStatus:
    """Status of a monitored service"""
    name: str
    last_check: datetime
    status: str  # "running", "error", "stopped"
    last_error: Optional[str] = None
    processed_count: int = 0
    error_count: int = 0

class UnifiedMCPMonitorUpdated:
    """Unified monitor for all MCP servers using unified database"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # 1 minute
        self.services: Dict[str, MonitorStatus] = {}
        self.start_time = datetime.now(timezone.utc)
        self.unified_db_path = "unified_messages.db"
        
        # Initialize service statuses
        self.services = {
            "feedback-management-unified": MonitorStatus(
                name="feedback-management-unified",
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "reddit-mcp-unified": MonitorStatus(
                name="reddit-mcp-unified", 
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "slack-integration-unified": MonitorStatus(
                name="slack-integration-unified",
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "message-processor": MonitorStatus(
                name="message-processor",
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "slack-reply-system": MonitorStatus(
                name="slack-reply-system",
                last_check=datetime.now(timezone.utc),
                status="stopped"
            )
        }
        
        # Load configuration
        self.load_config()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self):
        """Load configuration from environment and config files"""
        self.check_interval = int(os.getenv('MONITOR_CHECK_INTERVAL', '60'))
        self.auto_process = os.getenv('AUTO_PROCESS_REVIEWS', 'true').lower() == 'true'
        
        # Load MCP server config if available
        config_path = 'mcp_server_config.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.mcp_config = json.load(f)
                logger.info(f"Loaded MCP configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading MCP config: {e}")
                self.mcp_config = {}
        else:
            self.mcp_config = {}
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def get_unified_database_stats(self) -> Dict[str, Any]:
        """Get statistics from the unified database"""
        if not os.path.exists(self.unified_db_path):
            return {"error": "Unified database not found"}
        
        try:
            import sqlite3
            with sqlite3.connect(self.unified_db_path) as conn:
                cursor = conn.cursor()
                
                # Total messages
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                # Messages by source
                cursor.execute("SELECT source, COUNT(*) FROM messages GROUP BY source")
                by_source = dict(cursor.fetchall())
                
                # Recent messages (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE datetime(timestamp) > datetime('now', '-1 day')
                """)
                recent_messages = cursor.fetchone()[0]
                
                # Processed vs unprocessed
                cursor.execute("SELECT processed, COUNT(*) FROM messages GROUP BY processed")
                by_processed = dict(cursor.fetchall())
                
                return {
                    'total_messages': total_messages,
                    'by_source': by_source,
                    'recent_messages_24h': recent_messages,
                    'by_processed': by_processed,
                    'database_path': self.unified_db_path
                }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}
    
    async def check_feedback_management_unified(self) -> bool:
        """Check feedback management server status (unified version)"""
        try:
            # Import and use the unified feedback server components
            from feedback_mcp_server_unified import slack_fetcher, db, normalizer, classifier, scorer
            
            # Just check if components are available and working
            if slack_fetcher.client and slack_fetcher.auto_process_enabled:
                logger.debug("Feedback management (unified): Components healthy")
                return True
            else:
                logger.warning("Feedback management (unified): Components not fully initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error in feedback management (unified) check: {e}")
            self.services["feedback-management-unified"].error_count += 1
            self.services["feedback-management-unified"].last_error = str(e)
            return False
    
    async def check_reddit_mcp_unified(self) -> bool:
        """Check and process Reddit MCP server using the unified database"""
        try:
            # Use the unified Reddit monitor
            from reddit_monitor_unified import RedditEarnInMonitorUnified
            
            logger.info("Reddit MCP (unified): Using unified Reddit monitor to search for 'earnin'...")
            
            # Create monitor instance
            reddit_monitor = RedditEarnInMonitorUnified()
            
            # Fetch new posts (this includes both subreddit-specific and global search)
            total_posts = reddit_monitor.fetch_new_posts()
            
            if total_posts > 0:
                self.services["reddit-mcp-unified"].processed_count += total_posts
                logger.info(f"Reddit MCP (unified): Found {total_posts} new Earnin-related posts")
            else:
                logger.info("Reddit MCP (unified): No new Earnin-related posts found")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in Reddit MCP (unified) check: {e}")
            self.services["reddit-mcp-unified"].error_count += 1
            self.services["reddit-mcp-unified"].last_error = str(e)
            return False
    
    async def check_slack_integration_unified(self) -> bool:
        """Check Slack integration and process new messages (unified version)"""
        try:
            from feedback_mcp_server_unified import slack_fetcher
            
            # Test Slack connection and process new messages
            if slack_fetcher.client:
                # Try to get channel info
                channel_id = slack_fetcher.get_channel_id()
                if channel_id:
                    # Check for new messages and process them
                    if slack_fetcher.auto_process_enabled:
                        processed_count = slack_fetcher.auto_process_new_reviews()
                        if processed_count > 0:
                            logger.info(f"Slack integration (unified): ✅ Processed {processed_count} new messages")
                            self.services["slack-integration-unified"].processed_count += processed_count
                        else:
                            logger.info("Slack integration (unified): ℹ️ No new messages found (deduplication working)")
                    else:
                        logger.debug("Slack integration (unified): Auto-processing disabled")
                    return True
                else:
                    logger.warning("Slack integration (unified): Channel not found")
                    return False
            else:
                logger.warning("Slack integration (unified): Client not initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error in Slack integration (unified) check: {e}")
            self.services["slack-integration-unified"].error_count += 1
            self.services["slack-integration-unified"].last_error = str(e)
            return False
    
    async def check_message_processor(self) -> bool:
        """Check and run the message processor for classification and Slack posting"""
        try:
            from message_processor import MessageProcessor
            
            logger.info("Message Processor: Processing unprocessed messages...")
            
            # Create processor instance
            processor = MessageProcessor(self.unified_db_path)
            
            # Process all unprocessed messages
            stats = await processor.run_processing_cycle()
            
            if stats['total'] > 0:
                self.services["message-processor"].processed_count += stats['successful']
                self.services["message-processor"].error_count += stats['failed']
                logger.info(f"Message Processor: Processed {stats['successful']}/{stats['total']} messages successfully")
                
                if stats['failed'] > 0:
                    logger.warning(f"Message Processor: {stats['failed']} messages failed to process")
            else:
                logger.info("Message Processor: No unprocessed messages found")
            
            # Close processor
            await processor.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in message processor check: {e}")
            self.services["message-processor"].error_count += 1
            self.services["message-processor"].last_error = str(e)
            return False
    
    async def check_slack_reply_system(self) -> bool:
        """Check and run the Slack reply system for all-feedforward channel"""
        try:
            from slack_reply_system import SlackReplySystem
            
            logger.info("Slack Reply System: Checking for new messages in all-feedforward channel...")
            
            # Create reply system instance
            reply_system = SlackReplySystem()
            
            # Process recent messages (limit to 20 to avoid overwhelming)
            results = await reply_system.process_recent_messages(limit=20)
            
            if results:
                replies_posted = len([r for r in results if r.success])
                jira_tickets = len([r for r in results if r.jira_ticket])
                
                self.services["slack-reply-system"].processed_count += replies_posted
                
                if replies_posted > 0:
                    logger.info(f"Slack Reply System: ✅ Posted {replies_posted} replies to all-feedforward channel")
                    if jira_tickets > 0:
                        logger.info(f"Slack Reply System: 🎫 Generated {jira_tickets} JIRA tickets for negative feedback")
                else:
                    logger.info("Slack Reply System: ℹ️ No new messages requiring replies found")
            else:
                logger.info("Slack Reply System: ℹ️ No new messages found in all-feedforward channel")
            
            # Close reply system
            await reply_system.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in Slack reply system check: {e}")
            self.services["slack-reply-system"].error_count += 1
            self.services["slack-reply-system"].last_error = str(e)
            return False
    
    async def run_health_checks(self):
        """Run health checks for all services"""
        logger.info("Running health checks for all MCP services (unified)...")
        
        # Check feedback management (unified)
        self.services["feedback-management-unified"].last_check = datetime.now(timezone.utc)
        if await self.check_feedback_management_unified():
            self.services["feedback-management-unified"].status = "running"
        else:
            self.services["feedback-management-unified"].status = "error"
        
        # Check Reddit MCP (unified)
        self.services["reddit-mcp-unified"].last_check = datetime.now(timezone.utc)
        if await self.check_reddit_mcp_unified():
            self.services["reddit-mcp-unified"].status = "running"
        else:
            self.services["reddit-mcp-unified"].status = "error"
        
        # Check Slack integration (unified)
        self.services["slack-integration-unified"].last_check = datetime.now(timezone.utc)
        if await self.check_slack_integration_unified():
            self.services["slack-integration-unified"].status = "running"
        else:
            self.services["slack-integration-unified"].status = "error"
        
        # Check message processor
        self.services["message-processor"].last_check = datetime.now(timezone.utc)
        if await self.check_message_processor():
            self.services["message-processor"].status = "running"
        else:
            self.services["message-processor"].status = "error"
        
        # Check Slack reply system
        self.services["slack-reply-system"].last_check = datetime.now(timezone.utc)
        if await self.check_slack_reply_system():
            self.services["slack-reply-system"].status = "running"
        else:
            self.services["slack-reply-system"].status = "error"
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report"""
        uptime = datetime.now(timezone.utc) - self.start_time
        
        # Get unified database stats
        db_stats = self.get_unified_database_stats()
        
        return {
            "monitor_status": "running" if self.running else "stopped",
            "uptime_seconds": uptime.total_seconds(),
            "check_interval_seconds": self.check_interval,
            "unified_database": db_stats,
            "services": {
                name: {
                    "status": service.status,
                    "last_check": service.last_check.isoformat(),
                    "processed_count": service.processed_count,
                    "error_count": service.error_count,
                    "last_error": service.last_error
                }
                for name, service in self.services.items()
            },
            "summary": {
                "total_processed": sum(s.processed_count for s in self.services.values()),
                "total_errors": sum(s.error_count for s in self.services.values()),
                "healthy_services": sum(1 for s in self.services.values() if s.status == "running"),
                "total_services": len(self.services)
            }
        }
    
    async def log_status(self):
        """Log current status"""
        report = self.get_status_report()
        logger.info(f"Status Report: {report['summary']['healthy_services']}/{report['summary']['total_services']} services healthy")
        
        # Log database stats
        if 'error' not in report['unified_database']:
            db_stats = report['unified_database']
            logger.info(f"Unified Database: {db_stats['total_messages']} total messages, {db_stats['recent_messages_24h']} recent")
        
        for name, service in self.services.items():
            logger.info(f"  {name}: {service.status} (processed: {service.processed_count}, errors: {service.error_count})")
    
    async def save_status_report(self):
        """Save status report to file"""
        try:
            report = self.get_status_report()
            with open('monitor_status_updated.json', 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving status report: {e}")
    
    async def main_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Unified MCP Monitor (Updated) with Reply System...")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Auto-processing: {'enabled' if self.auto_process else 'disabled'}")
        logger.info(f"Using unified database: {self.unified_db_path}")
        logger.info("📝 Services: Feedback Management, Reddit MCP, Slack Integration, Message Processor, Slack Reply System")
        
        self.running = True
        
        while self.running:
            try:
                # Run health checks
                await self.run_health_checks()
                
                # Log status
                await self.log_status()
                
                # Save status report
                await self.save_status_report()
                
                # Wait for next check
                logger.info(f"⏰ Next check in {self.check_interval} seconds...")
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds before retrying
        
        logger.info("🛑 Unified MCP Monitor (Updated) stopped")

async def main():
    """Main entry point"""
    monitor = UnifiedMCPMonitorUpdated()
    await monitor.main_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
