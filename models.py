import sqlite3

DB_NAME = "rps_bot.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def create_tables():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            username TEXT,
            points INTEGER DEFAULT 0,
            clan TEXT,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            daily_tasks TEXT,
            shop_items TEXT,
            tasks_progress TEXT,
            referrals INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            referred INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_claim_date TEXT,
            daily_claimed INTEGER DEFAULT 0,
            achievements TEXT,
            solo_games INTEGER DEFAULT 0,
            random_games INTEGER DEFAULT 0,
            friend_games INTEGER DEFAULT 0,
            channel_games INTEGER DEFAULT 0,
            tournament_wins INTEGER DEFAULT 0,
            rock_used INTEGER DEFAULT 0,
            paper_used INTEGER DEFAULT 0,
            scissors_used INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            bo3_wins INTEGER DEFAULT 0,
            bo3_losses INTEGER DEFAULT 0,
            login_streak INTEGER DEFAULT 0,
            days_since_register INTEGER DEFAULT 0,
            gems INTEGER DEFAULT 0,
            title TEXT,
            theme TEXT DEFAULT 'theme_1',
            language TEXT DEFAULT 'ar',
            move_history TEXT DEFAULT '[]',
            story_level INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS clans (
            clan_name TEXT PRIMARY KEY,
            leader_id TEXT,
            members TEXT,
            points INTEGER DEFAULT 0,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            description TEXT,
            points_reward INTEGER,
            type TEXT
        );

        CREATE TABLE IF NOT EXISTS shop (
            item_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            price INTEGER,
            emoji TEXT
        );

        CREATE TABLE IF NOT EXISTS ratings (
            user_id TEXT PRIMARY KEY,
            stars INTEGER,
            comment TEXT
        );

        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id TEXT PRIMARY KEY,
            status TEXT,
            players TEXT,
            rounds TEXT,
            winner_id TEXT,
            prize INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS achievements (
            ach_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            icon TEXT,
            condition_field TEXT,
            condition_value INTEGER
        );

        CREATE TABLE IF NOT EXISTS friends (
            user_id TEXT,
            friend_id TEXT,
            PRIMARY KEY (user_id, friend_id)
        );

        CREATE TABLE IF NOT EXISTS friend_requests (
            from_id TEXT,
            to_id TEXT,
            from_name TEXT,
            date TEXT,
            PRIMARY KEY (from_id, to_id)
        );

        CREATE TABLE IF NOT EXISTS group_challenges (
            challenge_id TEXT PRIMARY KEY,
            group_id TEXT,
            target_wins INTEGER,
            prize INTEGER,
            start_date TEXT,
            end_date TEXT,
            participants TEXT,
            winner_id TEXT
        );

        CREATE TABLE IF NOT EXISTS titles_shop (
            title_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            cost_gems INTEGER
        );

        CREATE TABLE IF NOT EXISTS themes_shop (
            theme_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            cost_gems INTEGER,
            icon_set TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            special_tasks TEXT,
            special_bosses TEXT
        );

        CREATE TABLE IF NOT EXISTS clan_wars (
            war_id TEXT PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            clan_points TEXT,
            winner_clan TEXT
        );
    """)
    conn.commit()
    conn.close()
