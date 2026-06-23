import json, logging, time, asyncio, aiosqlite, threading
from datetime import datetime, timedelta

DB_NAME = "rps_bot.db"
_initialized = False

# قفل للقنوات النشطة فقط (تظل في الذاكرة)
_channels_lock = threading.Lock()
_channels_cache = {}

def _safe_int(val, default=0):
    try: return int(val)
    except: return default

def _safe_bool(val, default=False):
    if isinstance(val, bool): return val
    if isinstance(val, str): return val.upper() == "TRUE"
    return default

def _safe_json_load(data, default=None):
    if not data:
        return default
    try:
        return json.loads(data)
    except:
        return default

async def _get_db():
    db = await aiosqlite.connect(DB_NAME)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db

async def _fetchone(query, params=None):
    db = await _get_db()
    cursor = await db.execute(query, params or ())
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None

async def _fetchall(query, params=None):
    db = await _get_db()
    cursor = await db.execute(query, params or ())
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]

async def _execute(query, params=None):
    db = await _get_db()
    await db.execute(query, params or ())
    await db.commit()
    await db.close()

def _run(coro):
    return asyncio.run(coro)

# ── تهيئة الجداول ───────────────────────────────────────────
def init_cache():
    global _initialized
    if _initialized: return
    _run(_create_tables())
    _initialized = True

async def _create_tables():
    from models import create_tables
    await create_tables()

# ── دوال API ─────────────────────────────────────────────────
def get_or_create_user(user_id, name, username):
    uid = str(user_id)
    row = _run(_fetchone("SELECT * FROM users WHERE user_id = ?", (uid,)))
    if not row:
        u = {
            "user_id": uid, "name": name, "username": username or "",
            "points":0,"clan":"","wins":0,"losses":0,"draws":0,"rating":0,
            "daily_tasks":"","shop_items":"","tasks_progress":"","referrals":0,
            "banned":0,"referred":0,"streak_count":0,"last_claim_date":"",
            "daily_claimed":0,"achievements":"","solo_games":0,"random_games":0,
            "friend_games":0,"channel_games":0,"tournament_wins":0,
            "rock_used":0,"paper_used":0,"scissors_used":0,"win_streak":0,
            "bo3_wins":0,"bo3_losses":0,"login_streak":0,"days_since_register":0,
            "gems":0,"title":"","theme":"theme_1","language":"ar",
            "move_history":"[]","story_level":1
        }
        _run(_execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(u.values())
        ))
        return u
    return row

def update_user(user_id, **kwargs):
    uid = str(user_id)
    for k in ("points","wins","losses","draws","rating","referrals","streak_count",
              "solo_games","random_games","friend_games","channel_games",
              "tournament_wins","rock_used","paper_used","scissors_used",
              "win_streak","bo3_wins","bo3_losses","login_streak","days_since_register",
              "gems","story_level"):
        if k in kwargs: kwargs[k] = _safe_int(kwargs[k])
    if "banned" in kwargs: kwargs["banned"] = int(kwargs["banned"])
    if "referred" in kwargs: kwargs["referred"] = int(kwargs["referred"])
    if "daily_claimed" in kwargs: kwargs["daily_claimed"] = int(kwargs["daily_claimed"])

    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [uid]
    _run(_execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values))

def get_user(user_id):
    uid = str(user_id)
    return _run(_fetchone("SELECT * FROM users WHERE user_id = ?", (uid,)))

def get_users_count():
    row = _run(_fetchone("SELECT COUNT(*) as cnt FROM users"))
    return row["cnt"] if row else 0

def get_all_user_ids():
    rows = _run(_fetchall("SELECT user_id FROM users"))
    return [r["user_id"] for r in rows]

def get_leaderboard(limit=10, period="all"):
    rows = _run(_fetchall(f"SELECT * FROM users ORDER BY points DESC LIMIT ?", (limit,)))
    return rows

# ─ـ العشائر ─ـ
def get_clan(clan_name):
    return _run(_fetchone("SELECT * FROM clans WHERE clan_name = ?", (clan_name,)))

def create_clan(clan_name, leader_id, description=""):
    c = {"clan_name": clan_name, "leader_id": str(leader_id), "members": str(leader_id), "points": 0, "description": description}
    _run(_execute("INSERT OR IGNORE INTO clans VALUES (?,?,?,?,?)", (c["clan_name"], c["leader_id"], c["members"], c["points"], c["description"])))

