from discord.ext.commands import Bot
from discord import Message

from agent_graph.graph import agent_graph


TARGET_USERS = [767429290194632726]

async def user_roaster_handler(bot: Bot, message: Message):
    if message.author.id not in TARGET_USERS:
        return
    
    ai_response = await agent_graph(ctx=message, msg=message.content, handler="user_roaster", log="speak")

    response = f"{message.author.mention} {ai_response.split("%%")[0]}" 
    await message.channel.send(response)
    