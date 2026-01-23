
import config
import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import logging
from services.db_manager import db

logger = logging.getLogger("HealthMonitor")

class Health(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.heartbeat_loop.start()

    def cog_unload(self):
        self.heartbeat_loop.cancel()

    @tasks.loop(seconds=60)
    async def heartbeat_loop(self):
        
        logger.info(f"HEARTBEAT: Bot active for {int(time.time() - self.start_time)}s. Latency: {self.bot.latency * 1000:.2f}ms")

    @app_commands.command(name="ping", description="Check bot health and latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        
        latency = self.bot.latency * 1000
        
        
        db_status = "❌ Failed"
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                db_status = "✅ Connected"
                if db.db_type == "sqlite":
                    cursor.close()
        except Exception as e:
            db_status = f"❌ Error: {str(e)}"

        
        uptime = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        embed = discord.Embed(title="🏓 Pong!", color=config.COLOR_MAIN)
        embed.add_field(name="Latency", value=f"{latency:.2f} ms", inline=True)
        embed.add_field(name="Database", value=db_status, inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Health(bot))