def update_clan(clan_name, **kwargs):
    if "points" in kwargs: kwargs["points"] = _safe_int(kwargs["points"])
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [clan_name]
    _run(_execute(f"UPDATE clans SET {set_clause} WHERE clan_name = ?", values))

def get_all_clans():
    return _run(_fetchall("SELECT * FROM clans ORDER BY points DESC"))

def get_clans_count():
    row = _run(_fetchone("SELECT COUNT(*) as cnt FROM clans"))
    return row["cnt"] if row else 0

# ─ـ المهام ─ـ
def get_tasks(task_type=None):
    if task_type:
        rows = _run(_fetchall("SELECT * FROM tasks WHERE type = ?", (task_type,)))
    else:
        rows = _run(_fetchall("SELECT * FROM tasks"))
    return rows

# ─ـ المتجر ─ـ
def get_shop_items():
    return _run(_fetchall("SELECT * FROM shop"))

# ─ـ التقييمات ─ـ
def add_rating(user_id, stars):
    _run(_execute("INSERT OR REPLACE INTO ratings (user_id, stars) VALUES (?,?)", (str(user_id), stars)))

def get_avg_rating():
    row = _run(_fetchone("SELECT AVG(stars) as avg_rating, COUNT(*) as cnt FROM ratings"))
    avg = round(row["avg_rating"], 1) if row["avg_rating"] else 0
    count = row["cnt"] if row else 0
    return avg, count

# ─ـ المستخدم ─ـ
def is_banned(user_id):
    u = get_user(user_id)
    return bool(u["banned"]) if u else False

def ban_user(user_id): update_user(user_id, banned=1)
def unban_user(user_id): update_user(user_id, banned=0)
def has_been_referred(user_id):
    u = get_user(user_id)
    return bool(u["referred"]) if u else False
def mark_referred(user_id): update_user(user_id, referred=1)

# ─ـ القنوات النشطة (في الذاكرة) ─ـ
def add_active_channel(channel_id, title):
    with _channels_lock:
        _channels_cache[str(channel_id)] = {"id": channel_id, "title": title}

def remove_active_channel(channel_id):
    with _channels_lock:
        _channels_cache.pop(str(channel_id), None)

def get_active_channels():
    with _channels_lock:
        return list(_channels_cache.values())

# ─ـ البطولات ─ـ
def create_tournament(tournament_id, prize=500):
    t = {"tournament_id": tournament_id, "status":"open", "players":"", "rounds":"[]", "winner_id":"", "prize":prize, "created_at":str(datetime.now())}
    _run(_execute("INSERT OR IGNORE INTO tournaments VALUES (?,?,?,?,?,?,?)", (t["tournament_id"], t["status"], t["players"], t["rounds"], t["winner_id"], t["prize"], t["created_at"])))
    return t

def get_active_tournament():
    rows = _run(_fetchall("SELECT * FROM tournaments WHERE status IN ('open','running')"))
    return rows[0] if rows else None

def get_tournament(tournament_id):
    return _run(_fetchone("SELECT * FROM tournaments WHERE tournament_id = ?", (tournament_id,)))

def join_tournament(tournament_id, user_id):
    t = get_tournament(tournament_id)
    if not t or t["status"] != "open": return False
    players = [p for p in t["players"].split(",") if p]
    if str(user_id) in players: return False
    players.append(str(user_id))
    new_players = ",".join(players)
    _run(_execute("UPDATE tournaments SET players = ? WHERE tournament_id = ?", (new_players, tournament_id)))
    return True

def update_tournament(tournament_id, **kwargs):
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [tournament_id]
    _run(_execute(f"UPDATE tournaments SET {set_clause} WHERE tournament_id = ?", values))

# ─ـ الإنجازات ─ـ
def get_achievements():
    return _run(_fetchall("SELECT * FROM achievements"))

def add_achievement(user_id, ach_id):
    u = get_user(user_id)
    if not u: return False
    earned = [a for a in u["achievements"].split(",") if a]
    if ach_id in earned: return False
    earned.append(ach_id)
    new_achievements = ",".join(earned)
    _run(_execute("UPDATE users SET achievements = ? WHERE user_id = ?", (new_achievements, str(user_id))))
    return True

# ─ـ الأصدقاء ─ـ
def get_friends(user_id):
    rows = _run(_fetchall("SELECT friend_id FROM friends WHERE user_id = ?", (str(user_id),)))
    return [r["friend_id"] for r in rows]

def add_friend(user_id, friend_id):
    uid, fid = str(user_id), str(friend_id)
    _run(_execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (uid, fid)))
    _run(_execute("INSERT OR IGNORE INTO friends VALUES (?,?)", (fid, uid)))

