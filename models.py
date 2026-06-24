import sqlite3
import config

DB_NAME = "rps_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT 'ar',
            points INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            solo_games INTEGER DEFAULT 0,
            random_games INTEGER DEFAULT 0,
            friend_games INTEGER DEFAULT 0,
            channel_games INTEGER DEFAULT 0,
            tournament_wins INTEGER DEFAULT 0,
            bo3_wins INTEGER DEFAULT 0,
            bo3_losses INTEGER DEFAULT 0,
            login_streak INTEGER DEFAULT 0,
            days_since_register INTEGER DEFAULT 0,
            rock_used INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            theme TEXT DEFAULT 'theme_1',
            title TEXT,
            clan TEXT,
            shop_items TEXT DEFAULT '',
            achievements TEXT DEFAULT '',
            tasks_progress TEXT,
            move_history TEXT,
            active_boosters TEXT DEFAULT '{}',
            last_login TEXT,
            registered_date TEXT
        )
    """)

    # ... (باقي الجداول الأساسية: clans, tasks, shop, ratings, tournaments, achievements, friends, friend_requests, group_challenges, titles_shop, themes_shop, events, clan_wars)
    # هي نفسها بدون تغيير، سأختصرها هنا لتجنب تكرار الطول. في الملف الكامل ستجدها كاملة كما في النسخ السابقة.
    # ...
    # لكن تأكد من وجود جدول tournaments القديم (tournaments) وهذا لنغيره ليدعم bracket الجديد. سنضيف جدول tournaments جديد ونترك القديم إن أردت.
    # ولكن لسهولة التطوير، سنستخدم جدول tournaments الموجود مع حقل bracket كمصفوفة JSON.
    # لذا الجداول الأصلية تبقى كما هي.

    # جداول إدارة المباريات
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_matches (
            user_id INTEGER PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_games (
            game_id TEXT PRIMARY KEY,
            player1 INTEGER,
            player2 INTEGER,
            type TEXT,
            status TEXT,
            data TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جداول الميزات السابقة
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_claims (
            user_id INTEGER PRIMARY KEY,
            last_claimed_date TEXT,
            streak INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS battle_pass (
            user_id INTEGER PRIMARY KEY,
            season INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            premium INTEGER DEFAULT 0
        )
    """)

    # 🆕 جداول الإطارات والسوق
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_frames (
            user_id INTEGER PRIMARY KEY,
            owned_frames TEXT DEFAULT 'default',
            active_frame TEXT DEFAULT 'default'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            item_type TEXT,
            item_id TEXT,
            price_type TEXT,
            price INTEGER,
            status TEXT DEFAULT 'active'
        )
    """)

    # إدراج بيانات افتراضية (نفس السابق)
    # ... (tasks, achievements, shop, titles_shop, themes_shop)
    # اختصار

    conn.commit()
    conn.close()
