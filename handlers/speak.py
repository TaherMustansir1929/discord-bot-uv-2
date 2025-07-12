from datetime import datetime
import os
from pathlib import Path
import random
import shutil
from typing import Literal, Optional
import asyncio
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext.commands import Context, Bot

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

from agent_graph.graph import agent_graph
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

# Animated loading messages with emojis
LOADING_MESSAGES = [
    "🧠 Thinking deeply...",
    "🤔 Contemplating life choices...",
    "💡 Having an epiphany...",
    "🔍 Analyzing your request...",
    "🎯 Focusing on the task...",
    "🚀 Almost there...",
    "✨ Adding the final touches...",
    "🎭 Channeling my inner philosopher..."
]
n = len(LOADING_MESSAGES)

async def speak_handler(bot: Bot, ctx: Context, handler: Literal['zeo', 'assistant', 'rizz', 'rate', 'react', 'word_count', 'poetry'], msg: str):
    """Handle zeo requests with rich logging and user feedback."""
    n = len(LOADING_MESSAGES)
    
    # Log the incoming request
    channel_name = getattr(ctx.channel, 'name', 'DM')
    log_panel(
        "🎭 Speak Request",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {channel_name}\n[bold]Message:[/] {msg}",
        border_style="magenta"
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
        ai_response = await agent_graph(ctx=ctx, msg=msg, handler=handler, log="speak")
        # Clean the response
        responses = ai_response.split("%%")
        ai_response = responses[0]
        final_response = responses[1]

        try:
            audio_file = eleven_labs_api(ai_response, handler)
            await send_audio(ctx.channel, audio_file, final_response)
            log_success(f"Successfully sent audio response for handler: {handler}")
        except Exception as e:
            log_error(f"Error in speak_handler: {str(e)}")
            await ctx.send(f"❌ An error occurred while processing your request: {str(e)}")
    
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

    

def eleven_labs_api(text: str, handler: Optional[str]=None):
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        raise ValueError("API key is required. Either pass it as parameter or set ELEVENLABS_API_KEY environment variable.")
    audio_folder = "audio"
    os.makedirs(audio_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"speech_{timestamp}.mp3"

    # Full path for the output file
    output_path = os.path.join(audio_folder, filename)

    elevenlabs = ElevenLabs(
        api_key=api_key,
    )

    voice_id = "nPczCjzI2devNBz1zQrb" # Brian - Default Voice
    if handler == "assistant":
        voice_id = "77aEIu0qStu8Jwv1EdhX" # Ayinde - Nigerian Accent
    elif handler == "zeo":
        voice_id = "nPczCjzI2devNBz1zQrb" # Brian - Default Voice
    elif handler == "poetry":
        voice_id = "N2lVS1w4EtoT3dr4eOWO" # Callum - Deep Voice
    
    response = elevenlabs.text_to_speech.convert(
        voice_id=voice_id,
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",
        # Optional voice settings that allow you to customize the output
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # Writing the audio to a file
    with open(output_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    log_success(f"Audio file saved successfully: {output_path}")
    return output_path


async def send_audio(channel, file_path: str, message: Optional[str]=None):
    try:
        # Convert file_path to Path object for easier handling
        audio_path = Path(file_path)
        
        # Check if file exists
        if not audio_path.exists():
            error_msg = f"Audio file not found: {file_path}"
            log_error(error_msg)
            return None
        
        # Check file size (Discord has 25MB limit for regular users, 100MB for Nitro)
        file_size = audio_path.stat().st_size
        max_size = 25 * 1024 * 1024  # 25MB in bytes
        
        if file_size > max_size:
            error_msg = f"File size ({file_size / (1024*1024):.2f}MB) exceeds Discord's 25MB limit"
            log_error(error_msg)
            return None
        
        # Create Discord File object
        discord_file = discord.File(audio_path)
        
        # Send the file
        if message:
            sent_message = await channel.send(content=message, file=discord_file)
        else:
            sent_message = await channel.send(file=discord_file)
        
        log_success(f"Successfully sent audio file: {audio_path.name}")
        return sent_message
        
    except discord.Forbidden as e:
        error_msg = "Bot doesn't have permission to send files in this channel"
        log_error(error_msg)
        return None
    except discord.HTTPException as e:
        error_msg = f"HTTP error while sending file: {str(e)}"
        log_error(error_msg)
        return None
    except Exception as e:
        error_msg = f"Unexpected error while sending file: {str(e)}"
        log_error(error_msg)
        return None


def delete_directory(directory_path):
    try:
        # Convert to Path object for easier handling
        path = Path(directory_path)
        
        # Check if directory exists
        if not path.exists():
            raise FileNotFoundError(f"Directory '{directory_path}' does not exist")
        
        # Check if it's actually a directory
        if not path.is_dir():
            raise ValueError(f"'{directory_path}' is not a directory")
        
        # Delete the directory and all its contents
        shutil.rmtree(path)
        log_info(f"Successfully deleted directory: {directory_path}")
        return True
        
    except Exception as e:
        log_error(f"Error deleting directory '{directory_path}': {str(e)}")
        return False