def remove_friend(user_id, friend_id):
    uid, fid = str(user_id), str(friend_id)
    _run(_execute("DELETE FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)", (uid, fid, fid, uid)))

def send_friend_request(from_id, to_id, from_name):
    _run(_execute("INSERT OR IGNORE INTO friend_requests VALUES (?,?,?,?)", (str(from_id), str(to_id), from_name, str(datetime.now()))))
    return True

def get_friend_requests(user_id):
    return _run(_fetchall("SELECT * FROM friend_requests WHERE to_id = ?", (str(user_id),)))

def remove_friend_request(user_id, from_id):
    _run(_execute("DELETE FROM friend_requests WHERE to_id = ? AND from_id = ?", (str(user_id), str(from_id))))

# ─ـ التحديات الجماعية ─ـ
def create_group_challenge(challenge_id, group_id, target_wins, prize, duration_hours=24):
    now = datetime.now()
    end = now + timedelta(hours=duration_hours)
    _run(_execute("INSERT OR IGNORE INTO group_challenges VALUES (?,?,?,?,?,?,?,?)",
                  (challenge_id, str(group_id), target_wins, prize, str(now), str(end), "{}", "")))

def get_active_group_challenge(group_id):
    rows = _run(_fetchall("SELECT * FROM group_challenges WHERE group_id = ? AND winner_id = '' AND datetime(end_date) > datetime('now')", (str(group_id),)))
    return rows[0] if rows else None

def update_group_challenge_participant(challenge_id, user_id, wins):
    challenge = _run(_fetchone("SELECT * FROM group_challenges WHERE challenge_id = ?", (challenge_id,)))
    if not challenge: return
    participants = _safe_json_load(challenge["participants"], {})
    participants[str(user_id)] = wins
    _run(_execute("UPDATE group_challenges SET participants = ? WHERE challenge_id = ?", (json.dumps(participants), challenge_id)))
    if wins >= challenge["target_wins"] and not challenge["winner_id"]:
        _run(_execute("UPDATE group_challenges SET winner_id = ? WHERE challenge_id = ?", (str(user_id), challenge_id)))

# ─ـ الألقاب والثيمات ─ـ
def get_titles_shop():
    return _run(_fetchall("SELECT * FROM titles_shop"))

def get_themes_shop():
    return _run(_fetchall("SELECT * FROM themes_shop"))

# ─ـ الأحداث الموسمية ─ـ
def get_active_event():
    rows = _run(_fetchall("SELECT * FROM events WHERE datetime(start_date) <= datetime('now') AND datetime(end_date) >= datetime('now')"))
    return rows[0] if rows else None

# ─ـ حرب العشائر ─ـ
def get_active_clan_war():
    rows = _run(_fetchall("SELECT * FROM clan_wars WHERE datetime(start_date) <= datetime('now') AND datetime(end_date) >= datetime('now')"))
    return rows[0] if rows else None

def add_clan_war_points(clan_name, points):
    war = get_active_clan_war()
    if not war: return
    pts = _safe_json_load(war["clan_points"], {})
    pts[clan_name] = pts.get(clan_name, 0) + points
    _run(_execute("UPDATE clan_wars SET clan_points = ? WHERE war_id = ?", (json.dumps(pts), war["war_id"])))

def create_clan_war(duration_days=7, prize_points=10000, prize_gems=50):
    war_id = f"cw_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    start = datetime.now()
    end = start + timedelta(days=duration_days)
    _run(_execute("INSERT INTO clan_wars VALUES (?,?,?,?,?)", (war_id, str(start), str(end), "{}", "")))
    return {"war_id": war_id, "prize_points": prize_points, "prize_gems": prize_gems}

def end_clan_war(war_id):
    war = _run(_fetchone("SELECT * FROM clan_wars WHERE war_id = ?", (war_id,)))
    if not war or war["winner_clan"]: return
    cp = _safe_json_load(war["clan_points"], {})
    if not cp: return
    winner = max(cp, key=cp.get)
    _run(_execute("UPDATE clan_wars SET winner_clan = ? WHERE war_id = ?", (winner, war_id)))
    clan = get_clan(winner)
    if clan:
        members = [m for m in clan["members"].split(",") if m]
        for mid in members:
            u = get_user(mid)
            if u:
                new_points = _safe_int(u["points"]) + 10000
                new_gems = _safe_int(u["gems"]) + 50
                update_user(mid, points=new_points, gems=new_gems)
