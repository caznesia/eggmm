
import json
import os
import sys
import psycopg2
from psycopg2.extras import Json
from typing import Dict, Any


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_manager import db

def load_json(filename):
    if not os.path.exists(filename):
        print(f"File {filename} not found, skipping.")
        return {}
    with open(filename, 'r') as f:
        return json.load(f)

def migrate_deals():
    data = load_json("data.json")
    count = 0
    with db.session() as conn:
        cursor = conn.cursor()
        for deal_id, info in data.items():
            
            cursor.execute("SELECT deal_id FROM deals WHERE deal_id = %s", (deal_id,))
            if cursor.fetchone():
                continue

            
            channel_id = str(info.get("channel_id"))
            buyer = info.get("buyer")
            seller = info.get("seller")
            amount = info.get("amount", 0.0)
            currency = info.get("currency")
            created_at = info.get("start_time")
            
            
            
            status = "completed" if info.get("amount_final_embed_sent") else "active"

            
            schema_keys = {"deal_id", "channel_id", "buyer", "seller", "amount", "currency", "start_time"}
            other_data = {k: v for k, v in info.items() if k not in schema_keys}
            
            cursor.execute("""
                INSERT INTO deals (deal_id, channel_id, buyer_id, seller_id, amount, currency, status, created_at, other_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deal_id, 
                channel_id, 
                buyer, 
                seller, 
                amount, 
                currency, 
                status, 
                created_at, 
                Json(other_data)
            ))
            count += 1
    print(f"Migrated {count} deals.")

def migrate_users():
    data = load_json("users.json")
    count = 0
    with db.session() as conn:
        cursor = conn.cursor()
        for user_id, stats in data.items():
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if cursor.fetchone():
                continue

            deals = stats.get("deals", 0)
            volume = stats.get("volume", 0.0)
            
            cursor.execute("""
                INSERT INTO users (user_id, deals_completed, volume_usd)
                VALUES (%s, %s, %s)
            """, (user_id, deals, volume))
            count += 1
    print(f"Migrated {count} users.")

def migrate_counter():
    if not os.path.exists("counter.json"):
        print("counter.json not found.")
        return

    try:
        with open("counter.json", "r") as f:
            val = json.load(f)
            
        with db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO config (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, ("deal_counter", str(val)))
        print(f"Migrated counter: {val}")
    except Exception as e:
        print(f"Error migrating counter: {e}")

if __name__ == "__main__":
    print("Starting migration (PostgreSQL)...")
    try:
        migrate_deals()
        migrate_users()
        migrate_counter()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
