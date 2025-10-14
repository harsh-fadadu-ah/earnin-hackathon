#!/usr/bin/env python3
"""
Test script to check available Slack channels and validate the bot's access
"""

import asyncio
import os
from slack_sdk.web.async_client import AsyncWebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('env.local')

async def test_slack_channels():
    """Test Slack channels and bot access"""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN not found in environment")
        return
    
    print(f"🔑 Bot token found: {bot_token[:20]}...")
    
    client = AsyncWebClient(token=bot_token)
    
    try:
        # Test bot authentication
        print("\n🔍 Testing bot authentication...")
        auth_response = await client.auth_test()
        if auth_response.get("ok"):
            print(f"✅ Bot authenticated as: {auth_response.get('user')}")
            print(f"   Team: {auth_response.get('team')}")
        else:
            print(f"❌ Authentication failed: {auth_response.get('error')}")
            return
        
        # List all channels
        print("\n📋 Listing all channels...")
        channels_response = await client.conversations_list(types="public_channel,private_channel")
        
        if channels_response.get("ok"):
            channels = channels_response.get("channels", [])
            print(f"Found {len(channels)} channels:")
            
            # Check for our target channels
            target_channels = [
                "help-cashout-experience",
                "help-earnin-card", 
                "help-money-movement",
                "help-analytics",
                "help-edx-accountverification",
                "help-marketing",
                "help-performance-ux",
                "help-cx",
                "help-security"
            ]
            
            print("\n🎯 Checking target channels:")
            found_channels = []
            
            for channel in channels:
                channel_name = channel.get("name", "")
                channel_id = channel.get("id", "")
                is_member = channel.get("is_member", False)
                is_private = channel.get("is_private", False)
                
                if channel_name in target_channels:
                    status = "✅" if is_member else "❌"
                    privacy = "private" if is_private else "public"
                    print(f"  {status} #{channel_name} ({channel_id}) - {privacy}")
                    found_channels.append(channel_name)
            
            missing_channels = set(target_channels) - set(found_channels)
            if missing_channels:
                print(f"\n⚠️  Missing channels: {', '.join(missing_channels)}")
            
            # Test posting to a channel (if we have access)
            accessible_channels = [ch for ch in channels if ch.get("is_member", False) and ch.get("name") in target_channels]
            
            if accessible_channels:
                test_channel = accessible_channels[0]
                print(f"\n🧪 Testing message posting to #{test_channel['name']}...")
                
                try:
                    response = await client.chat_postMessage(
                        channel=test_channel["id"],
                        text="🧪 Test message from message processor integration"
                    )
                    
                    if response.get("ok"):
                        print(f"✅ Successfully posted test message to #{test_channel['name']}")
                        print(f"   Message timestamp: {response.get('ts')}")
                    else:
                        print(f"❌ Failed to post message: {response.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Error posting test message: {e}")
            else:
                print("\n⚠️  No accessible target channels found for testing")
        
        else:
            print(f"❌ Failed to list channels: {channels_response.get('error')}")
    
    except Exception as e:
        print(f"❌ Error testing Slack integration: {e}")
    
    finally:
        # AsyncWebClient doesn't have a close method
        pass

if __name__ == "__main__":
    asyncio.run(test_slack_channels())
