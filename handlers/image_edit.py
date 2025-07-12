import asyncio
from datetime import datetime
import os
import random
import time
from typing import Literal, Tuple, Optional
import aiofiles
import aiohttp
from discord.ext.commands import Bot, Context
import discord
from pathlib import Path

from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)
from handlers.image_gen import send_image_to_discord
from llms.flux_image_edit import flux_image_edit
from llms.gemini_image_gen import gemini_image_edit

# Animated loading messages with emojis
LOADING_MESSAGES = [
    "🎨 Editing your image...",
    "🖌️ Applying changes...",
    "✨ Enhancing details...",
    "🌈 Adjusting colors...",
    "📸 Finalizing edits...",
    "🎭 Adding artistic touches...",
    "🔍 Perfecting the composition...",
    "🔄 Processing changes..."
]

async def image_edit_handler(bot: Bot, ctx: Context, handler: str, message: discord.Message):
    """Handle image editing requests with rich logging and user feedback."""
    n = len(LOADING_MESSAGES)
    
    # Log the incoming request
    channel_name = getattr(ctx.channel, 'name', 'DM')
    log_panel(
        "🖼️ Image Edit Request",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {channel_name}\n[bold]Handler:[/] {handler}\n[bold]Message:[/] {message.content}",
        border_style="blue"
    )
    
    start_time = time.time()
    
    # Send initial loading message
    rand_idx = random.randint(0, n-1)
    loading_message = await ctx.send(LOADING_MESSAGES[rand_idx])
    should_continue = True
    
    # Function to update loading message
    async def update_loading():
        nonlocal should_continue
        try:
            while should_continue:
                await asyncio.sleep(0.5)
                if should_continue:
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
        if message.author.bot:
            log_debug("Ignoring message from bot")
            return
        
        log_info(f"Starting image edit with handler: {handler}")
        
        # Check if message has attachments
        if not message.attachments:
            error_msg = "No image attachment found in the message"
            log_error(error_msg)
            await ctx.send("❌ Please attach an image to edit.")
            return

        # Save the image with metadata
        log_info("Saving image with metadata...")
        image_path, metadata_path = await save_discord_image_with_metadata(message)
        
        if not image_path:
            error_msg = "Failed to save image or no valid image found"
            log_error(error_msg)
            await ctx.send("❌ Failed to process the attached image. Please try again.")
            return
            
        log_success(f"Image saved as: {os.path.basename(str(image_path))}")
        if metadata_path:
            log_debug(f"Metadata saved to: {os.path.basename(str(metadata_path))}")
        
        # Process the image with the selected handler
        log_info(f"Processing image with {handler}...")
        try:
            if handler == "gemini":
                log_debug("Using Gemini for image editing")
                msg, output_path = gemini_image_edit(message.content, str(image_path))
            elif handler == "flux":
                log_debug("Using Flux for image editing")
                msg, output_path = flux_image_edit(message.content, str(image_path))
            else:
                error_msg = f"Unsupported handler: {handler}"
                log_error(error_msg)
                await ctx.send("❌ Unsupported image editor. Please use 'gemini' or 'flux'.")
                return
            
            if not output_path or not Path(output_path).exists():
                error_msg = "Failed to generate edited image"
                log_error(error_msg)
                await ctx.send("❌ Failed to process the image. Please try again.")
                return

            log_success(f"Successfully processed image with {handler}")
            log_debug(f"Output path: {output_path}")
            
            # Send the edited image
            await send_image_to_discord(
                channel=ctx.channel,
                image_path=str(output_path),
                message=f"{ctx.author.mention} {msg}\n`Edit time: {(time.time() - start_time):.2f} seconds`"
            )
            
        except Exception as proc_error:
            error_msg = f"Error in image processing: {str(proc_error)}"
            log_error(error_msg, exception=proc_error)
            await ctx.send("❌ An error occurred while processing your image.")
    
    except Exception as e:
        error_msg = f"Unexpected error in image_edit_handler: {str(e)}"
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


async def save_discord_image_with_metadata(message, save_directory: str = "images/edit_images/saved_images") -> Tuple[Optional[Path], Optional[Path]]:
    """
    Save a Discord image attachment along with its metadata.
    
    Args:
        message: The Discord message containing the image
        save_directory: Directory to save the image and metadata
        
    Returns:
        Tuple containing (image_path, metadata_path) or (None, None) on failure
    """
    log_info("Saving Discord image with metadata...")
    
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_directory, exist_ok=True)
        log_debug(f"Save directory: {save_directory}")
        
        # Save the image
        image_path = await save_discord_image(message, save_directory)
        if not image_path:
            log_error("Failed to save image")
            return None, None
            
        # Create metadata file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_filename = f"{timestamp}_metadata.txt"
        metadata_path = os.path.join(save_directory, metadata_filename)
        
        try:
            log_debug(f"Saving metadata to: {metadata_path}")
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as file:
                metadata = [
                    f"Message Content: {message.content}",
                    f"Author: {message.author} (ID: {message.author.id})",
                    f"Channel: {message.channel} (ID: {getattr(message.channel, 'id', 'N/A')})",
                    f"Server: {message.guild.name if message.guild else 'DM'}",
                    f"Timestamp: {message.created_at}",
                    f"Image File: {os.path.basename(str(image_path))}"
                ]
                await file.write('\n'.join(metadata))
            
            log_success("Successfully saved image and metadata")
            return Path(image_path), Path(metadata_path)
            
        except Exception as meta_error:
            error_msg = f"Error saving metadata: {str(meta_error)}"
            log_error(error_msg, exception=meta_error)
            return Path(image_path), None
            
    except Exception as e:
        error_msg = f"Unexpected error in save_discord_image_with_metadata: {str(e)}"
        log_error(error_msg, exception=e)
        return None, None


async def save_discord_image(message, save_directory: str = "images/edit_images/saved_images") -> Optional[str]:
    """
    Save an image attachment from a Discord message.
    
    Args:
        message: The Discord message containing the image
        save_directory: Directory to save the image
        
    Returns:
        Path to the saved image or None if failed
    """
    log_info("Saving Discord image...")
    
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_directory, exist_ok=True)
        log_debug(f"Save directory: {save_directory}")
        
        # Check if message has attachments
        if not message.attachments:
            log_error("No attachments found in the message")
            return None
        
        # Find the first image attachment
        image_attachment = None
        for attachment in message.attachments:
            # Check if attachment is an image
            if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                image_attachment = attachment
                log_debug(f"Found image attachment: {attachment.filename} ({attachment.size/1024:.2f} KB)")
                break
        
        if not image_attachment:
            log_error("No supported image attachments found in the message")
            return None
        
        # Generate filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{image_attachment.filename}"
        filepath = os.path.join(save_directory, filename)
        
        log_info(f"Downloading image: {image_attachment.filename}")
        log_debug(f"Source URL: {image_attachment.url}")
        log_debug(f"Destination: {filepath}")
        
        # Download and save the image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_attachment.url) as response:
                if response.status == 200:
                    file_size = 0
                    async with aiofiles.open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)
                            file_size += len(chunk)
                    
                    log_success(f"Image saved successfully: {os.path.basename(filepath)} ({file_size/1024:.2f} KB)")
                    log_debug(f"Message content: {message.content}")
                    log_debug(f"Author: {message.author}")
                    log_debug(f"Channel: {message.channel}")
                    
                    return filepath
                else:
                    error_msg = f"Failed to download image. Status: {response.status}"
                    log_error(error_msg)
                    return None
                    
    except Exception as e:
        error_msg = f"Error in save_discord_image: {str(e)}"
        log_error(error_msg, exception=e)
        return None