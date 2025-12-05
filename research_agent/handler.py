"""
Discord Bot Wrapper for Research Agent
Handles Discord interactions and streaming updates
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from typing import Optional
import os

from research_agent.agent import ResearchAgent

from agent_graph.logger import log_info, log_error


class ResearchCog(commands.Cog):
    """Discord Cog for research commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_researches = {}  # Track active research sessions

        # Initialize research agent
        # You can configure these via environment variables
        self.agent = ResearchAgent(
            llm_provider=os.getenv("LLM_PROVIDER", "google"),
            model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
            api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            temperature=0.1,
            max_iterations=15,
        )

    @app_commands.command(
        name="research", description="Conduct deep research on any topic using AI"
    )
    @app_commands.describe(topic="The topic or question you want to research")
    async def research_command(self, interaction: discord.Interaction, topic: str):
        """
        Discord slash command for research

        Usage: /research <topic>
        """
        # Defer the response since research will take time
        await interaction.response.defer(thinking=True)

        # Check if user already has an active research
        user_id = interaction.user.id
        if user_id in self.active_researches:
            await interaction.followup.send(
                "❌ You already have an active research in progress. Please wait for it to complete.",
                ephemeral=True,
            )
            return

        # Mark user as having active research
        self.active_researches[user_id] = True

        # Create initial embed
        initial_embed = discord.Embed(
            title="🔬 Deep Research Agent Activated",
            description=f"**Topic**: {topic}\n\n*Initializing research...*",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        initial_embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        # Send initial message
        progress_message = await interaction.followup.send(
            embed=initial_embed, wait=True
        )

        # Create callback for streaming updates
        update_queue = asyncio.Queue()

        async def discord_callback(message: str, embed_data: Optional[dict] = None):
            """Callback to send updates to Discord"""
            await update_queue.put((message, embed_data))

        # Create task for processing updates
        async def process_updates():
            """Process and send updates to Discord"""
            last_update_time = asyncio.get_event_loop().time()
            update_buffer = []

            while True:
                try:
                    # Wait for update with timeout
                    message, embed_data = await asyncio.wait_for(
                        update_queue.get(), timeout=2.0
                    )

                    update_buffer.append((message, embed_data))
                    current_time = asyncio.get_event_loop().time()

                    # Batch updates to avoid rate limits (update every 2 seconds)
                    if current_time - last_update_time >= 2.0 or embed_data:
                        await send_batched_updates(update_buffer)
                        update_buffer = []
                        last_update_time = current_time

                except asyncio.TimeoutError:
                    # Send any buffered updates
                    if update_buffer:
                        await send_batched_updates(update_buffer)
                        update_buffer = []
                        last_update_time = asyncio.get_event_loop().time()
                    continue
                except asyncio.CancelledError:
                    # Send remaining updates before exit
                    if update_buffer:
                        await send_batched_updates(update_buffer)
                    break

        async def send_batched_updates(updates):
            """Send batched updates to Discord"""
            if not updates:
                return

            try:
                # If last update has embed data, use that
                last_update = updates[-1]
                if last_update[1]:
                    embed = discord.Embed(
                        title=last_update[1].get("title", "Research Update"),
                        description=last_update[1].get("description", ""),
                        color=last_update[1].get("color", discord.Color.blue()),
                    )
                    if "timestamp" in last_update[1]:
                        embed.timestamp = discord.utils.utcnow()

                    await progress_message.edit(embed=embed)
                else:
                    # Combine text updates
                    combined_text = "\n".join(msg for msg, _ in updates if msg)
                    if len(combined_text) > 300:
                        combined_text = combined_text[-300:]

                    current_embed = (
                        progress_message.embeds[0] if progress_message.embeds else None
                    )
                    if current_embed:
                        # Update description
                        new_desc = f"{current_embed.description}\n\n{combined_text}"
                        # Keep description under Discord's limit
                        if len(new_desc) > 2000:
                            new_desc = "...\n" + new_desc[-1900:]

                        current_embed.description = new_desc
                        await progress_message.edit(embed=current_embed)

            except discord.HTTPException as e:
                log_error(f"Error updating Discord message: {e}")

        # Start update processor
        update_task = asyncio.create_task(process_updates())

        try:
            # Configure agent with callback
            self.agent.discord_callback = discord_callback

            # Execute research
            result = await self.agent.research(topic)

            # Cancel update processor
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass

            # Send final result in chunks if too long
            if len(result) > 2000:
                # Split into chunks
                chunks = [result[i : i + 2000] for i in range(0, len(result), 2000)]

                # Send first chunk as edit
                final_embed = discord.Embed(
                    title="✅ Research Complete",
                    description=chunks[0],
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                final_embed.set_footer(
                    text=f"Research by {interaction.user.display_name}"
                )
                await progress_message.edit(embed=final_embed)

                # Send remaining chunks as follow-ups
                for i, chunk in enumerate(chunks[1:], 1):
                    continuation_embed = discord.Embed(
                        title=f"📄 Research Results (Part {i + 1})",
                        description=chunk,
                        color=discord.Color.green(),
                    )
                    await interaction.followup.send(embed=continuation_embed)
            else:
                final_embed = discord.Embed(
                    title="✅ Research Complete",
                    description=result,
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow(),
                )
                final_embed.set_footer(
                    text=f"Research by {interaction.user.display_name}"
                )
                await progress_message.edit(embed=final_embed)

        except Exception as e:
            log_error(f"Error during research: {e}", exc_info=True)

            # Cancel update processor
            update_task.cancel()

            error_embed = discord.Embed(
                title="❌ Research Failed",
                description=f"An error occurred during research:\n```{str(e)}```",
                color=discord.Color.red(),
            )
            await progress_message.edit(embed=error_embed)

        finally:
            # Remove user from active researches
            if user_id in self.active_researches:
                del self.active_researches[user_id]


async def setup_research_bot(bot: commands.Bot):
    """
    Setup function to add the research cog to your bot

    Usage in your main bot file:
        from discord_research_wrapper import setup_research_bot

        await setup_research_bot(bot)
    """
    await bot.add_cog(ResearchCog(bot))
    log_info("Research cog loaded successfully")


# Example: Standalone bot (for testing)
# async def main():
#     """Example of running the bot standalone"""
#     intents = discord.Intents.default()
#     intents.message_content = True

#     bot = commands.Bot(command_prefix="!", intents=intents)

#     @bot.event
#     async def on_ready():
#         logger.info(f"Bot logged in as {bot.user}")
#         await setup_research_bot(bot)

#         # Sync commands
#         try:
#             synced = await bot.tree.sync()
#             logger.info(f"Synced {len(synced)} command(s)")
#         except Exception as e:
#             logger.error(f"Failed to sync commands: {e}")

#     # Run bot
#     token = os.getenv("DISCORD_BOT_TOKEN")
#     if not token:
#         raise ValueError("DISCORD_BOT_TOKEN environment variable not set")

#     await bot.start(token)


# if __name__ == "__main__":
#     asyncio.run(main())
