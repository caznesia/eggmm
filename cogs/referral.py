import discord
from discord import app_commands
from discord.ext import commands
from services.referral_service import referral_service

class Referral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    referral_group = app_commands.Group(name="referral", description="Referral system commands")

    @referral_group.command(name="code", description="Get your unique referral code")
    async def referral_code(self, interaction: discord.Interaction):
        if not referral_service.is_referral_enabled():
            return await interaction.response.send_message("❌ The referral system is currently disabled.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        try:
            code = referral_service.get_referral_code(interaction.user.id)
            await interaction.followup.send(f"🔗 Your Referral Code: `{code}`\nShare this with friends!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @referral_group.command(name="enable", description="Enable the referral system (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def referral_enable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        referral_service.set_referral_status(True)
        await interaction.followup.send("✅ Referral system has been **ENABLED**.", ephemeral=True)

    @referral_group.command(name="disable", description="Disable the referral system (Admin Only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def referral_disable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        referral_service.set_referral_status(False)
        await interaction.followup.send("🚫 Referral system has been **DISABLED**.", ephemeral=True)

    @app_commands.command(name="redeem", description="Redeem a referral code")
    async def redeem(self, interaction: discord.Interaction, code: str):
        if not referral_service.is_referral_enabled():
            return await interaction.response.send_message("❌ The referral system is currently disabled.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        try:
            success, msg = referral_service.set_referrer(interaction.user.id, code)
            if success:
                await interaction.followup.send(f"✅ {msg}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {msg}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Referral(bot))
