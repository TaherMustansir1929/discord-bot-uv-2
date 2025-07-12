# Importing libraries and modules
import asyncio
import logging
import os
import sys
from typing import Literal, Optional
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord.ext.commands import Context

# Import custom logger
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_system, setup_logging
)

from handlers.assistant import ai_handler
from handlers.channel_restriction import channel_restriction_handler
from handlers.image_edit import image_edit_handler
from handlers.minecraft_channel import minecraft_channel_handler
from handlers.poetry import poetry_handler
from handlers.rate import rate_handler
from handlers.rizz import rizz_handler
from handlers.speak import speak_handler
from handlers.user_roaster import user_roaster_handler
from handlers.word_counter import word_counter_handler
from handlers.zeo import zeo_handler
from handlers.image_gen import image_handler

# Dictionary to store chat history for each user
chat_histories_poetry = {}

# Set up logging with rich
setup_logging()

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

if not token:
    log_error("DISCORD_TOKEN not found in environment variables")
    sys.exit(1)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    if bot.user is not None:
        log_success(f"Bot is ready! Logged in as {bot.user.name} (ID: {bot.user.id})")
        log_info(f"Connected to {len(bot.guilds)} guilds")
        log_info(f"Connected to the following guilds:")
        for guild in bot.guilds:
            log_info(f"- {guild.name} (ID: {guild.id})")


@bot.event
async def on_member_join(member):
    welcome_message = f"Welcome to the server {member.name}! We're glad to have you here! 😊"
    await member.send(welcome_message)
    log_info(f"Sent welcome message to {member.name} (ID: {member.id})")


@bot.command(brief="Secret command. Beware.")
async def secret(ctx):
    secret_message = "Welcome to the club twin! There are no secrets here. Just be yourself and spread positivity. Luv you gng! 🥀❤"
    await ctx.send(secret_message)
    log_info(f"Secret command used by {ctx.author.name} (ID: {ctx.author.id})")


# -------------------------------------------------------------------------------------
# -----------------------------MY CUSTOM COMMANDS--------------------------------------
# -------------------------------------------------------------------------------------

# --------LANGGRAPH IMPLEMENTATION--------
from agent_graph.graph import agent_graph

