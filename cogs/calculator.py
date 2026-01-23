
import discord
from discord import app_commands
from discord.ext import commands
from services.price_service import get_cached_price
import datetime

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currency_map = {
            'ltc': 'ltc', 'litecoin': 'ltc',
            'eth': 'ethereum', 'ethereum': 'ethereum',
            'sol': 'solana', 'solana': 'solana',
            'usdt': 'usdt_bep20', 'tether': 'usdt_bep20', 'usdtpol': 'usdt_polygon', 'usdtbep': 'usdt_bep20'
        }
        self.blacklist = ["nigga", "nigger", "faggot", "tranny", "retard"] 

    def _normalize_currency(self, currency: str):
        c = currency.lower().replace(" ", "").replace("_", "")
        return self.currency_map.get(c, c)

    def _is_safe(self, text: str):
        t = text.lower()
        return not any(word in t for word in self.blacklist)

    @app_commands.command(name="price", description="Check current price of a cryptocurrency")
    @app_commands.describe(currency="The cryptocurrency to check (e.g., ltc, eth, sol)")
    async def price(self, interaction: discord.Interaction, currency: str):
        if not self._is_safe(currency):
            await interaction.response.send_message("❌ Invalid currency name.", ephemeral=True)
            return

        curr = self._normalize_currency(currency)
        await interaction.response.defer()
        
        price = await get_cached_price(curr)

        if price > 0:
            embed = discord.Embed(title=f"💰 Price of {curr.upper()}", color=0x00ff00)
            embed.add_field(name="USD Price", value=f"${price:,.2f}", inline=False)
            embed.set_footer(text=f"Updated: {datetime.datetime.now().strftime('%H:%M:%S')}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Could not fetch price for `{currency}`. Supported: ltc, eth, sol, usdt.", ephemeral=True)

    @app_commands.command(name="calc", description="Convert between USD and Crypto")
    @app_commands.describe(
        amount="Amount to convert",
        currency="Cryptocurrency (e.g., ltc, eth)",
        mode="Conversion mode (crypto_to_usd or usd_to_crypto)"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Crypto -> USD", value="to_usd"),
        app_commands.Choice(name="USD -> Crypto", value="to_crypto")
    ])
    async def calc(self, interaction: discord.Interaction, amount: float, currency: str, mode: app_commands.Choice[str] = "to_usd"):
        if not self._is_safe(currency):
            await interaction.response.send_message("❌ Invalid currency name.", ephemeral=True)
            return

        curr = self._normalize_currency(currency)
        await interaction.response.defer()
        price = await get_cached_price(curr)
        
        if price <= 0:
            await interaction.followup.send(f"❌ Could not fetch price for `{currency}`.", ephemeral=True)
            return

        embed = discord.Embed(color=0x3498db)
        
        
        mode_val = mode.value if hasattr(mode, 'value') else mode

        if mode_val == "to_usd":
            
            result = amount * price
            embed.title = "🔄 Crypto to USD Conversion"
            embed.add_field(name=f"Amount ({curr.upper()})", value=f"{amount:,.8f}", inline=True)
            embed.add_field(name="Rate", value=f"${price:,.2f}", inline=True)
            embed.add_field(name="Result (USD)", value=f"**${result:,.2f}**", inline=False)
        else:
            
            result = amount / price
            embed.title = "🔄 USD to Crypto Conversion"
            embed.add_field(name="Amount (USD)", value=f"${amount:,.2f}", inline=True)
            embed.add_field(name="Rate", value=f"${price:,.2f}", inline=True)
            embed.add_field(name=f"Result ({curr.upper()})", value=f"**{result:,.8f} {curr.upper()}**", inline=False)
            
        embed.set_footer(text="Rates are approximate.")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Calculator(bot))
