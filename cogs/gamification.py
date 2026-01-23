import discord
from discord import app_commands
from discord.ext import commands
import database
from typing import Optional

class Gamification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.achievements_config = {
            "first_deal": {"name": "First Steps", "desc": "Complete your first deal", "emoji": "🌱"},
            "high_roller": {"name": "High Roller", "desc": "Complete a deal over $1000", "emoji": "💎"},
            "fast_trader": {"name": "Speed Demon", "desc": "Complete a deal in under 10 minutes", "emoji": "⚡"},
            "steady_hand": {"name": "Steady Hand", "desc": "Reach a 7-day streak", "emoji": "🤝"},
            "whaler": {"name": "Whaler", "desc": "Surpass $10,000 total volume", "emoji": "🐳"},
            "trusted_partner": {"name": "Trusted Partner", "desc": "Complete 10 successful deals", "emoji": "👑"}
        }
        self.badges_config = {
            "early_adopter": {"name": "Early Adopter", "emoji": "🚀", "rarity": "Legendary"},
            "streak_master": {"name": "Streak Master", "emoji": "🔥", "rarity": "Epic"},
            "certified_trader": {"name": "Certified", "emoji": "✅", "rarity": "Rare"}
        }

    def get_progress_bar(self, current, total, length=10):
        percent = min(1.0, current / total) if total > 0 else 0
        filled = int(length * percent)
        bar = "▰" * filled + "▱" * (length - filled)
        return f"{bar} {int(percent * 100)}%"

    @app_commands.command(name="streak", description="Check your current deal streak (Duolingo Style)")
    async def streak(self, interaction: discord.Interaction):
        stats = database.get_gamified_stats(interaction.user.id)
        current = stats['streak']
        highest = stats['highest_streak']
        
        
        emoji = "🔥" if current > 0 else "❄️"
        if current >= 7: emoji = "🎆"
        if current >= 30: emoji = "👑"
        
        embed = discord.Embed(
            title=f"{emoji} Your Streak Dashboard",
            description=f"Keep the fire burning! Complete a deal daily to grow your streak.",
            color=0xFFA500 if current > 0 else 0xCCCCCC
        )
        
        embed.add_field(name="Current Streak", value=f"### {current} Days", inline=True)
        embed.add_field(name="All-Time High", value=f"### {highest} Days", inline=True)
        
        if current == 0:
            embed.set_footer(text="Start your streak today by completing a deal!")
        else:
            embed.set_footer(text="Maintain your streak for bonuses and exclusive badges!")
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="achievements", description="View your progress and unlocked achievements")
    @app_commands.describe(user="User to check achievements for")
    async def achievements(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        stats = database.get_gamified_stats(target.id)
        
        unlocked = set(stats['achievements'])
        xp = stats['xp']
        level = int(xp / 100) + 1
        xp_in_level = xp % 100
        
        embed = discord.Embed(
            title=f"🏆 {target.display_name}'s Achievements",
            description=f"**Level {level}** | {xp} Total XP\n" + self.get_progress_bar(xp_in_level, 100),
            color=0x5865F2
        )
        
        
        displayed_items = []
        for key, info in self.achievements_config.items():
            status = "✅" if key in unlocked else "🔒"
            displayed_items.append(f"{status} **{info['name']}**\n*{info['desc']}*")
        
        
        for i in range(0, len(displayed_items), 3):
            chunk = "\n\n".join(displayed_items[i:i+3])
            embed.add_field(name="\u200b", value=chunk, inline=True)
            
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="badges", description="Show off your premium badges")
    async def badges(self, interaction: discord.Interaction):
        stats = database.get_gamified_stats(interaction.user.id)
        earned = stats['badges'] or []
        
        embed = discord.Embed(
            title="✨ Your Badge Collection",
            description="Premium badges earned through milestones and events.",
            color=0xFFD700
        )
        
        if not earned:
            embed.description += "\n\n*You haven't earned any badges yet. Keep trading to unlock them!*"
        else:
            badge_list = []
            for b_key in earned:
                if b_key in self.badges_config:
                    b = self.badges_config[b_key]
                    badge_list.append(f"{b['emoji']} **{b['name']}** ({b['rarity']})")
            
            embed.add_field(name="Unlocked", value="\n".join(badge_list) if badge_list else "None", inline=False)
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Gamification(bot))
