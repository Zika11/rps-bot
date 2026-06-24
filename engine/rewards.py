import sqlite3, logging
from datetime import datetime
import config

DB = "rps_bot.db"
logger = logging.getLogger(__name__)

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def batch_process_channel_rewards_with_streak(chat_id, players_rewards):
    if not players_rewards:
        return
    conn = get_conn()
    now = datetime.now().isoformat()
    user_ids = [p["user_id"] for p in players_rewards]

    placeholders = ",".join("?" * len(user_ids))
    users = conn.execute(
        f"SELECT user_id, points, clan, xp, level FROM users WHERE user_id IN ({placeholders})",
        user_ids
    ).fetchall()
    user_data = {u["user_id"]: {"points": u["points"], "xp": u["xp"], "level": u["level"]} for u in users}

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
            for threshold in sorted(config.STREAK_MULTIPLIERS.keys(), reverse=True):
                if new_streak >= threshold:
                    reward *= config.STREAK_MULTIPLIERS[threshold]
                    break
            xp_gained = config.XP_PER_WIN
        else:
            new_streak = 0
            xp_gained = config.XP_PER_DRAW if p.get("draw") else config.XP_PER_LOSS

        new_streaks.append((chat_id, uid, new_streak, now))

        current_points = user_data.get(uid, {"points": 0})["points"]
        current_xp = user_data.get(uid, {"xp": 0})["xp"]
        current_level = user_data.get(uid, {"level": 1})["level"]

        new_xp = current_xp + xp_gained
        # حساب المستوى الجديد
        new_level = current_level
        for lvl in sorted(config.LEVEL_THRESHOLDS.keys()):
            if new_xp >= config.LEVEL_THRESHOLDS[lvl]:
                new_level = lvl

        user_updates.append((current_points + reward, new_xp, new_level, uid))
        channel_points_updates.append((chat_id, uid, reward, now))

    conn.executemany("UPDATE users SET points = ?, xp = ?, level = ? WHERE user_id = ?", user_updates)

    conn.executemany("""
        INSERT INTO channel_user_streaks (chat_id, user_id, streak, last_vote_time) 
        VALUES (?,?,?,?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET streak=?, last_vote_time=?
    """, [(c, u, s, t, s, t) for (c, u, s, t) in new_streaks])

    conn.executemany("""
        INSERT INTO channel_user_points (chat_id, user_id, points, last_updated) 
        VALUES (?,?,?,?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET points = points + ?, last_updated = excluded.last_updated
    """, [(c, u, r, t, r) for (c, u, r, t) in channel_points_updates])

    conn.commit()
    conn.close()
