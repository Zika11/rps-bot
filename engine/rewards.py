import sqlite3, logging
from datetime import datetime
import config

DB = "rps_bot.db"
logger = logging.getLogger(__name__)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def batch_process_channel_rewards_with_streak(chat_id, players_rewards, streak_bonus):
    if not players_rewards:
        return
    conn = get_conn()
    now = datetime.now().isoformat()
    user_ids = [p["user_id"] for p in players_rewards]

    placeholders = ",".join("?" * len(user_ids))
    users = conn.execute(
        f"SELECT user_id, points, clan FROM users WHERE user_id IN ({placeholders})",
        user_ids
    ).fetchall()
    user_points = {u["user_id"]: u["points"] for u in users}
    user_clan = {u["user_id"]: u["clan"] for u in users}

    streaks = conn.execute(
        f"SELECT user_id, streak FROM channel_user_streaks WHERE chat_id=? AND user_id IN ({placeholders})",
        [chat_id] + user_ids
    ).fetchall()
    streak_data = {s["user_id"]: s["streak"] for s in streaks}

    new_streaks = []
    user_updates = []
    channel_points_updates = []

    for p in players_rewards:
        uid = p["user_id"]
        reward = p["reward"]
        is_winner = p["is_winner"]

        current_streak = streak_data.get(uid, 0)
        if is_winner:
            new_streak = current_streak + 1
            if new_streak > 1:
                reward += streak_bonus * new_streak
        else:
            new_streak = 0

        new_streaks.append((chat_id, uid, new_streak, now))

        current_points = user_points.get(uid, 0)
        user_updates.append((current_points + reward, uid))

        channel_points_updates.append((chat_id, uid, reward))

    conn.executemany("UPDATE users SET points = ? WHERE user_id = ?", user_updates)

    conn.executemany("""
        INSERT INTO channel_user_streaks (chat_id, user_id, streak, last_vote_time) 
        VALUES (?,?,?,?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET streak=?, last_vote_time=?
    """, [(c, u, s, t, s, t) for (c, u, s, t) in new_streaks])

    conn.executemany("""
        INSERT INTO channel_user_points (chat_id, user_id, points) 
        VALUES (?,?,?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET points = points + ?
    """, [(c, u, r, r) for (c, u, r) in channel_points_updates])

    conn.commit()
    conn.close()
