import discord
from discord.ext import commands
from discord import app_commands
import database
import math
from datetime import datetime

import config

class ProfileView(discord.ui.View):
    def __init__(self, target_id=None):
        super().__init__(timeout=None)  
        self.target_id = target_id
    
    def get_target_id(self, interaction: discord.Interaction):
        
        if self.target_id:
            return self.target_id
        
        
        if interaction.message and interaction.message.embeds:
            footer = interaction.message.embeds[0].footer.text
            if footer and "ARCHIVE ID:" in footer:
                try:
                    archive_id = int(footer.split("ARCHIVE ID:")[-1].strip())
                    
                    
                    return interaction.user.id
                except:
                    pass
        
        
        return interaction.user.id

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.secondary, emoji="📊", custom_id="profile_leaderboard")
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            top_users = database.get_top_users(limit=10)
            if not top_users:
                return await interaction.response.send_message("No archival data recorded yet.", ephemeral=True)
            
            desc = "### 🏆 GLOBAL ELITE\n"
            for idx, (uid, stats) in enumerate(top_users, 1):
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**{idx}.**"
                desc += f"{medal} <@{uid}> ┃ `${stats['volume']:,.0f}`\n"
                
            embed = discord.Embed(title="Trading Archive", description=desc, color=0xF1C40F)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Retrieval error: {e}", ephemeral=True)

    @discord.ui.button(label="Achievements", style=discord.ButtonStyle.secondary, emoji="✨", custom_id="profile_achievements")
    async def achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            from services.achievement_service import achievement_service
            target_id = self.get_target_id(interaction)
            stats = database.get_gamified_stats(target_id)
            unlocked = set(stats.get('achievements', []))
            
            embed = discord.Embed(title="✨ Milestones", color=0x3498DB)
            embed.description = "Achievements unlocked through successful trading."
            
            items = []
            for key, info in achievement_service.achievements_config.items():
                status = "✅" if key in unlocked else "🔒"
                items.append(f"{status} **{info['name']}**\n*{info['desc']}*")
            
            for i in range(0, min(len(items), 8), 2):
                chunk = "\n\n".join(items[i:i+2])
                embed.add_field(name="\u200b", value=chunk, inline=True)
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @discord.ui.button(label="Ranks", style=discord.ButtonStyle.secondary, emoji="🏆", custom_id="profile_ranks")
    async def ranks(self, interaction: discord.Interaction, button: discord.ui.Button):
        ranks_desc = (
            "### 🏷️ TRADING PRESTIGE\n"
            "⚪ **Novice** ┃ `Lvl 0-1`\n"
            "🔵 **Apprentice** ┃ `Lvl 2-4`\n"
            "🟢 **Journeyman** ┃ `Lvl 5-9`\n"
            "🟡 **Expert** ┃ `Lvl 10-19`\n"
            "🟠 **Master** ┃ `Lvl 20-49`\n"
            "🟣 **Grandmaster** ┃ `Lvl 50+`\n\n"
            "*Complete high-volume deals to increase your rank.*"
        )
        embed = discord.Embed(title="Rank Information", description=ranks_desc, color=0xBDC3C7)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Referral", style=discord.ButtonStyle.primary, emoji="🎁", custom_id="profile_referral")
    async def referral(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_id = self.get_target_id(interaction)
        stats = database.get_gamified_stats(target_id)
        code = stats.get('referral_code', 'N/A')
        await interaction.response.send_message(
            f"💰 **PARTNER BONUSES**\n\nInvite others to the network and earn commission.\n\n"
            f"**Your Invite Code:** `{code}`\n"
            f"**Link:** https://discord.gg/rainymm", ephemeral=True
        )

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_rank_info(self, level):
        
        if level < 2: return "Novice Trader", 0xBDC3C7, "Apprentice"
        if level < 5: return "Apprentice", 0x3498DB, "Journeyman"
        if level < 10: return "Journeyman", 0x2ECC71, "Expert"
        if level < 20: return "Expert Trader", 0xF1C40F, "Master"
        if level < 50: return "Master", 0xE67E22, "Grandmaster"
        return "Grandmaster", 0x9B59B6, "Eldritch"

    def get_trust_name(self, reputation):
        if reputation < 0: return "💀 Untrusted"
        if reputation < 5: return "🤝 Reliable"
        if reputation < 20: return "💎 Trusted"
        if reputation < 50: return "👑 Elite"
        return "🌟 Immortal"

    def get_level(self, xp):
        if xp <= 0: return 0
        return math.floor(math.sqrt(xp / 20))

    def get_xp_for_level(self, level):
        return 20 * level ** 2

    @app_commands.command(name="profile", description="View your deluxe trading dashboard")
    @app_commands.describe(user="User to view (default: you)")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=False)
        target = user or interaction.user
        stats = database.get_gamified_stats(target.id)
        
        level = self.get_level(stats['xp'])
        rank_name, color, next_rank = self.get_rank_info(level)
        trust_status = self.get_trust_name(stats['reputation'])
        
        curr_lvl_xp = self.get_xp_for_level(level)
        next_lvl_xp = self.get_xp_for_level(level + 1)
        progress = stats['xp'] - curr_lvl_xp
        goal = next_lvl_xp - curr_lvl_xp
        percent = min(1.0, progress / goal) if goal > 0 else 1.0
        
        
        bar_len = 14
        filled = int(percent * bar_len)
        bar = "█" * filled + "▒" * (bar_len - filled)
        
        
        global_rank = max(1, 100 - (level * 2) - int(stats['volume']/5000))
        rank_suffix = "st" if global_rank == 1 else "nd" if global_rank == 2 else "rd" if global_rank == 3 else "th"

        embed = discord.Embed(color=color)
        embed.set_author(name=f"{target.display_name.upper()} • TRADING PROFILE", icon_url=target.display_avatar.url)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        
        
        owner_badge = " 👑 **OWNER**" if target.id in config.OWNER_IDS else ""
        
        embed.description = (
            f"**{rank_name.upper()}** ┃ `RANK #{global_rank}{rank_suffix}`{owner_badge}\n"
            f"`{bar}` **{int(percent*100)}%**\n"
            f"XP: `{stats['xp']}` / `{next_lvl_xp}`"
        )

        
        perf_box = (
            f"<:usd_symbo:1457992848686448661> **Volume:** `${stats['volume']:,.0f}`\n"
            f"🤝 **Deals:** `{stats['deals']}`\n"
            f"👑 **Status:** {trust_status.upper()}"
        )
        embed.add_field(name="📊 Performance", value=perf_box, inline=True)
        
        
        attr_box = (
            f"<a:16985fire:1457993180359295026> **Streak:** `{stats['streak']}` Days\n"
            f"✨ **Badges:** `{len(stats.get('badges', []))}` Earned\n"
            f"💠 **Prestige:** `{int(stats['xp'] / 5)}`"
        )
        embed.add_field(name="✨ Attributes", value=attr_box, inline=True)

        
        last_deal_str = "No recent records"
        if stats.get('last_deal_info'):
            ld = stats['last_deal_info']
            usd = ld.get('amount', 0)
            crypto = ld.get('crypto', 0)
            raw_curr = str(ld.get('currency', 'LTC')).upper()
            
            
            curr_map = {
                "USDT_POLYGON": "<:tether:1463096853498302669>",
                "USDT_BSC": "<:tether:1463096853498302669>",
                "LTC": "<:litecoin:1463098611029246013>",
                "BTC": "<:bitcoin:1463096676352000056>",
                "SOL": "<:solana:1463096910423523513>",
                "ETH": "<:ethereum:1463096760363782309>"
            }
            curr_display = curr_map.get(raw_curr, f"`{raw_curr}`")
            last_deal_str = f"`${usd:,.2f}` ┃ `{crypto}` {curr_display}"

        last_ach_str = "None earned"
        last_ach_key = stats.get('last_achievement')
        if not last_ach_key and stats.get('achievements'):
             last_ach_key = stats['achievements'][-1]
             with database.db.session() as conn:
                 conn.cursor().execute(f"UPDATE users SET last_achievement = {database.db.p} WHERE user_id = {database.db.p}", (last_ach_key, str(target.id)))
        
        if last_ach_key:
            from services.achievement_service import achievement_service
            ach = achievement_service.achievements_config.get(last_ach_key)
            if ach: last_ach_str = f"{ach['emoji']} **{ach['name']}**"

        activity_box = (
            f"**Latest Deal:** {last_deal_str}\n"
            f"**Latest Milestone:** {last_ach_str}\n"
            f"**Current Status:** `Active` ⚡"
        )
        embed.add_field(name="📑 Activity Logs", value=activity_box, inline=False)

        
        first_seen = stats.get('first_seen')
        if not first_seen:
             import time
             first_seen = time.time()
             with database.db.session() as conn:
                 conn.cursor().execute(f"UPDATE users SET first_seen = {database.db.p} WHERE user_id = {database.db.p}", (first_seen, str(target.id)))
        
        since = datetime.fromtimestamp(first_seen).strftime("%b %Y")
        embed.set_footer(text=f"MEMBER SINCE {since.upper()} • ARCHIVE ID: {target.id % 10000}")
        
        await interaction.followup.send(embed=embed, view=ProfileView(target.id))

    @app_commands.command(name="profile_sync", description="Force sync the profile command for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def profile_sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.tree.copy_from(guild=interaction.guild) 
            await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send("✅ Guild command tree synced. Please restart your Discord client if errors persist.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Sync error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Profile(bot))
