import sqlite3, json, logging
from datetime import datetime, date
from config import *

logging.basicConfig(level=logging.INFO)

DB = "rps_bot.db"

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- المستخدمين ----------
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
    if not kwargs:
        return
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

# ---------- العشائر ----------
def get_clan(clan_name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clans WHERE name=?", (clan_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_clan_by_leader(leader_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM clans WHERE leader_id=?", (leader_id,)).fetchone()
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

def get_clan_members(clan_name):
    conn = get_conn()
    rows = conn.execute("SELECT user_id, first_name, points FROM users WHERE clan=?", (clan_name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- المهام ----------
def get_tasks():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- المتجر ----------
def get_shop_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM shop").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------- التصنيف ----------
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

# ---------- الأصدقاء ----------
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

# ---------- البطولات ----------
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

# ---------- الإنجازات ----------
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

# ---------- حرب العشائر ----------
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
