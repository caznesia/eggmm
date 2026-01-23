
from services.db_manager import db
import string
import random
import logging

logger = logging.getLogger(__name__)

class ReferralService:
    def get_referral_code(self, user_id):
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    
                    cursor.execute(f"SELECT referral_code FROM users WHERE user_id = {db.p}", (str(user_id),))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0]
                    
                     
                    new_code = self._generate_unique_code()
                    import time
                    timestamp = time.time()
                    
                    cursor.execute(f"""
                        INSERT INTO users (user_id, referral_code, first_seen) 
                        VALUES ({db.p}, {db.p}, {db.p})
                        ON CONFLICT(user_id) DO UPDATE SET 
                            referral_code = EXCLUDED.referral_code,
                            first_seen = COALESCE(users.first_seen, EXCLUDED.first_seen)
                    """, (str(user_id), new_code, timestamp))
                    return new_code
                finally:
                    cursor.close()
        except Exception as e:
            raise e

    def _generate_unique_code(self):
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=6))

    def set_referrer(self, user_id, referrer_code):
        
        referrer_code = referrer_code.upper()
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    
                    cursor.execute(f"SELECT user_id FROM users WHERE referral_code = {db.p}", (referrer_code,))
                    referrer = cursor.fetchone()
                    if not referrer:
                        return False, "Invalid referral code."
                    
                    referrer_id = referrer[0]
                    if str(referrer_id) == str(user_id):
                        return False, "You cannot refer yourself."

                    
                    cursor.execute(f"SELECT referrer_id FROM users WHERE user_id = {db.p}", (str(user_id),))
                    current = cursor.fetchone()
                    if current and current[0]:
                        return False, "You already have a referrer."

                    
                    cursor.execute(f"""
                        INSERT INTO users (user_id, referrer_id) 
                        VALUES ({db.p}, {db.p})
                        ON CONFLICT(user_id) DO UPDATE SET referrer_id = EXCLUDED.referrer_id
                    """, (str(user_id), referrer_id))
                    return True, "Referrer set successfully!"
                finally:
                    cursor.close()
        except Exception as e:
            raise e

    def add_volume(self, user_id, amount_usd):
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    
                    cursor.execute(f"SELECT referrer_id FROM users WHERE user_id = {db.p}", (str(user_id),))
                    row = cursor.fetchone()
                    if row and row[0]:
                        referrer_id = row[0]
                        
                        pass 
                    if row and row[0]:
                        referrer_id = row[0]
                        
                        pass 
                finally:
                    cursor.close()
        except Exception:
            pass

    def is_referral_enabled(self):
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT value FROM config WHERE key = {db.p}", ('referral_enabled',))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0].lower() == 'true'
                return True 
        except Exception as e:

            logger.error(f"Error checking referral status: {e}")
            return True

    def set_referral_status(self, enabled: bool):
        
        try:
            with db.session() as conn:
                cursor = conn.cursor()
                val = 'true' if enabled else 'false'
                cursor.execute(f"""
                    INSERT INTO config (key, value) VALUES ({db.p}, {db.p})
                    ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value
                """, ('referral_enabled', val))
                conn.commit()
                cursor.close()
            return True

        except Exception as e:
            logger.error(f"Error setting referral status: {e}")
            return False

referral_service = ReferralService()
