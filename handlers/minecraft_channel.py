import os
from discord import Message
from discord.ext.commands import Bot
from dotenv import load_dotenv

from agent_graph.graph import agent_graph
from agent_graph.logger import (
    log_info, log_warning, log_error, log_success, log_debug,
    log_panel, log_loading, log_request_response, log_system
)

load_dotenv()

MINECRAFT_CHANNEL_ID = int(os.getenv("AHD_MINECRAFT_CHANNEL_ID", "0"))
# MINECRAFT_CHANNEL_ID = int(os.getenv("CHANNEL_ID_EXP", "0"))
BOT_ID = 1361449135730982943

async def minecraft_channel_handler(bot: Bot, message: Message):
    if message.channel.id != MINECRAFT_CHANNEL_ID:
        return

    if MINECRAFT_CHANNEL_ID == 0:
        log_error("MINECRAFT_CHANNEL_ID not found in environment variables")
        return
    
    if message.author.id != BOT_ID:
        return
    
    msg = message.content.split("»")
    if len(msg) != 2:
        return
    msg = msg[1].strip()

    handlers_list = ["!ai", "!zeo", "!poetry", "!rate", "!rizz"]

    handler = msg.split(" ")[0]
    if handler not in handlers_list:
        return
    
    handlers_dict = {
        "!ai": "assistant",
        "!zeo": "zeo",
        "!poetry": "poetry",
        "!rate": "rate",
        "!rizz": "rizz"
    }

    handler = handlers_dict[handler]

    # Log the incoming request
    channel_name = getattr(message.channel, 'name', 'DM')
    log_panel(
        "📨 New Minecraft Channel Request",
        f"[bold]User:[/] {message.content.split("»")[0].strip()} \n[bold]Channel:[/] {channel_name} \n[bold]Message:[/] {msg} \n[bold]Handler:[/] {handler}",
        border_style="blue"
    )

    try:
        # Process the request
        with log_loading("Generating response..."):
            ai_response = await agent_graph(ctx=message, msg=msg, handler=handler, log="speak") # type: ignore
    except Exception as e:
        log_error(f"Error processing Minecraft Channel request: {str(e)}")
        return

    response = ai_response.split("%%")[0]
    await message.channel.send(f"`@{message.content.split("»")[0].strip()}` {response}")