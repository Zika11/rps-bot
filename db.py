import sqlite3, json, logging, random
from datetime import datetime, date
import config

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# --- دوال المستخدمين ---
def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id, username, first_name, language='ar'):
    conn = get_conn()
    now = datetime.now().isoformat()
    try:
        conn.execute("INSERT INTO users (user_id, username, first_name, language, registered_date, last_login) VALUES (?,?,?,?,?,?)",
                     (user_id, username, first_name, language, now, now))
        conn.execute("INSERT OR IGNORE INTO ratings (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def update_user(user_id, **kwargs):
    if not kwargs: return
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values())
    values.append(user_id)
    conn.execute(f"UPDATE users SET {fields} WHERE user_id=?", values)
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r[0] for r in rows]

# --- العشائر ---
def get_clan(clan_name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clans WHERE name=?", (clan_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_clan(name, leader_id):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO clans (name, leader_id, created_at) VALUES (?,?,?)",
                     (name, leader_id, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_clan(name, **kwargs):
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [name]
    conn.execute(f"UPDATE clans SET {fields} WHERE name=?", values)
    conn.commit()
    conn.close()

def get_all_clans():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM clans ORDER BY points DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_tasks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_shop_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_rating(user_id):
    conn = get_conn()
    row = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else None

def update_rating(user_id, new_rating):
    conn = get_conn()
    conn.execute("UPDATE ratings SET rating=? WHERE user_id=?", (new_rating, user_id))
    conn.commit()
    conn.close()

def get_top_ratings(limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.user_id, u.first_name, r.rating
        FROM ratings r JOIN users u ON r.user_id = u.user_id
        ORDER BY r.rating DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- الأصدقاء ---
def send_friend_request(sender, receiver):
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO friend_requests VALUES (?,?, 'pending')", (sender, receiver))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_pending_requests(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT sender_id FROM friend_requests WHERE receiver_id=? AND status='pending'", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

def accept_friend_request(sender, receiver):
    conn = get_conn()
    conn.execute("UPDATE friend_requests SET status='accepted' WHERE sender_id=? AND receiver_id=?", (sender, receiver))
    conn.execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (sender, receiver))
    conn.execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (receiver, sender))
    conn.commit()
    conn.close()

def reject_friend_request(sender, receiver):
    conn = get_conn()
    conn.execute("DELETE FROM friend_requests WHERE sender_id=? AND receiver_id=?", (sender, receiver))
    conn.commit()
    conn.close()

def get_friends(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT friend_id FROM friends WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]

# --- البطولات ---
def create_tournament(name):
    conn = get_conn()
    cur = conn.execute("INSERT INTO tournaments (name, status) VALUES (?, 'open')", (name,))
    conn.commit()
    tour_id = cur.lastrowid
    conn.close()
    return tour_id

def join_tournament(tour_id, user_id):
    conn = get_conn()
    row = conn.execute("SELECT players FROM tournaments WHERE tour_id=?", (tour_id,)).fetchone()
    if not row: return False
    players = json.loads(row[0] or "[]")
    if len(players) >= 8: return False
    if user_id in players: return True
    players.append(user_id)
    conn.execute("UPDATE tournaments SET players=? WHERE tour_id=?", (json.dumps(players), tour_id))
    conn.commit()
    conn.close()
    return True

def get_tournament(tour_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tournaments WHERE tour_id=?", (tour_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_tournament(tour_id, **kwargs):
    conn = get_conn()
    fields = ', '.join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [tour_id]
    conn.execute(f"UPDATE tournaments SET {fields} WHERE tour_id=?", values)
    conn.commit()
    conn.close()

def get_achievements():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM achievements").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_achievement(user_id, ach_id):
    conn = get_conn()
    u = conn.execute("SELECT achievements FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u: return False
    achieved = u[0].split(",") if u[0] else []
    if ach_id in achieved: return False
    achieved.append(ach_id)
    conn.execute("UPDATE users SET achievements=? WHERE user_id=?", (",".join(achieved), user_id))
    conn.commit()
    conn.close()
    return True

def get_active_clan_war():
    conn = get_conn()
    row = conn.execute("SELECT * FROM clan_wars WHERE active=1").fetchone()
    conn.close()
    return dict(row) if row else None

def add_clan_war_points(clan, amount):
    conn = get_conn()
    conn.execute("UPDATE clan_wars SET points1 = points1 + ? WHERE clan1=? AND active=1", (amount, clan))
    conn.execute("UPDATE clan_wars SET points2 = points2 + ? WHERE clan2=? AND active=1", (amount, clan))
    conn.commit()
    conn.close()

def apply_game_result(user_id, result, move, opponent_id=None):
    conn = get_conn()
    u = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        conn.close()
        return None

    wins = u["wins"] + (1 if result == "win" else 0)
    losses = u["losses"] + (1 if result == "loss" else 0)
    draws = u["draws"] + (1 if result == "draw" else 0)
    points = u["points"] + (10 if result == "win" else (5 if result == "draw" else 0))
    gems = u["gems"] + 1
    rock_used = u["rock_used"] + (1 if move == "rock" else 0)
    win_streak = u["win_streak"] + 1 if result == "win" else 0
    streak_count = u["streak_count"] + 1 if result == "win" else max(0, u["streak_count"] - 1)

    conn.execute("""
        UPDATE users SET
            wins = ?, losses = ?, draws = ?, points = ?, gems = ?,
            rock_used = ?, win_streak = ?, streak_count = ?
        WHERE user_id = ?
    """, (wins, losses, draws, points, gems, rock_used, win_streak, streak_count, user_id))

    rating = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (user_id,)).fetchone()
    rating = rating[0] if rating else config.DEFAULT_RATING
    opp_rating = config.DEFAULT_RATING
    if opponent_id:
        opp = conn.execute("SELECT rating FROM ratings WHERE user_id=?", (opponent_id,)).fetchone()
        if opp:
            opp_rating = opp[0]
    expected = 1 / (1 + 10 ** ((opp_rating - rating) / 400))
    score = 1 if result == "win" else 0.5 if result == "draw" else 0
    new_rating = int(rating + config.RATING_K * (score - expected))
    conn.execute("UPDATE ratings SET rating = ? WHERE user_id = ?", (new_rating, user_id))

    # إضافة XP للباتل باس (باستثناء حالة الاستدعاء المزدوجة، نضيف هنا للمباريات الفعلية)
    add_battle_pass_xp(user_id, 15, conn)

    conn.commit()
    conn.close()
    return {
        "user_id": user_id,
        "wins": wins, "losses": losses, "draws": draws,
        "points": points, "gems": gems, "win_streak": win_streak,
        "rock_used": rock_used, "streak_count": streak_count,
        "rating": new_rating
    }

# --- 🆕 دوال الميزات الجديدة ---
def claim_daily(user_id):
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute("SELECT * FROM daily_claims WHERE user_id=?", (user_id,)).fetchone()
    if row and row["last_claimed_date"] == today:
        conn.close()
        return None
    if row:
        last_date = row["last_claimed_date"]
        streak = row["streak"]
        if last_date:
            last = date.fromisoformat(last_date)
            diff = (date.today() - last).days
            if diff == 1:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1
    else:
        streak = 1
    if streak > 7:
        streak = 1
    reward = config.DAILY_REWARDS.get(streak, (0,0))
    points, gems = reward
    u = conn.execute("SELECT points, gems FROM users WHERE user_id=?", (user_id,)).fetchone()
    if u:
        conn.execute("UPDATE users SET points=?, gems=? WHERE user_id=?", 
                     (u["points"] + points, u["gems"] + gems, user_id))
    conn.execute("INSERT OR REPLACE INTO daily_claims (user_id, last_claimed_date, streak) VALUES (?,?,?)",
                 (user_id, today, streak))
    # إضافة XP يومي للباتل باس
    add_battle_pass_xp(user_id, 10, conn)
    conn.commit()
    conn.close()
    return {"day": streak, "points": points, "gems": gems}

def get_battle_pass(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT OR IGNORE INTO battle_pass (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {"user_id": user_id, "season": 1, "xp": 0, "level": 1, "premium": 0}

def add_battle_pass_xp(user_id, xp_amount, existing_conn=None):
    conn = existing_conn if existing_conn else get_conn()
    bp = conn.execute("SELECT * FROM battle_pass WHERE user_id=?", (user_id,)).fetchone()
    if not bp:
        conn.execute("INSERT INTO battle_pass (user_id, xp, level) VALUES (?,?,?)", (user_id, xp_amount, 1))
        if not existing_conn:
            conn.commit()
            conn.close()
        return 1
    new_xp = bp["xp"] + xp_amount
    new_level = bp["level"]
    while new_level < config.MAX_BATTLE_PASS_LEVEL and new_xp >= new_level * config.BATTLE_PASS_XP_PER_LEVEL:
        new_xp -= new_level * config.BATTLE_PASS_XP_PER_LEVEL
        new_level += 1
    conn.execute("UPDATE battle_pass SET xp=?, level=? WHERE user_id=?", (new_xp, new_level, user_id))
    if not existing_conn:
        conn.commit()
        conn.close()
    return new_level

def spin_wheel(user_id):
    r = random.random()
    cumulative = 0
    for reward_type, value, prob in config.WHEEL_REWARDS:
        cumulative += prob
        if r <= cumulative:
            return (reward_type, value)
    return ("points", 50)
