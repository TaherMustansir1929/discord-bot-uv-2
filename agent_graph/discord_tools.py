import os
from re import DEBUG
import discord
from discord.ext import commands
import asyncio


import discord
from discord.ext import commands

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
token = str(os.getenv("DISCORD_TOKEN") or os.getenv("AHD_DISCORD_TOKEN"))


async def send_message_to_user(userId: str, message: str, bot_instance=None):
    """
    Sends a message to a Discord user via DM using a Discord bot.
    
    Args:
        userId (str): The Discord user ID (as string)
        message (str): The message to send
        bot_instance: The Discord bot instance (optional, uses global bot if None)
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        # Remove all non-digit characters from userId before converting to int
        clean_user_id = ''.join(filter(str.isdigit, userId))
        if not clean_user_id:
            print(f"No valid digits found in userId: {userId}")
            return False
        user_id = int(clean_user_id)
        
        # Get the bot instance (assumes bot is defined globally if not passed)
        if bot_instance is None:
            # You'll need to have your bot instance accessible here
            # This assumes 'bot' is defined in your global scope
            global bot
            client = bot
        else:
            client = bot_instance
        
        # Get the user object
        user = await client.fetch_user(user_id)
        
        if user is None:
            print(f"User with ID {userId} not found")
            return False
        
        # Send the message as a DM
        await user.send(message)
        print(f"Message sent successfully to user {user.name} ({userId})")
        
        # Close the bot after sending the message
        await client.close()
        print("Bot connection closed")
        
        return f"\nMessage sent successfully to user {user.name} ({userId})\nMESSAGE: {message}"
        
    except discord.NotFound:
        print(f"User with ID {userId} not found")
        return f"User with ID {userId} not found"
    except discord.Forbidden:
        print(f"Cannot send message to user {userId} - user may have DMs disabled")
        return f"Cannot send message to user {userId} - user may have DMs disabled"
    except discord.HTTPException as e:
        print(f"HTTP error occurred: {e}")
        return f"HTTP error occurred: {e}"
    except ValueError:
        print(f"Invalid user ID format: {userId} (no valid digits found)")
        return f"Invalid user ID format: {userId} (no valid digits found)"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Unexpected error: {e}"

# Synchronous wrapper function
def send_discord_message(userId: str, message: str):
    """
    Sends a message to a Discord user via DM.
    
    Args:
        userId (str): The Discord user ID (as string)
        message (str): The message to send
    
    Returns:
        str: A message indicating the result of the operation
    """
    @bot.event
    async def on_ready():
        print(f'HELPER BOT:{bot.user} has logged in!')
        try:
            # Get or create event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                return asyncio.create_task(send_message_to_user(userId, message))
            else:
                # If not in async context, run the coroutine
                return loop.run_until_complete(send_message_to_user(userId, message))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(send_message_to_user(userId, message))
    
    # Run the bot
    bot.run(token, log_level=DEBUG)


# Usage example:
if __name__ == "__main__":
    send_discord_message("<@915623041105551420>", "Hello from the bot!")