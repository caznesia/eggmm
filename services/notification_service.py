
import discord
import logging
import config
import os

logger = logging.getLogger("NotificationService")

class NotificationService:
    def __init__(self):
        
        self.public_log_channel_id = config.PUBLIC_LOG_CHANNEL_ID

    async def send_dm(self, user: discord.User, content: str = None, embed: discord.Embed = None):
        
        if not user:
            return False
        
        try:
            await user.send(content=content, embed=embed)
            return True
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to {user.id} (DMs closed or blocked).")
            return False
        except Exception as e:
            logger.error(f"Failed to send DM to {user.id}: {e}")
            return False

    async def post_public_log(self, guild: discord.Guild, embed: discord.Embed):
        
        if not self.public_log_channel_id:
            return

        try:
            channel = guild.get_channel(int(self.public_log_channel_id))
            if channel:
                await channel.send(embed=embed)
            else:
                logger.warning(f"Public log channel {self.public_log_channel_id} not found.")
        except Exception as e:
            logger.error(f"Failed to post public log: {e}")

notification_service = NotificationService()
