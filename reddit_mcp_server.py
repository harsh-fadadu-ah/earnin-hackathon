#!/usr/bin/env python3
"""
Reddit MCP Server

A comprehensive MCP server for Reddit operations including searching posts,
fetching subreddit information, and managing Reddit data.
"""

import asyncio
import json
import logging
import os
import praw
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListResourcesRequest, ListResourcesResult,
    ReadResourceRequest, ReadResourceResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("reddit-mcp")

# Constants
JSON_MIME_TYPE = "application/json"

@dataclass
class RedditPost:
    id: str
    title: str
    content: str
    author: str
    subreddit: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: datetime
    url: str
    permalink: str
    is_self: bool
    over_18: bool
    flair: Optional[str] = None

class RedditClient:
    """Reddit API client using PRAW"""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str, 
                 username: str, password: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            username=username,
            password=password
        )
        
        # Test connection
        try:
            self.reddit.user.me()
            logger.info(f"Successfully connected to Reddit as {username}")
        except Exception as e:
            logger.error(f"Failed to connect to Reddit: {e}")
            raise
    
    def search_subreddits(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for subreddits by name"""
        try:
            subreddits = []
            for subreddit in self.reddit.subreddits.search(query, limit=limit):
                subreddits.append({
                    "name": subreddit.display_name,
                    "title": subreddit.title,
                    "description": subreddit.description,
                    "subscribers": subreddit.subscribers,
                    "active_users": getattr(subreddit, 'active_user_count', 0),
                    "created_utc": datetime.fromtimestamp(subreddit.created_utc, tz=timezone.utc).isoformat(),
                    "url": f"https://reddit.com/r/{subreddit.display_name}",
                    "over_18": subreddit.over18
                })
            return subreddits
        except Exception as e:
            logger.error(f"Error searching subreddits: {e}")
            return []
    
    def search_posts(self, query: str, subreddit: Optional[str] = None, 
                    limit: int = 25, sort: str = "new") -> List[RedditPost]:
        """Search for posts across Reddit or in a specific subreddit"""
        try:
            posts = []
            
            if subreddit:
                # Search in specific subreddit
                subreddit_obj = self.reddit.subreddit(subreddit)
                search_results = subreddit_obj.search(query, sort=sort, limit=limit)
            else:
                # Search across all subreddits
                search_results = self.reddit.subreddit("all").search(query, sort=sort, limit=limit)
            
            for submission in search_results:
                post = RedditPost(
                    id=submission.id,
                    title=submission.title,
                    content=submission.selftext if submission.is_self else "",
                    author=str(submission.author) if submission.author else "[deleted]",
                    subreddit=submission.subreddit.display_name,
                    score=submission.score,
                    upvote_ratio=submission.upvote_ratio,
                    num_comments=submission.num_comments,
                    created_utc=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                    url=submission.url,
                    permalink=f"https://reddit.com{submission.permalink}",
                    is_self=submission.is_self,
                    over_18=submission.over_18,
                    flair=submission.link_flair_text
                )
                posts.append(post)
            
            return posts
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            return []
    
    def get_subreddit_posts(self, subreddit_name: str, limit: int = 25, 
                           sort: str = "new") -> List[RedditPost]:
        """Get posts from a specific subreddit"""
        try:
            posts = []
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Get posts based on sort method
            if sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "new":
                submissions = subreddit.new(limit=limit)
            elif sort == "top":
                submissions = subreddit.top(limit=limit)
            elif sort == "rising":
                submissions = subreddit.rising(limit=limit)
            else:
                submissions = subreddit.new(limit=limit)
            
            for submission in submissions:
                post = RedditPost(
                    id=submission.id,
                    title=submission.title,
                    content=submission.selftext if submission.is_self else "",
                    author=str(submission.author) if submission.author else "[deleted]",
                    subreddit=submission.subreddit.display_name,
                    score=submission.score,
                    upvote_ratio=submission.upvote_ratio,
                    num_comments=submission.num_comments,
                    created_utc=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                    url=submission.url,
                    permalink=f"https://reddit.com{submission.permalink}",
                    is_self=submission.is_self,
                    over_18=submission.over_18,
                    flair=submission.link_flair_text
                )
                posts.append(post)
            
            return posts
        except Exception as e:
            logger.error(f"Error getting subreddit posts: {e}")
            return []
    
    def get_subreddit_info(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a subreddit"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            return {
                "name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "public_description": subreddit.public_description,
                "subscribers": subreddit.subscribers,
                "active_users": getattr(subreddit, 'active_user_count', 0),
                "created_utc": datetime.fromtimestamp(subreddit.created_utc, tz=timezone.utc).isoformat(),
                "url": f"https://reddit.com/r/{subreddit.display_name}",
                "over_18": subreddit.over18,
                "quarantine": subreddit.quarantine,
                "submission_type": subreddit.submission_type
            }
        except Exception as e:
            logger.error(f"Error getting subreddit info: {e}")
            return None

# Initialize Reddit client with provided credentials
reddit_client = RedditClient(
    client_id="k3n3Jc9hKlpm0OBC9f5VoA",
    client_secret="GM2yWaXXS7-SCwMq5KUpARLh2bqg2A",
    user_agent="FeedForward",
    username="Best_Mirror2588",
    password="Harsh_password"
)

# MCP Tools Implementation

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_subreddits",
            description="Search for subreddits by name or topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for subreddit names"},
                    "limit": {"type": "integer", "description": "Maximum number of subreddits to return", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_posts",
            description="Search for posts across Reddit or in a specific subreddit",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for posts"},
                    "subreddit": {"type": "string", "description": "Specific subreddit to search (optional)"},
                    "limit": {"type": "integer", "description": "Maximum number of posts to return", "default": 25},
                    "sort": {"type": "string", "description": "Sort method (new, hot, top, rising)", "default": "new"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_subreddit_posts",
            description="Get posts from a specific subreddit",
            inputSchema={
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Subreddit name"},
                    "limit": {"type": "integer", "description": "Maximum number of posts to return", "default": 25},
                    "sort": {"type": "string", "description": "Sort method (new, hot, top, rising)", "default": "new"}
                },
                "required": ["subreddit"]
            }
        ),
        Tool(
            name="get_subreddit_info",
            description="Get information about a specific subreddit",
            inputSchema={
                "type": "object",
                "properties": {
                    "subreddit": {"type": "string", "description": "Subreddit name"}
                },
                "required": ["subreddit"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "search_subreddits":
            return search_subreddits(arguments)
        elif name == "search_posts":
            return search_posts(arguments)
        elif name == "get_subreddit_posts":
            return get_subreddit_posts(arguments)
        elif name == "get_subreddit_info":
            return get_subreddit_info(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")]
            )
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")]
        )

# Tool implementations

def search_subreddits(arguments: Dict[str, Any]) -> CallToolResult:
    """Search for subreddits by name or topic"""
    query = arguments["query"]
    limit = arguments.get("limit", 10)
    
    subreddits = reddit_client.search_subreddits(query, limit)
    
    result = {
        "query": query,
        "count": len(subreddits),
        "subreddits": subreddits
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Found {len(subreddits)} subreddits for query '{query}':\n{json.dumps(result, indent=2)}"
        )]
    )

def search_posts(arguments: Dict[str, Any]) -> CallToolResult:
    """Search for posts across Reddit or in a specific subreddit"""
    query = arguments["query"]
    subreddit = arguments.get("subreddit")
    limit = arguments.get("limit", 25)
    sort = arguments.get("sort", "new")
    
    posts = reddit_client.search_posts(query, subreddit, limit, sort)
    
    # Convert posts to dictionaries for JSON serialization
    posts_data = []
    for post in posts:
        post_dict = asdict(post)
        post_dict["created_utc"] = post.created_utc.isoformat()
        posts_data.append(post_dict)
    
    result = {
        "query": query,
        "subreddit": subreddit,
        "sort": sort,
        "count": len(posts),
        "posts": posts_data
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Found {len(posts)} posts for query '{query}':\n{json.dumps(result, indent=2)}"
        )]
    )

def get_subreddit_posts(arguments: Dict[str, Any]) -> CallToolResult:
    """Get posts from a specific subreddit"""
    subreddit = arguments["subreddit"]
    limit = arguments.get("limit", 25)
    sort = arguments.get("sort", "new")
    
    posts = reddit_client.get_subreddit_posts(subreddit, limit, sort)
    
    # Convert posts to dictionaries for JSON serialization
    posts_data = []
    for post in posts:
        post_dict = asdict(post)
        post_dict["created_utc"] = post.created_utc.isoformat()
        posts_data.append(post_dict)
    
    result = {
        "subreddit": subreddit,
        "sort": sort,
        "count": len(posts),
        "posts": posts_data
    }
    
    return CallToolResult(
        content=[TextContent(
            type="text", 
            text=f"Found {len(posts)} posts from r/{subreddit}:\n{json.dumps(result, indent=2)}"
        )]
    )

def get_subreddit_info(arguments: Dict[str, Any]) -> CallToolResult:
    """Get information about a specific subreddit"""
    subreddit = arguments["subreddit"]
    
    info = reddit_client.get_subreddit_info(subreddit)
    
    if info:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Subreddit info for r/{subreddit}:\n{json.dumps(info, indent=2)}"
            )]
        )
    else:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=f"Could not find subreddit r/{subreddit}"
            )]
        )

# Resources

@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="reddit-connection",
            name="Reddit Connection Status",
            description="Current Reddit API connection status and user information",
            mimeType=JSON_MIME_TYPE
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read resource content"""
    if uri == "reddit-connection":
        try:
            user = reddit_client.reddit.user.me()
            connection_info = {
                "connected": True,
                "username": str(user),
                "user_id": user.id,
                "created_utc": datetime.fromtimestamp(user.created_utc, tz=timezone.utc).isoformat(),
                "comment_karma": user.comment_karma,
                "link_karma": user.link_karma,
                "is_employee": user.is_employee,
                "is_mod": user.is_mod,
                "is_gold": user.is_gold
            }
        except Exception as e:
            connection_info = {
                "connected": False,
                "error": str(e)
            }
        
        return ReadResourceResult(
            contents=[TextContent(type="text", text=json.dumps(connection_info, indent=2))]
        )
    else:
        return ReadResourceResult(
            contents=[TextContent(type="text", text=f"Resource {uri} not found")]
        )

async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="reddit-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())

