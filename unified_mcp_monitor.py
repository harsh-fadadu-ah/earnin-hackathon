#!/usr/bin/env python3
"""
Unified MCP Server Monitor

A comprehensive monitoring system that coordinates all MCP servers and ensures
they check for new posts/messages every minute. This serves as the main entry
point for the entire MCP server ecosystem.
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
        logging.FileHandler('unified_monitor.log'),
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

class UnifiedMCPMonitor:
    """Unified monitor for all MCP servers"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # 1 minute
        self.services: Dict[str, MonitorStatus] = {}
        self.start_time = datetime.now(timezone.utc)
        
        # Initialize service statuses
        self.services = {
            "feedback-management": MonitorStatus(
                name="feedback-management",
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "reddit-mcp": MonitorStatus(
                name="reddit-mcp", 
                last_check=datetime.now(timezone.utc),
                status="stopped"
            ),
            "slack-integration": MonitorStatus(
                name="slack-integration",
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
    
    async def check_feedback_management(self) -> bool:
        """Check feedback management server status"""
        try:
            # Import and use the feedback server components
            from feedback_mcp_server import slack_fetcher, db, normalizer, classifier, scorer
            
            # Just check if components are available and working
            if slack_fetcher.client and slack_fetcher.auto_process_enabled:
                logger.debug("Feedback management: Components healthy")
                return True
            else:
                logger.warning("Feedback management: Components not fully initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error in feedback management check: {e}")
            self.services["feedback-management"].error_count += 1
            self.services["feedback-management"].last_error = str(e)
            return False
    
    async def check_reddit_mcp(self) -> bool:
        """Check and process Reddit MCP server using the working SSL-fixed monitor"""
        try:
            # Use the working Reddit monitor that has SSL bypass
            from reddit_monitor_ssl_fixed import RedditEarnInMonitorSSLFixed
            
            logger.info("Reddit MCP: Using SSL-fixed Reddit monitor to search for 'earnin'...")
            
            # Create monitor instance
            reddit_monitor = RedditEarnInMonitorSSLFixed()
            
            # Fetch new posts (this includes both subreddit-specific and global search)
            total_posts = reddit_monitor.fetch_new_posts()
            
            if total_posts > 0:
                self.services["reddit-mcp"].processed_count += total_posts
                logger.info(f"Reddit MCP: Found {total_posts} new Earnin-related posts")
            else:
                logger.info("Reddit MCP: No new Earnin-related posts found")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in Reddit MCP check: {e}")
            self.services["reddit-mcp"].error_count += 1
            self.services["reddit-mcp"].last_error = str(e)
            return False
    
    async def check_slack_integration(self) -> bool:
        """Check Slack integration and process new messages"""
        try:
            from feedback_mcp_server import slack_fetcher
            
            # Test Slack connection and process new messages
            if slack_fetcher.client:
                # Try to get channel info
                channel_id = slack_fetcher.get_channel_id()
                if channel_id:
                    # Check for new messages and process them
                    if slack_fetcher.auto_process_enabled:
                        processed_count = slack_fetcher.auto_process_new_reviews()
                        if processed_count > 0:
                            logger.info(f"Slack integration: Processed {processed_count} new messages")
                            self.services["slack-integration"].processed_count += processed_count
                        else:
                            logger.debug("Slack integration: No new messages found")
                    else:
                        logger.debug("Slack integration: Auto-processing disabled")
                    return True
                else:
                    logger.warning("Slack integration: Channel not found")
                    return False
            else:
                logger.warning("Slack integration: Client not initialized")
                return False
                
        except Exception as e:
            logger.error(f"Error in Slack integration check: {e}")
            self.services["slack-integration"].error_count += 1
            self.services["slack-integration"].last_error = str(e)
            return False
    
    async def run_health_checks(self):
        """Run health checks for all services"""
        logger.info("Running health checks for all MCP services...")
        
        # Check feedback management
        self.services["feedback-management"].last_check = datetime.now(timezone.utc)
        if await self.check_feedback_management():
            self.services["feedback-management"].status = "running"
        else:
            self.services["feedback-management"].status = "error"
        
        # Check Reddit MCP
        self.services["reddit-mcp"].last_check = datetime.now(timezone.utc)
        if await self.check_reddit_mcp():
            self.services["reddit-mcp"].status = "running"
        else:
            self.services["reddit-mcp"].status = "error"
        
        # Check Slack integration
        self.services["slack-integration"].last_check = datetime.now(timezone.utc)
        if await self.check_slack_integration():
            self.services["slack-integration"].status = "running"
        else:
            self.services["slack-integration"].status = "error"
    
    def get_status_report(self) -> Dict[str, Any]:
        """Generate a comprehensive status report"""
        uptime = datetime.now(timezone.utc) - self.start_time
        
        return {
            "monitor_status": "running" if self.running else "stopped",
            "uptime_seconds": uptime.total_seconds(),
            "check_interval_seconds": self.check_interval,
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
        
        for name, service in self.services.items():
            logger.info(f"  {name}: {service.status} (processed: {service.processed_count}, errors: {service.error_count})")
    
    async def save_status_report(self):
        """Save status report to file"""
        try:
            report = self.get_status_report()
            with open('monitor_status.json', 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving status report: {e}")
    
    async def main_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Unified MCP Monitor...")
        logger.info(f"Check interval: {self.check_interval} seconds")
        logger.info(f"Auto-processing: {'enabled' if self.auto_process else 'disabled'}")
        
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
        
        logger.info("🛑 Unified MCP Monitor stopped")

async def main():
    """Main entry point"""
    monitor = UnifiedMCPMonitor()
    await monitor.main_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
