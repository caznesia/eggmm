try:
    import psycopg2
    import psycopg2.pool
except ImportError:
    psycopg2 = None
import sqlite3
import json
import logging
import os
import config
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBManager")

class DBManager:
    def __init__(self):
        
        self.database_url = os.getenv("DATABASE_URL")
        
        self.db_type = config.DB_TYPE
        self._pool = None

        
        if self.db_type == "sqlite":
            self.database_url = config.DB_PATH
            logger.info(f"Using SQLite database: {self.database_url}")
        else:
            if not self.database_url or "postgres.xxx" in self.database_url:
                logger.warning("DATABASE_URL is missing or placeholder. Falling back to SQLite.")
                self.db_type = "sqlite"
                self.database_url = config.DB_PATH
            else:
                self._init_pool()
        
        self._initialize_tables()

    def _init_pool(self):
        try:
            
            self._pool = psycopg2.pool.ThreadedConnectionPool(1, 20, self.database_url)
            logger.info("PostgreSQL connection pool initialized (Max 20).")
        except Exception as e:
            logger.error(f"Failed to initialize pool: {e}")
            self.db_type = "sqlite" 

    @property
    def p(self):
        return "?" if self.db_type == "sqlite" else "%s"

    def get_connection(self):
        if self.db_type == "postgres" and self._pool:
            try:
                return self._pool.getconn()
            except Exception as e:
                logger.error(f"Pool error: {e}. Attempting direct connection.")
                return psycopg2.connect(self.database_url)
        else:
            
            
            conn = sqlite3.connect(self.database_url, check_same_thread=False, timeout=30.0)
            
            
            conn.execute("PRAGMA journal_mode=WAL;")
            
            conn.execute("PRAGMA foreign_keys=ON;")
            
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            return conn

    def _initialize_tables(self):
        try:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                
                if self.db_type == "postgres":
                    
                    
                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS deals (
                            deal_id TEXT PRIMARY KEY,
                            channel_id TEXT UNIQUE,
                            buyer_id TEXT,
                            seller_id TEXT,
                            amount REAL,
                            currency TEXT,
                            status TEXT,
                            created_at REAL,
                            other_data JSONB
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id TEXT PRIMARY KEY,
                            deals_completed INTEGER DEFAULT 0,
                            volume_usd REAL DEFAULT 0.0,
                            reputation_score INTEGER DEFAULT 0,
                            referral_code TEXT,
                            referrer_id TEXT,
                            first_seen REAL,
                            last_active REAL,
                            current_streak INTEGER DEFAULT 0,
                            highest_streak INTEGER DEFAULT 0,
                            last_deal_date TEXT,
                            achievements TEXT DEFAULT '[]',
                            badges TEXT DEFAULT '[]',
                            xp INTEGER DEFAULT 0
                        )
                    """)

                    
                    cols_to_add = [
                        ('current_streak', 'INTEGER DEFAULT 0'),
                        ('highest_streak', 'INTEGER DEFAULT 0'),
                        ('last_deal_date', 'TEXT'),
                        ('achievements', "TEXT DEFAULT '[]'"),
                        ('badges', "TEXT DEFAULT '[]'"),
                        ('xp', 'INTEGER DEFAULT 0'),
                        ('used_chains', "TEXT DEFAULT '[]'"),
                        ('languages_used', 'INTEGER DEFAULT 1'),
                        ('fast_deals', 'INTEGER DEFAULT 0'),
                        ('last_deal_info', 'TEXT'),
                        ('last_achievement', 'TEXT')
                    ]
                    for col_name, col_def in cols_to_add:
                        try:
                            cursor.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
                        except: pass

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS config (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                    """) 

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS blacklist (
                            user_id TEXT PRIMARY KEY,
                            reason TEXT,
                            added_at REAL,
                            added_by TEXT
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS audit_logs (
                            id SERIAL PRIMARY KEY,
                            action TEXT,
                            user_id TEXT,
                            target_id TEXT,
                            details TEXT,
                            timestamp REAL
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS price_alerts (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT,
                            currency TEXT,
                            target_price REAL,
                            condition TEXT,
                            fiat TEXT DEFAULT 'usd',
                            created_at REAL
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS transaction_tracking (
                            id SERIAL PRIMARY KEY,
                            user_id TEXT,
                            txid TEXT,
                            currency TEXT,
                            target_confs INTEGER DEFAULT 1,
                            status TEXT DEFAULT 'pending',
                            created_at REAL
                        )
                    """)
                    
                else:
                    
                    
                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS deals (
                            deal_id TEXT PRIMARY KEY,
                            channel_id TEXT UNIQUE,
                            buyer_id TEXT,
                            seller_id TEXT,
                            amount REAL,
                            currency TEXT,
                            status TEXT,
                            created_at REAL,
                            other_data TEXT
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id TEXT PRIMARY KEY,
                            deals_completed INTEGER DEFAULT 0,
                            volume_usd REAL DEFAULT 0.0,
                            reputation_score INTEGER DEFAULT 0,
                            referral_code TEXT,
                            referrer_id TEXT,
                            first_seen REAL,
                            last_active REAL,
                            current_streak INTEGER DEFAULT 0,
                            highest_streak INTEGER DEFAULT 0,
                            last_deal_date TEXT,
                            achievements TEXT DEFAULT '[]',
                            badges TEXT DEFAULT '[]',
                            xp INTEGER DEFAULT 0
                        )
                    """)

                    
                    cols_to_add = [
                        ('current_streak', 'INTEGER DEFAULT 0'),
                        ('highest_streak', 'INTEGER DEFAULT 0'),
                        ('last_deal_date', 'TEXT'),
                        ('achievements', "TEXT DEFAULT '[]'"),
                        ('badges', "TEXT DEFAULT '[]'"),
                        ('xp', 'INTEGER DEFAULT 0'),
                        ('used_chains', "TEXT DEFAULT '[]'"),
                        ('languages_used', 'INTEGER DEFAULT 1'),
                        ('fast_deals', 'INTEGER DEFAULT 0'),
                        ('last_deal_info', 'TEXT'),
                        ('last_achievement', 'TEXT')
                    ]
                    for col_name, col_def in cols_to_add:
                        try:
                            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                        except: pass

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS config (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                    """) 

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS blacklist (
                            user_id TEXT PRIMARY KEY,
                            reason TEXT,
                            added_at REAL,
                            added_by TEXT
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS audit_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            action TEXT,
                            user_id TEXT,
                            target_id TEXT,
                            details TEXT,
                            timestamp REAL
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS price_alerts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT,
                            currency TEXT,
                            target_price REAL,
                            condition TEXT,
                            fiat TEXT DEFAULT 'usd',
                            created_at REAL
                        )
                    """)

                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS transaction_tracking (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT,
                            txid TEXT,
                            currency TEXT,
                            target_confs INTEGER DEFAULT 1,
                            status TEXT DEFAULT 'pending',
                            created_at REAL
                        )
                    """)

                    
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_channel ON deals(channel_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_volume ON users(volume_usd)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_deals ON users(deals_completed)")

                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Init error: {e}")
                raise
            finally:
                if self.db_type == "postgres" and self._pool:
                    self._pool.putconn(conn)
                else:
                    conn.close()
            logger.info(f"Database tables initialized ({self.db_type}).")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    
    @contextmanager
    def session(self):
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self.db_type == "postgres" and self._pool:
                self._pool.putconn(conn)
            else:
                conn.close()

db = DBManager()
