from datetime import datetime
import os
from pathlib import Path
import time
import discord
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import random
from discord.ext.commands import Context, Bot
import asyncio

from agent_graph.graph import agent_graph
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)
from llms.dall_e_image_gen import dall_e_image_generator
from llms.gemini_image_gen import gemini_image_gen
from llms.flux_image_gen import flux_image_generator
from llms.google_imagen_image_gen import google_imagen_image_generator

# Animated loading messages with emojis
LOADING_MESSAGES = [
    "🎨 Brushing up the canvas...",
    "🖌️ Sketching your vision...",
    "🌈 Mixing colors...",
    "✨ Adding final touches...",
    "📸 Capturing the moment...",
    "🖼️ Framing your masterpiece...",
    "🎭 Channeling creativity...",
    "🔍 Perfecting the details..."
]

async def image_handler(bot: Bot, ctx: Context, model: str, msg: str):
    """Handle image generation requests with rich logging and user feedback."""
    n = len(LOADING_MESSAGES)
    
    # Log the incoming request
    channel_name = getattr(ctx.channel, 'name', 'DM')
    log_panel(
        "🖼️ Image Generation Request",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {channel_name}\n[bold]Model:[/] {model}\n[bold]Prompt:[/] {msg}",
        border_style="blue"
    )
    
    # Send initial loading message
    rand_idx = random.randint(0, n-1)
    loading_message = await ctx.send(LOADING_MESSAGES[rand_idx])
    should_continue = True
    
    # Function to update loading message
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
        start_time = time.time()
        # Call the appropriate image generation function based on the model
        log_info(f"Generating image with model: {model}")
        if model == "dall-e":
            log_debug("Using DALL-E 3 model for image generation")
            ai_response, image_path = dall_e_image_generator(msg)
        elif model == "gemini":
            log_debug("Using Gemini Flash Preview model for image generation")
            ai_response, image_path = gemini_image_gen(msg)
        elif model == "flux":
            log_debug("Using Flux model for image generation")
            ai_response, image_path = flux_image_generator(msg)
        elif model == "imagen":
            log_debug("Using Google Imagen model for image generation")
            ai_response, image_path = google_imagen_image_generator(msg)
        else:
            error_msg = f"Invalid model specified: {model}"
            log_error(error_msg)
            await ctx.send("❌ Invalid model specified. Please use 'dall-e-3', 'gemini-flash-preview', 'google-imagen-3', or 'flux'.")
            return
        
        log_success(f"Successfully generated image with {model}")
        log_debug(f"Image path: {image_path}")

        await send_image_to_discord(
            channel=ctx.channel,
            image_path=str(image_path),
            message=f"{ctx.author.mention} {ai_response}\n`Execution time: {(time.time() - start_time):.2f} seconds`"
        )

    except Exception as e:
        error_msg = f"Unexpected error in image_handler: {str(e)}"
        log_error(error_msg, exception=e)
        await ctx.send("❌ An unexpected error occurred while processing your request.")
        
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


async def send_image_to_discord(channel, image_path: str, message=None):
    """
    Send an image to a Discord channel with comprehensive logging.
    
    Args:
        channel: The Discord channel to send the image to
        image_path (str): Path to the image file
        message (str, optional): Optional message to send with the image
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        log_info(f"Preparing to send image to channel {getattr(channel, 'name', 'DM')}")
        log_debug(f"Image path: {image_path}")
        
        # Check if the image file exists
        if not Path(image_path).exists():
            error_msg = f"Image file not found: {image_path}"
            log_error(error_msg)
            return False
        
        # Get file size for logging
        file_size = os.path.getsize(image_path) / (1024 * 1024)  # Convert to MB
        log_debug(f"Image size: {file_size:.2f}MB")
        
        # Create discord File object
        try:
            with open(image_path, 'rb') as f:
                picture = discord.File(f)
                
                # Send the image
                log_info("Sending image to Discord...")
                if message:
                    log_debug(f"Including message with image: {message}")
                    await channel.send(message, file=picture)
                else:
                    await channel.send(file=picture)
            
            log_success(f"Image sent successfully to channel '{getattr(channel, 'name', 'DM')}'")
            if message:
                log_debug(f"Message sent with image: {message}")
            return True
            
        except Exception as file_error:
            error_msg = f"Error creating or sending file: {str(file_error)}"
            log_error(error_msg)
            return False
        
    except discord.errors.Forbidden as e:
        error_msg = f"Bot doesn't have permission to send messages in channel {getattr(channel, 'name', 'DM')}"
        log_error(error_msg)
        return False
        
    except discord.errors.HTTPException as e:
        error_msg = f"HTTP error occurred while sending image: {str(e)}"
        log_error(error_msg)
        return False
        
    except Exception as e:
        error_msg = f"Unexpected error in send_image_to_discord: {str(e)}"
        log_error(error_msg, exception=e)
        return False