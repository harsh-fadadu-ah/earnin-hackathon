#!/usr/bin/env python3
"""
Script to invite the bot to all target Slack channels
"""

import asyncio
import os
from slack_sdk.web.async_client import AsyncWebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config/env.local')

async def invite_bot_to_channels():
    """Invite the bot to all target channels"""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    
    if not bot_token:
        print("❌ SLACK_BOT_TOKEN not found in environment")
        return
    
    client = AsyncWebClient(token=bot_token)
    
    # Get bot user ID
    try:
        auth_response = await client.auth_test()
        if not auth_response.get("ok"):
            print(f"❌ Authentication failed: {auth_response.get('error')}")
            return
        
        bot_user_id = auth_response.get("user_id")
        bot_name = auth_response.get("user")
        print(f"🤖 Bot: {bot_name} (ID: {bot_user_id})")
        
    except Exception as e:
        print(f"❌ Error getting bot info: {e}")
        return
    
    # Target channels
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
    
    print(f"\n📋 Inviting bot to {len(target_channels)} channels...")
    
    # Get all channels
    try:
        channels_response = await client.conversations_list(types="public_channel,private_channel")
        
        if not channels_response.get("ok"):
            print(f"❌ Failed to list channels: {channels_response.get('error')}")
            return
        
        channels = channels_response.get("channels", [])
        channel_map = {ch["name"]: ch for ch in channels}
        
        success_count = 0
        error_count = 0
        
        for channel_name in target_channels:
            if channel_name not in channel_map:
                print(f"⚠️  Channel #{channel_name} not found")
                continue
            
            channel = channel_map[channel_name]
            channel_id = channel["id"]
            is_member = channel.get("is_member", False)
            
            if is_member:
                print(f"✅ Bot already in #{channel_name}")
                success_count += 1
                continue
            
            try:
                # Invite bot to channel
                response = await client.conversations_invite(
                    channel=channel_id,
                    users=bot_user_id
                )
                
                if response.get("ok"):
                    print(f"✅ Successfully invited bot to #{channel_name}")
                    success_count += 1
                else:
                    error = response.get("error", "Unknown error")
                    print(f"❌ Failed to invite bot to #{channel_name}: {error}")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error inviting bot to #{channel_name}: {e}")
                error_count += 1
        
        print(f"\n📊 Summary:")
        print(f"  ✅ Successfully invited: {success_count}")
        print(f"  ❌ Failed: {error_count}")
        print(f"  📋 Total channels: {len(target_channels)}")
        
        if success_count > 0:
            print(f"\n🎉 Bot is now ready to post messages to {success_count} channels!")
            print("You can now run the message processor to start posting classified messages.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(invite_bot_to_channels())
