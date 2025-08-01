from discord.ext.commands import Bot, Context
import os
import requests
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
import time
import random
import asyncio

from handlers.image_gen import send_image_to_discord
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)


# Animated loading messages with emojis
LOADING_MESSAGES = [
    "🎭 Channeling creativity...",
    "🔍 Perfecting the details...",
    "💫 Summoning your waifu...",
    "🧩 Piecing together anime magic...",
    "🚀 Fetching from waifu dimension...",
    "🕵️‍♂️ Searching for the best waifu...",
    "🎬 Animating your request...",
    "✨ Adding final touches...",
]


SFW_CATEGORIES = [
    "waifu",
    "neko",
    "shinobu",
    "megumin",
    "bully",
    "cuddle",
    "cry",
    "hug",
    "awoo",
    "kiss",
    "lick",
    "pat",
    "smug",
    "bonk",
    "yeet",
    "blush",
    "smile",
    "wave",
    "highfive",
    "handhold",
    "nom",
    "bite",
    "glomp",
    "slap",
    "kill",
    "kick",
    "happy",
    "wink",
    "poke",
    "dance",
    "cringe"
]
NSFW_CATEGORIES = [
"waifu",
"neko",
"trap",
"blowjob"]


async def anime_handler(bot: Bot, ctx: Context, fw: Optional[str], category: Optional[str]):
    """Handles the anime command to generate a random anime images or gifs."""
    if category and category.lower() == "help":
        log_info("User requested help for anime command")
        
        await ctx.send(
            f"""
            Command Usage: `!anime [category] [sfw|nsfw]`
            Available categories:
            `NSFW`: {', '.join(NSFW_CATEGORIES)}
            `SFW`: {', '.join(SFW_CATEGORIES)}
            """
        )
        
        log_success("Sent help message for anime command")
        return
    
    if fw is not None and fw.lower() not in ["sfw", "nsfw"]:
        log_error(f"Invalid content type: {fw}")
        
        await ctx.reply(
            "Invalid content type. Please use 'sfw' or 'nsfw'."
        )
        raise ValueError("Invalid content type specified")

    nsfw = True if fw and fw.lower() == "nsfw" else False

    if category is not None:
        if nsfw:
            if category.lower() not in NSFW_CATEGORIES:
                await ctx.reply(
                    f"Invalid category for NSFW content. Please choose from: {', '.join(NSFW_CATEGORIES)}"
                )
                return
        else:
            if category.lower() not in SFW_CATEGORIES:
                await ctx.reply(
                    f"Invalid category for SFW content. Please choose from: {', '.join(SFW_CATEGORIES)}"
                )
                return
    
    n = len(LOADING_MESSAGES)
    
    # Log the incoming request
    channel_name = getattr(ctx.channel, 'name', 'DM')
    log_panel(
        "🖼️ Anime Image Request",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {channel_name}\n[bold]Category:[/] {category}\n[bold]Content Type:[/] {fw}",
        border_style="purple"
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

        success, message, file_path = fetch_random_anime(
            save_folder="images/anime",
            category=category.lower() if category else "waifu",
            sfw=not nsfw
        )
        
        if success and file_path:
            log_success(f"{message}")
            log_success(f"File 📁 Saved to: {file_path}")
        else:
            log_error(f"{message}")
            raise ValueError(message)

        await send_image_to_discord(
            channel=ctx.channel,
            image_path=file_path,
            message=f"{ctx.author.mention} Here's your `{"nsfw" if nsfw else "sfw"}` type, `{category}` category anime image! \n`Execution time: {(time.time() - start_time):.2f} seconds`",
        )
        
        log_success(f"\nImage sent successfully to {ctx.channel.name} by {ctx.author.name}\nCompleted in {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        error_msg = f"Unexpected error in anime_handler: {str(e)}"
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


def fetch_random_anime(save_folder="images/anime", category="waifu", sfw=False) -> tuple[bool, str, Optional[str]]:
    """
    Fetches a random anime waifu image from waifu.pics API and saves it to specified folder.
    
    Args:
        save_folder (str): Folder path to save images (default: "waifu_images")
        category (str): Image category - "waifu", "neko", "shinobu", "megumin", "bully", "cuddle", "cry", "hug", "awoo", "kiss", "lick", "pat", "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", "handhold", "nom", "bite", "glomp", "slap", "kill", "kick", "happy", "wink", "poke", "dance", "cringe"
        sfw (bool): Safe for work content (True) or NSFW (False)
    
    Returns:
        tuple: (success: bool, message: str, file_path: str or None)
    """
    
    log_info(f"Starting fetch for random waifu image in category '{category}' (SFW: {sfw})")
    
    # Create folder if it doesn't exist
    try:
        os.makedirs(save_folder, exist_ok=True)
    except Exception as e:
        log_error(f"Failed to create folder '{save_folder}': {str(e)}")
        return False, f"Failed to create folder: {str(e)}", None
    
    # Construct API URL
    base_url = "https://api.waifu.pics"
    content_type = "sfw" if sfw else "nsfw"
    api_url = f"{base_url}/{content_type}/{category}"
    
    log_debug(f"Constructed API URL: {api_url}")
    
    try:
        # Make API request
        with log_loading(f"Making API Request to {api_url}..."):
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

        # Parse JSON response
        data = response.json()
        image_url = data.get('url')
        
        if not image_url:
            log_error("No image URL found in API response")
            return False, "No image URL found in API response", None

        log_info(f"Found image: {image_url}")

        # Download the image
        with log_loading("Downloading image..."):
            img_response = requests.get(image_url, timeout=5000)
            img_response.raise_for_status()
        log_success("Image downloaded successfully")
        
        # Generate filename with timestamp
        parsed_url = urlparse(image_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.png'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category}_{timestamp}{file_extension}"
        file_path = os.path.join(save_folder, filename)
        
        # Save image to file
        with open(file_path, 'wb') as f:
            f.write(img_response.content)
        
        log_success(f"Image saved successfully: {file_path}")
        
        file_size = len(img_response.content)
        return True, f"Successfully saved {filename} ({file_size} bytes)", file_path
        
    except requests.exceptions.RequestException as e:
        log_error(f"Network error while fetching image: {str(e)}")
        return False, f"Network error: {str(e)}", None
    except Exception as e:
        log_error(f"Unexpected error while fetching image: {str(e)}")
        return False, f"Unexpected error: {str(e)}", None
