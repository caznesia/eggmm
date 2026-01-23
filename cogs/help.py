import config
import discord
from discord.ext import commands
from discord import app_commands
from services.localization_service import localization_service

class HelpView(discord.ui.View):
    def __init__(self, user, lang="en"):
        super().__init__(timeout=120)
        self.user = user
        self.lang = lang
        self.current_category = "home"

    def create_embed(self, category):
        color = 0x0099ff
        if category == "home":
            embed = discord.Embed(
                title="📚 RainyDay MM Help Center",
                description=(
                    "Welcome to **RainyDay MM**, the most secure and automated escrow bot on Discord.\n\n"
                    "Use the buttons below to navigate through command categories and FAQs."
                ),
                color=color
            )
            embed.add_field(name="🚀 Getting Started", value="Click **🔒 Escrow** to learn how to create your first deal.", inline=False)
            embed.set_footer(text="Join our support server for more help!")
            
        elif category == "escrow":
            embed = discord.Embed(title="🔒 Escrow & Deal Management", color=config.COLOR_MAIN)
            embed.add_field(name="/setup", value="Set up the bot in your server (Admin only).", inline=False)
            embed.add_field(name="Deal Creation", value="Deals are usually created via a 'Create Ticket' button in the escrow channel set by admins.", inline=False)
            embed.add_field(name="/add <user>", value="Add a user to your current deal ticket.", inline=False)
            embed.add_field(name="/remove <user>", value="Remove a user from your current deal ticket.", inline=False)
            embed.add_field(name="/close", value="Close a completed or inactive deal ticket.", inline=False)
            
        elif category == "tools":
            embed = discord.Embed(title="🔍 Blockchain Tools", color=0x9b59b6)
            embed.add_field(name="/balance <curr> <addr>", value="Check the balance and stats of any wallet address.", inline=False)
            embed.add_field(name="/tx <curr> <hash>", value="Check the status and details of any transaction.", inline=False)
            embed.add_field(name="/search <input>", value="**NEW!** Intelligent search that detects the chain automatically.", inline=False)
            
        elif category == "social":
            embed = discord.Embed(title="🎮 Gamification & Stats", color=0xf1c40f)
            embed.add_field(name="/stats [user]", value="View your own or another user's trading stats.", inline=False)
            embed.add_field(name="/leaderboard", value="See who the top traders are by volume.", inline=False)
            embed.add_field(name="/profile", value="**NEW!** View your level, XP, and earned achievement badges.", inline=False)

        elif category == "admin":
            embed = discord.Embed(title="🔧 Admin & System", color=0xe74c3c)
            embed.add_field(name="/force_release <id>", value="Force release funds (Staff only).", inline=False)
            embed.add_field(name="/force_cancel <id>", value="Force cancel and refund (Staff only).", inline=False)
            embed.add_field(name="/admin_rescan <id>", value="Trigger a manual on-chain rescan.", inline=False)
            embed.add_field(name="/sync", value="Sync database with active channels.", inline=False)

        elif category == "faq":
            embed = discord.Embed(title="❓ Frequently Asked Questions", color=0x1abc9c)
            embed.add_field(name="How long does it take?", value="Verification depends on the blockchain (LTC: ~2.5m, ETH: ~15s, SOL: <5s).", inline=False)
            embed.add_field(name="What are the fees?", value="Fees vary by currency and are clearly displayed during deal creation.", inline=False)
            embed.add_field(name="Auto-Close", value="Tickets auto-close after 1 hour of inactivity if unpaid.", inline=False)

        return embed

    @discord.ui.button(label="Home", style=discord.ButtonStyle.gray, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed("home"), view=self)

    @discord.ui.button(label="Escrow", style=discord.ButtonStyle.green, emoji="🔒")
    async def escrow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed("escrow"), view=self)

    @discord.ui.button(label="Tools", style=discord.ButtonStyle.blurple, emoji="🔍")
    async def tools_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed("tools"), view=self)

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.gray, emoji="🏆")
    async def social_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed("social"), view=self)

    @discord.ui.button(label="FAQ", style=discord.ButtonStyle.gray, emoji="❓")
    async def faq_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.create_embed("faq"), view=self)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Open the interactive help dashboard")
    async def help_slash(self, interaction: discord.Interaction):
        lang = interaction.locale.value[:2] if interaction.locale else "en"
        view = HelpView(interaction.user, lang)
        await interaction.response.send_message(embed=view.create_embed("home"), view=view, ephemeral=True)

    @commands.command(name="help")
    async def help_prefix(self, ctx):
        view = HelpView(ctx.author, "en")
        await ctx.send(embed=view.create_embed("home"), view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))