@bot.command(
    name="zeo",
    brief="Ask me your stupid questions and Imma reply respectfully 😏🥀",
    help="Ask me your stupid questions and Imma reply respectfully 😏🥀",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def zeo(ctx: Context, *, msg: str):
    
    await zeo_handler(bot=bot, ctx=ctx, msg=msg)

@zeo.error
async def zeo_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occurred -> {error}")


# -----------NORMAL LLM CHAT---------
@bot.command(
    brief="Talk to AI",
    help="Use this command to access an AI chatbot directly into the server.",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def ai(ctx, *, msg):
    
    await ai_handler(bot=bot, ctx=ctx, msg=msg)

@ai.error
async def ai_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occurred -> {error}")
    

# ----------11LabsAudioCommand---------
@bot.command(
    brief="Talk to AI through 11Labs",
    help="Use this command to make your bot speak for itself.",
)
@commands.cooldown(1, 60, commands.BucketType.user)
async def speak(ctx, handler, *, msg):

    if handler not in ["zeo", "ai", "poetry"]:
        await ctx.reply("Invalid handler. Please use one of the following: zeo, ai, poetry")
        return
    
    if handler == "ai":
        handler = "assistant"

    await speak_handler(bot=bot, ctx=ctx, handler=handler, msg=msg)

@speak.error
async def speak_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occurred -> {error}")


# ----------Gemini/Flux/Dall-E/Imagen-ImageGenCommand---------
@bot.command(
    brief="Create AI images using Google Imagen, BFL Flux1.1 Pro, Google Flash or OpenAI Dall-E ",
    help="Use this command to create AI images using Google Gemini or Flux.1 Kontext Pro",
)
@commands.cooldown(1, 30, commands.BucketType.user)
async def image(ctx: Context, model: str, *, msg: str):

    if model not in ["gemini", "flux", "dall-e", "imagen"]:
        await ctx.reply("Invalid model. Please use one of the following: gemini, flux, dall-e, imagen\nExample: !image `gemini` or `flux` or `dall-e` or `imagen` <Your Prompt>")
        return
    
    await image_handler(bot=bot, ctx=ctx, model=model, msg=msg)

@image.error
async def image_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occurred -> {error}")


#----------Gemini / Flux-ImageEditCommand----------
@bot.command(
    brief="Edit an image using Google Gemini or Flux.1 Kontext Pro",
    help="Use this command to edit an image using Google Gemini or Flux.1 Kontext Pro",
)
@commands.cooldown(1, 30, commands.BucketType.user)
async def edit(ctx: Context, handler: Literal["gemini", "flux"]):
    
    if handler not in ["gemini", "flux"]:
        await ctx.reply("Invalid handler. Please use one of the following: gemini, flux")
        return
    
    await image_edit_handler(bot=bot, ctx=ctx, message=ctx.message, handler=handler)

@edit.error
async def edit_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occurred -> {error}")


# ---------SARCASTIC AI COMMANDS-------
@bot.command(
    brief="This command is now deprecated. Please proceed with the new command: `!zeo <Your Msg>`",
    help="This command is now deprecated. Please proceed with the new command: `!zeo <Your Msg>`",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def ask(ctx):
    # await ask_handler(ctx, msg, chat_histories_google_sdk)
    await ctx.reply("This command is now deprecated. Please proceed with the new command: `!zeo <Your Msg>`\n Use `!help` command for further help. Thank You!")


# ---------RIZZ COMMAND-------
@bot.command(
    brief="Spawns a dirty pickup line",
    help="Use this command to generate a dirty sus pickup line",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def rizz(ctx: Context, *, msg: Optional[str]):
    msg = msg if msg is not None else "rizz me up freaky style"
    await rizz_handler(bot=bot, ctx=ctx, msg=msg)


@rizz.error
async def rizz_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occured -> {error}")


# ---------PICKUP LINE RATING COMMAND-------
@bot.command(
    brief="Rates your pickup lines",
    help="Call this command along with your pickup line and it will rate is out of 10",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def rate(ctx: Context, *, msg: str):
    await rate_handler(bot=bot, ctx=ctx, msg=msg)


@rate.error
async def rate_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occured -> {error}")


# ------WORD COUNTER/ CHANNEL RESTRICTION/ USER ROASTER FUNC-----------
@bot.event
async def on_message(message: discord.Message):
    await word_counter_handler(bot, message)
    await user_roaster_handler(bot, message)
    await minecraft_channel_handler(bot, message)
    await channel_restriction_handler(bot, message)


# ------------ Ping command -------------------------
@bot.command(
    brief="Checks the bot's latency.",
    help="Responds with 'Pong!' and the current latency in milliseconds.",
)
async def ping(ctx: Context):
    latency = round(bot.latency * 1000 * 10)  # Latency in milliseconds
    log_panel(
        "🏓 Ping Command",
        f"[bold]User:[/] {ctx.author.name} (ID: {ctx.author.id})\n[bold]Channel:[/] {ctx.channel.name}\n[bold]Latency:[/] {latency / 10}ms", # type: ignore
        border_style="white"
    )
    await ctx.reply(f"Pong! 🏓 ({latency / 10}ms)")


# ----------Spam Messages-------------
@bot.command(hidden=True)
@commands.cooldown(1, 30, commands.BucketType.user)
async def spam_msg(ctx, *, msg: str):
    n = 10
    msg_arr = []

    if "?" in msg:
        msg_arr = msg.split("?")
        
        try:
            n = int(msg_arr[1].strip())
        except (IndexError, ValueError):
            n = 10
    else:
        msg_arr = [msg]

    for i in range(n):
        await ctx.send(f"[{i+1}] {msg_arr[0]}")
        await asyncio.sleep(0.25)  # Use asyncio.sleep in async function


# -----------URDU POETRY COMMAND(SPECIAL)------------------------------
@bot.command(
    brief="Get a beautiful piece of Urdu shayri",
    help="Use this command to generate a piece of Urdu poetry based on your chosen topic",
)
@commands.cooldown(1, 15, commands.BucketType.user)
async def poetry(ctx: Context, *, msg: str):
    await poetry_handler(bot=bot, ctx=ctx, msg=msg)


@poetry.error
async def poetry_error(ctx: Context, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"Please wait {error.retry_after:.2f} seconds before using this command again."
        )
    await ctx.reply(f"Sorry an error occured -> {error}")


bot.run(token=token, log_handler=handler, log_level=logging.ERROR)
