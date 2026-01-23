import config
import discord
from discord.ext import commands, tasks
from discord import app_commands
from services.alert_service import alert_service
from services.price_service import get_cached_price
import logging

logger = logging.getLogger("AlertsCog")

class Alerts(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_alerts.start()

    def cog_unload(self):
        self.check_alerts.cancel()

    @tasks.loop(minutes=2)
    async def check_alerts(self):
        
        alerts = alert_service.get_all_alerts()
        if not alerts:
            return

        
        price_cache = {}
        
        for alert in alerts:
            key = (alert['currency'], alert['fiat'])
            if key not in price_cache:
                current_price = await get_cached_price(alert['currency'], alert['fiat'])
                if isinstance(current_price, str): 
                    continue
                price_cache[key] = current_price
            
            current_val = price_cache[key]
            target = alert['target_price']
            condition = alert['condition']
            
            triggered = False
            if condition == "above" and current_val >= target:
                triggered = True
            elif condition == "below" and current_val <= target:
                triggered = True
                
            if triggered:
                await self.notify_user(alert, current_val)
                alert_service.delete_alert(alert['id'])

    async def notify_user(self, alert, current_price):
        
        try:
            user = await self.bot.fetch_user(int(alert['user_id']))
            if not user:
                return

            embed = discord.Embed(
                title="🔔 Price Alert Triggered!",
                description=(
                    f"Your alert for **{alert['currency'].upper()}** has been met.\n\n"
                    f"**Target Price:** {alert['target_price']:.2f} {alert['fiat'].upper()}\n"
                    f"**Current Price:** {current_price:.2f} {alert['fiat'].upper()}\n"
                    f"**Condition:** {alert['condition'].capitalize()}\n"
                ),
                color=0xf1c40f 
            )
            embed.set_footer(text="RainyDay MM | Stay ahead of the market")
            await user.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to notify user {alert['user_id']} for alert {alert['id']}: {e}")

    

    @app_commands.command(name="pricealert", description="Set a price alert for a cryptocurrency")
    @app_commands.describe(
        currency="The cryptocurrency symbol (e.g. LTC, ETH)",
        price="The target price threshold",
        condition="Whether to alert when price goes 'above' or 'below' the threshold",
        fiat="The fiat currency for the price (default: usd)"
    )
    @app_commands.choices(condition=[
        app_commands.Choice(name="Above", value="above"),
        app_commands.Choice(name="Below", value="below")
    ])
    async def pricealert_set(self, interaction: discord.Interaction, currency: str, price: float, condition: str = "above", fiat: str = "usd"):
        alert_service.add_alert(interaction.user.id, currency, price, condition, fiat)
        
        embed = discord.Embed(
            title="✅ Alert Set!",
            description=(
                f"I'll notify you when **{currency.upper()}** goes **{condition}** **{price:.2f} {fiat.upper()}**."
            ),
            color=config.COLOR_MAIN
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="alerts", description="List or manage your active price alerts")
    async def alerts_list(self, interaction: discord.Interaction):
        user_alerts = alert_service.get_user_alerts(interaction.user.id)
        
        if not user_alerts:
            await interaction.response.send_message("You have no active price alerts.", ephemeral=True)
            return

        embed = discord.Embed(title="🔔 Your Active Price Alerts", color=0x3498db)
        
        for a in user_alerts:
            field_val = f"**ID:** {a['id']}\n**Price:** {a['target_price']:.2f} {a['fiat'].upper()}\n**Condition:** {a['condition'].capitalize()}"
            embed.add_field(name=a['currency'].upper(), value=field_val, inline=True)
            
        embed.set_footer(text="To remove an alert, use /alertremove <id>")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="alertremove", description="Remove an active price alert by ID")
    async def alert_remove(self, interaction: discord.Interaction, alert_id: int):
        alert_service.delete_alert(alert_id, interaction.user.id)
        await interaction.response.send_message(f"✅ Alert #{alert_id} has been removed.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Alerts(bot))