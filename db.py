import json, logging, time, asyncio, aiosqlite
from datetime import datetime, timedelta

DB_NAME = "rps_bot.db"
_initialized = False

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
    return db

def init_cache():
    global _initialized
    if _initialized: return
    asyncio.run(_create_tables())
    _initialized = True

async def _create_tables():
    # تستخدم دالة create_tables من models.py
    from models import create_tables
    await create_tables()

# ── دوال API متطابقة تماماً ──────────────────────────────────
def get_or_create_user(user_id, name, username):
    uid = str(user_id)
    db = asyncio.run(_get_db())
    row = asyncio.run(_fetchone("SELECT * FROM users WHERE user_id = ?", (uid,)))
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
        asyncio.run(_execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(u.values())
        ))
        return u
    return dict(row)

def update_user(user_id, **kwargs):
    uid = str(user_id)
    # تحويل الأعداد والقيم المنطقية
    for k in ("points","wins","losses","draws","rating","referrals","streak_count",
              "solo_games","random_games","friend_games","channel_games",
              "tournament_wins","rock_used","paper_used","scissors_used",
              "win_streak","bo3_wins","bo3_losses","login_streak","days_since_register","gems","story_level"):
        if k in kwargs: kwargs[k] = _safe_int(kwargs[k])
    if "banned" in kwargs: kwargs["banned"] = int(kwargs["banned"])
    if "referred" in kwargs: kwargs["referred"] = int(kwargs["referred"])
    if "daily_claimed" in kwargs: kwargs["daily_claimed"] = int(kwargs["daily_claimed"])

    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [uid]
    asyncio.run(_execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values))

def get_user(user_id):
    uid = str(user_id)
    row = asyncio.run(_fetchone("SELECT * FROM users WHERE user_id = ?", (uid,)))
    return dict(row) if row else None

# ─ـ دوال مساعدة داخلية غير متزامنة ─ـ
async def _fetchone(query, params):
    db = await _get_db()
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    await db.close()
    return row

async def _fetchall(query, params=None):
    db = await _get_db()
    if params:
        cursor = await db.execute(query, params)
    else:
        cursor = await db.execute(query)
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]

async def _execute(query, params=None):
    db = await _get_db()
    if params:
        await db.execute(query, params)
    else:
        await db.execute(query)
    await db.commit()
    await db.close()

# ─ـ دوال API المتبقية (أمثلة) ─ـ
def get_users_count():
    if not _initialized: init_cache()
    row = asyncio.run(_fetchone("SELECT COUNT(*) as cnt FROM users", ()))
    return row["cnt"] if row else 0

def get_clans_count():
    row = asyncio.run(_fetchone("SELECT COUNT(*) as cnt FROM clans", ()))
    return row["cnt"] if row else 0

def get_all_user_ids():
    rows = asyncio.run(_fetchall("SELECT user_id FROM users"))
    return [r["user_id"] for r in rows]

# ... أكمل باقي الدوال (clans, tasks, shop, tournaments, achievements...)
# بنفس الطريقة، باستخدام SQLite. يمكنك نسخ المنطق من دوال get_user أعلاه.
