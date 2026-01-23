import discord
from services.db_manager import db
from services.notification_service import notification_service
import database

class AchievementService:
    def __init__(self):
        self.achievements_config = {
            "first_deal": {"name": "First Steps", "desc": "Complete your first deal", "emoji": "🌱", "check": lambda s: s['deals'] >= 1},
            "high_roller": {"name": "High Roller", "desc": "Complete a deal over $1000", "emoji": "💎", "check": lambda s: s['volume'] >= 1000},
            "steady_hand": {"name": "Steady Hand", "desc": "Reach a 7-day streak", "emoji": "🤝", "check": lambda s: s['streak'] >= 7},
            "whaler": {"name": "Whaler", "desc": "Surpass $10,000 total volume", "emoji": "🐳", "check": lambda s: s['volume'] >= 10000},
            "trusted_partner": {"name": "Trusted Partner", "desc": "Complete 10 successful deals", "emoji": "👑", "check": lambda s: s['deals'] >= 10},
            "explorer": {"name": "Chain Explorer", "desc": "Use the bot on 3 different chains", "emoji": "🧭", "check": lambda s: len(s.get('used_chains', [])) >= 3},
            "polyglot": {"name": "Polyglot", "desc": "Use the bot in a non-English language", "emoji": "🌍", "check": lambda s: s.get('languages_used', 1) > 1},
            "fast_trader": {"name": "Speed Demon", "desc": "Complete a deal in 10 minutes", "emoji": "⚡", "check": lambda s: s.get('fast_deals', 0) >= 1},
            "streak_master": {"name": "Streak Master", "desc": "Reach a 30-day streak", "emoji": "🔥", "check": lambda s: s['streak'] >= 30}
        }

    async def check_achievements(self, user_id, user_obj):
        
        if not user_obj:
            return

        stats = database.get_gamified_stats(user_id)
        current_unlocked = set(stats.get('achievements', []))
        new_unlocked = list(current_unlocked)
        earned_this_time = []

        for key, info in self.achievements_config.items():
            if key not in current_unlocked:
                if info['check'](stats):
                    new_unlocked.append(key)
                    earned_this_time.append(info)

        if earned_this_time:
            database.update_achievements(user_id, new_unlocked)
            for ach in earned_this_time:
                await self.notify_achievement(user_obj, ach)

    async def notify_achievement(self, user_obj, achievement_info):
        
        embed = discord.Embed(
            title="🏆 ACHIEVEMENT UNLOCKED!",
            description=f"### {achievement_info['emoji']} {achievement_info['name']}\n*{achievement_info['desc']}*",
            color=0xFFD700 
        )
        embed.set_footer(text="RainyDay MM | Keep trading to level up!")
        
        try:
            await user_obj.send(embed=embed)
        except:
            
            
            pass

achievement_service = AchievementService()
