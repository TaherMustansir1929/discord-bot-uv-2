import random
from discord.ext.commands import Context, Bot
import asyncio
from typing import Optional

from agent_graph.graph import agent_graph
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

# Animated loading messages with emojis
LOADING_MESSAGES = [
    "🧠 Stiring up thoughts...",
    "⚙️ Processing your request...",
    "🤔 Contemplating life choices...",
    "💡 Seeking Enlightenment...",
    "🔥 Running some code...",
    "📡 Communicating with the AI...",
    "🔍 Analyzing your request...",
    "🎯 Focusing on the task...",
    "🚀 Almost there...",
    "✨ Adding the final touches..."
]

async def rizz_handler(bot: Bot, ctx: Context, msg: str):
    """Handle Rizz requests with rich logging and user feedback."""
    msg = msg if msg is not None else "rizz me up freaky style"
    n = len(LOADING_MESSAGES)
    
    # Log the incoming request
    channel_name = getattr(ctx.channel, 'name', 'DM')
    log_panel(
        "📨 New Rizz Request",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {channel_name}\n[bold]Message:[/] {msg}",
        border_style="blue"
    )
    
    # Send initial loading message
    rand_idx = random.randint(0, n-1)
    loading_message = await ctx.send(LOADING_MESSAGES[rand_idx])
    
    # Create a task to update loading message animation
    should_continue = True
    
    async def update_loading():
        nonlocal should_continue
        try:
            while should_continue:
                await asyncio.sleep(0.5)  # Delay between animation frames
                if should_continue:  # Check again after sleep
                    rand_idx = random.randint(0, n-1)
                    try:
                        await loading_message.edit(content=LOADING_MESSAGES[rand_idx])
                    except Exception as edit_error:
                        log_error(f"Error updating loading message: {str(edit_error)}")
                        break
        except Exception as e:
            log_error(f"Error in loading animation: {str(e)}")
    
    # Start the loading animation in the background
    animation_task = bot.loop.create_task(update_loading())
    
    try:
        # Log that we're starting to process the request
        log_info(f"Processing Rizz request from {ctx.author.name} (ID: {ctx.author.id})")
        
        # Process the request
        with log_loading("Generating Rizz response..."):
            ai_response = await agent_graph(ctx=ctx, msg=msg, handler="rizz", log=None)
        
        # Send the response
        await ctx.reply(ai_response)
        log_success(f"Successfully responded to {ctx.author.name} (ID: {ctx.author.id})")
        
    except Exception as e:
        error_msg = f"Error processing Rizz request: {str(e)}"
        log_error(error_msg, e)
        
        # Send error message to the user
        error_response = "❌ Oops! Something went wrong while processing your request. Please try again later."
        await ctx.send(error_response)
        
    finally:
        # Clean up the loading animation
        try:
            should_continue = False
            animation_task.cancel()
            try:
                await loading_message.delete()
            except Exception as delete_error:
                log_error(f"Error deleting loading message: {str(delete_error)}")
        except Exception as e:
            log_error(f"Error during cleanup: {str(e)}")