import os
from dotenv import load_dotenv

load_dotenv()

# Channel where bot commands are allowed
# Set this to the ID of the channel where you want commands to be allowed
# If set to 0, commands will be allowed in all channels
# To get a channel ID, right-click on a channel in Discord and select "Copy ID"
# (Developer Mode must be enabled in Discord settings)
CHANNEL_ID_BOT_TESTING = int(os.getenv("CHANNEL_ID_BOT_TESTING", "0"))
CHANNEL_ID_EXP = int(os.getenv("CHANNEL_ID_EXP", "0"))# Default to 0 if not set
AHD_CHANNEL_ID = int(os.getenv("AHD_CHANNEL_ID", "0"))

async def channel_restriction_handler(bot, message):
    
    if message.content.startswith(bot.command_prefix):
        
        if CHANNEL_ID_BOT_TESTING != 0 and CHANNEL_ID_EXP != 0 and AHD_CHANNEL_ID != 0 and message.channel.id not in [CHANNEL_ID_BOT_TESTING, CHANNEL_ID_EXP, AHD_CHANNEL_ID]:
            
            allowed_channels = [message.guild.get_channel(CHANNEL_ID_BOT_TESTING), message.guild.get_channel(CHANNEL_ID_EXP), message.guild.get_channel(AHD_CHANNEL_ID)]
            
            if allowed_channels:
                # Send a message directing the user to the correct channel
                await message.channel.send(
                    f"{message.author.mention}, commands can only be used in {allowed_channels[2].mention}"
                )
            return  # Don't process the command

    # Process commands only if they're in the allowed channel or if no channel restriction is set
    await bot.process_commands(message)