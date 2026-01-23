import logging
import time
from services.db_manager import db

logger = logging.getLogger("BlacklistService")

class BlacklistService:
    def __init__(self):
        self._cache = set()
        self._last_refresh = 0
        self.CACHE_TTL = 300  

    def _load_cache(self):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT user_id FROM blacklist")
                    rows = cursor.fetchall()
                    self._cache = {str(row[0]) for row in rows}
                    self._last_refresh = time.time()
                    logger.debug(f"Blacklist cache refreshed. {len(self._cache)} users found.")
                finally:
                    cursor.close()
        except Exception as e:
            logger.error(f"Failed to load blacklist cache: {e}")

    def is_blacklisted(self, user_id):
        
        
        return str(user_id) in self._cache

    def add_user(self, user_id, reason, admin_id):
        try:
            with db.session() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"""
                        INSERT INTO blacklist (user_id, reason, added_at, added_by)
                        VALUES ({db.p}, {db.p}, {db.p}, {db.p})
                        ON CONFLICT (user_id) DO UPDATE SET
                            reason = EXCLUDED.reason,
                            added_at = EXCLUDED.added_at,
                            added_by = EXCLUDED.added_by
                    """, (str(user_id), reason, time.time(), str(admin_id)))
                finally:
                    cursor.close()
            
            
            self._cache.add(str(user_id))
            logger.info(f"User {user_id} added to blacklist by {admin_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist user {user_id}: {e}")
            return False

    def remove_user(self, user_id):
        try:
            with db.session() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"DELETE FROM blacklist WHERE user_id = {db.p}", (str(user_id),))
                finally:
                    cursor.close()
            
            if str(user_id) in self._cache:
                self._cache.remove(str(user_id))
            
            logger.info(f"User {user_id} removed from blacklist.")
            return True
        except Exception as e:
            logger.error(f"Failed to unblacklist user {user_id}: {e}")
            return False

    def get_info(self, user_id):
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"SELECT user_id, reason, added_at, added_by FROM blacklist WHERE user_id = {db.p}", (str(user_id),))
                    row = cursor.fetchone()
                    if row:
                        return {
                            "user_id": row[0],
                            "reason": row[1],
                            "added_at": row[2],
                            "added_by": row[3]
                        }
                finally:
                    cursor.close()
            return None
        except Exception as e:
            logger.error(f"Failed to get blacklist info for {user_id}: {e}")
            return None

blacklist_service = BlacklistService()
