import time
from services.db_manager import db

class TransactionTrackingService:
    def add_tracking(self, user_id, txid, currency, target_confs=1):
        
        with db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO transaction_tracking (user_id, txid, currency, target_confs, created_at)
                VALUES ({db.p}, {db.p}, {db.p}, {db.p}, {db.p})
            """, (str(user_id), txid, currency.lower(), int(target_confs), time.time()))

    def get_user_tracking(self, user_id):
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, txid, currency, target_confs, status FROM transaction_tracking WHERE user_id = {db.p}", (str(user_id),))
            rows = cursor.fetchall()
            if db.db_type == "sqlite":
                cursor.close()
            
            tracking_list = []
            for r in rows:
                tracking_list.append({
                    "id": r[0],
                    "txid": r[1],
                    "currency": r[2],
                    "target_confs": r[3],
                    "status": r[4]
                })
            return tracking_list

    def get_all_pending_tracking(self):
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, user_id, txid, currency, target_confs FROM transaction_tracking WHERE status = {db.p}", ('pending',))
            rows = cursor.fetchall()
            if db.db_type == "sqlite":
                cursor.close()
            
            tracking_list = []
            for r in rows:
                tracking_list.append({
                    "id": r[0],
                    "user_id": r[1],
                    "txid": r[2],
                    "currency": r[3],
                    "target_confs": r[4]
                })
            return tracking_list

    def update_tracking_status(self, tracking_id, status):
        
        with db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE transaction_tracking SET status = {db.p} WHERE id = {db.p}", (status, tracking_id))

    def delete_tracking(self, tracking_id, user_id=None):
        
        with db.session() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(f"DELETE FROM transaction_tracking WHERE id = {db.p} AND user_id = {db.p}", (tracking_id, str(user_id)))
            else:
                cursor.execute(f"DELETE FROM transaction_tracking WHERE id = {db.p}", (tracking_id,))

tracking_service = TransactionTrackingService()
