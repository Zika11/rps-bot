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

    c.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            leader_id INTEGER,
            points INTEGER DEFAULT 0,
            invite_link TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            points_reward INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS shop (
            item_id TEXT PRIMARY KEY,
            name TEXT,
            price INTEGER,
            type TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER PRIMARY KEY,
            rating INTEGER DEFAULT 1000
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            tour_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            status TEXT DEFAULT 'open',
            current_round INTEGER DEFAULT 0,
            players TEXT,
            bracket TEXT,
            winner_id INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            ach_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            icon TEXT,
            condition_field TEXT,
            condition_value INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            user_id INTEGER,
            friend_id INTEGER,
            PRIMARY KEY (user_id, friend_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT DEFAULT 'pending',
            PRIMARY KEY (sender_id, receiver_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS group_challenges (
            challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            creator_id INTEGER,
            opponent_id INTEGER,
            status TEXT DEFAULT 'open'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS titles_shop (
            title_id TEXT PRIMARY KEY,
            name TEXT,
            price INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS themes_shop (
            theme_id TEXT PRIMARY KEY,
            name TEXT,
            price INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            reward TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clan_wars (
            war_id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan1 TEXT,
            clan2 TEXT,
            points1 INTEGER DEFAULT 0,
            points2 INTEGER DEFAULT 0,
            start_time TEXT,
            end_time TEXT,
            active INTEGER DEFAULT 1
        )
    """)

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS clan_treasury (
            clan_name TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            upgrades TEXT DEFAULT '{}'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clan_war_season (
            season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS clan_war_scores (
            clan_name TEXT,
            season_id INTEGER,
            region TEXT,
            score INTEGER DEFAULT 0,
            PRIMARY KEY (clan_name, season_id, region)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS spectator_rooms (
            room_id TEXT PRIMARY KEY,
            player1 INTEGER,
            player2 INTEGER,
            chat_id INTEGER,
            status TEXT DEFAULT 'waiting',
            moves TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS season_info (
            season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS season_rankings (
            user_id INTEGER,
            season_id INTEGER,
            rating INTEGER,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, season_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS world_boss (
            boss_id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT DEFAULT 'تنين الظلام',
            current_hp INTEGER DEFAULT 1000,
            max_hp INTEGER DEFAULT 1000,
            status TEXT DEFAULT 'active',
            spawned_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS boss_damage (
            user_id INTEGER,
            boss_id INTEGER,
            damage INTEGER DEFAULT 0,
            attacks INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, boss_id)
        )
    """)

    # قدرات اللاعبين
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_abilities (
            user_id INTEGER PRIMARY KEY,
            shield INTEGER DEFAULT 1,
            double_points INTEGER DEFAULT 1,
            reverse INTEGER DEFAULT 1,
            shield_last_used TEXT,
            double_points_last_used TEXT,
            reverse_last_used TEXT
        )
    """)

    # معارك جماعية
    c.execute("""
        CREATE TABLE IF NOT EXISTS mass_battle (
            battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            start_time TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mass_battle_picks (
            battle_id INTEGER,
            user_id INTEGER,
            move TEXT,
            PRIMARY KEY (battle_id, user_id)
        )
    """)

    # Team Battles
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_battles (
            battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            team1_name TEXT,
            team2_name TEXT,
            status TEXT DEFAULT 'active',
            round INTEGER DEFAULT 1,
            winner_team TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_battle_players (
            battle_id INTEGER,
            user_id INTEGER,
            team TEXT,
            PRIMARY KEY (battle_id, user_id)
        )
    """)

    # جلسات القناة للتصويت الآلي
    c.execute("""
        CREATE TABLE IF NOT EXISTS channel_loop_state (
            chat_id INTEGER PRIMARY KEY,
            active INTEGER DEFAULT 1,
            interval_sec INTEGER DEFAULT 60,
            ttl_sec INTEGER DEFAULT 30,
            round_id INTEGER DEFAULT 0,
            players_choice TEXT DEFAULT '{}',
            predictions TEXT DEFAULT '{}',
            round_start_time TEXT
        )
    """)

    # متابعة الـ Streak لكل لاعب في كل قناة
    c.execute("""
        CREATE TABLE IF NOT EXISTS channel_user_streaks (
            chat_id INTEGER,
            user_id INTEGER,
            streak INTEGER DEFAULT 0,
            last_vote_time TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    # نقاط القناة (لتجميع نقاط التصويت)
    c.execute("""
        CREATE TABLE IF NOT EXISTS channel_user_points (
            chat_id INTEGER,
            user_id INTEGER,
            points INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    # إدراج بيانات افتراضية
    c.execute("SELECT COUNT(*) FROM tasks")
    if c.fetchone()[0] == 0:
        tasks = [
            ("task_1", "العب 5 مباريات فردية", 30),
            ("task_2", "اربح 3 مباريات عشوائية", 20),
            ("task_3", "انضم لعشيرة", 10),
            ("task_4", "اربح بطولة", 50),
            ("task_5", "اجمع 10 انتصارات", 40)
        ]
        c.executemany("INSERT INTO tasks VALUES (?,?,?)", tasks)

    c.execute("SELECT COUNT(*) FROM achievements")
    if c.fetchone()[0] == 0:
        achievements = [
            ("ach_wins_10", "مقاتل", "احصل على 10 انتصارات", "⚔️", "wins", 10),
            ("ach_wins_50", "بطل", "احصل على 50 انتصار", "🏅", "wins", 50),
            ("ach_streak_5", "ملتزم", "حقق 5 انتصارات متتالية", "🔥", "win_streak", 5),
            ("ach_friend_1", "اجتماعي", "أضف صديقاً", "🤝", "friend_games", 1),
            ("ach_clan_join", "عشائري", "انضم لعشيرة", "🏘️", "clan_joined", 1),
            ("ach_tournament_win", "المتوج", "اربح بطولة", "👑", "tournament_win", 1),
            ("ach_rock_100", "صخري", "استخدم الصخرة 100 مرة", "🪨", "rock_used", 100),
            ("ach_login_7", "مدمن", "سجل دخول 7 أيام متتالية", "📅", "login_streak", 7),
            ("ach_rating_1200", "خبير", "وصل تصنيفك إلى 1200", "📈", "rated", 1)
        ]
        c.executemany("INSERT INTO achievements VALUES (?,?,?,?,?,?)", achievements)

    c.execute("SELECT COUNT(*) FROM shop")
    if c.fetchone()[0] == 0:
        for item_id, data in config.SHOP_ITEMS.items():
            c.execute("INSERT OR IGNORE INTO shop VALUES (?,?,?,?)",
                      (item_id, data['name'], data['price'], data['type']))

    c.execute("SELECT COUNT(*) FROM titles_shop")
    if c.fetchone()[0] == 0:
        for t in config.TITLES_SHOP:
            c.execute("INSERT OR IGNORE INTO titles_shop VALUES (?,?,?)", (t['id'], t['name'], t['price']))

    c.execute("SELECT COUNT(*) FROM themes_shop")
    if c.fetchone()[0] == 0:
        for th in config.THEMES_SHOP:
            c.execute("INSERT OR IGNORE INTO themes_shop VALUES (?,?,?)", (th['id'], th['name'], th['price']))

    conn.commit()
    conn.close()
