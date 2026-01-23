
import discord
from discord import app_commands
from discord.ext import commands
from services.blacklist_service import blacklist_service
import config

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        
        if blacklist_service.is_blacklisted(interaction.user.id):
            embed = discord.Embed(title="You are blacklisted from our services!", description="Appeal this in <#1428193038588579880>", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @app_commands.command(name="blacklist", description="Manage the blacklist")
    @app_commands.describe(
        action="Action to perform (add/remove/check)",
        user="The user to target",
        reason="Reason for blacklisting (required for add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="Check", value="check")
    ])
    async def blacklist(self, interaction: discord.Interaction, action: app_commands.Choice[str], user: discord.User, reason: str = None):
        
        if interaction.user.id not in config.OWNER_IDS:
            
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        if action.value == "add":
            if not reason:
                await interaction.response.send_message("❌ Please provide a reason for blacklisting.", ephemeral=True)
                return
            
            success = blacklist_service.add_user(user.id, reason, interaction.user.id)
            if success:
                await interaction.response.send_message(f"✅ **{user.name}** (`{user.id}`) has been blacklisted.\nReason: {reason}")
            else:
                await interaction.response.send_message("❌ Failed to add user to blacklist. Check logs.", ephemeral=True)

        elif action.value == "remove":
            success = blacklist_service.remove_user(user.id)
            if success:
                await interaction.response.send_message(f"✅ **{user.name}** (`{user.id}`) has been removed from the blacklist.")
            else:
                await interaction.response.send_message("❌ Failed to remove user from blacklist.", ephemeral=True)

        elif action.value == "check":
            info = blacklist_service.get_info(user.id)
            if info:
                embed = discord.Embed(title="⛔ Blacklisted User", color=discord.Color.red())
                embed.add_field(name="User", value=f"{user.name} (`{user.id}`)", inline=False)
                embed.add_field(name="Reason", value=info['reason'], inline=False)
                embed.add_field(name="Added By", value=f"<@{info['added_by']}>", inline=False)
                from datetime import datetime
                embed.set_footer(text=f"Date: {datetime.fromtimestamp(info['added_at'])}")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"✅ **{user.name}** is not blacklisted.")

async def setup(bot):
    await bot.add_cog(Blacklist(bot))
