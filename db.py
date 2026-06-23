import os
import json
import threading
import time
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "13Hy-NBQ8ZRFbcbzWB056Pbi1b2w_0OjWM5VByldeiCU"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── In-memory cache ──────────────────────────────────────────────────
_cache = {
    "users": {},      # user_id -> dict
    "clans": {},      # clan_name -> dict
    "tasks": [],
    "shop": [],
    "ratings": {},    # user_id -> stars
}
_dirty = {
    "users": set(),
    "clans": set(),
    "ratings": set(),
}
_initialized = False
_lock = threading.Lock()

# ── Google Sheets client ─────────────────────────────────────────────

def get_client():
    creds_json = os.environ.get("GOOGLE_CREDS")
    if creds_json:
        creds_dict = json.loads(creds_json)
    else:
        with open("creds.json") as f:
            creds_dict = json.load(f)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(name):
    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        return ws

# ── Load all data into cache on startup ─────────────────────────────

def init_cache():
    global _initialized
    with _lock:
        if _initialized:
            return
        _load_users()
        _load_clans()
        _load_tasks()
        _load_shop()
        _load_ratings()
        _initialized = True
        # Start background sync thread
        t = threading.Thread(target=_sync_loop, daemon=True)
        t.start()

def _load_users():
    ws = get_sheet("users")
    if ws.row_values(1) == []:
        ws.append_row(["user_id","name","username","points","clan","wins","losses","draws","rating","daily_tasks","shop_items"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["users"][str(r["user_id"])] = dict(r)

def _load_clans():
    ws = get_sheet("clans")
    if ws.row_values(1) == []:
        ws.append_row(["clan_name","leader_id","members","points","description"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["clans"][r["clan_name"]] = dict(r)

def _load_tasks():
    ws = get_sheet("tasks")
    if ws.row_values(1) == []:
        ws.append_row(["task_id","description","points_reward","type"])
        default_tasks = [
            ["task_1", "العب 5 جولات فردية", 50, "daily"],
            ["task_2", "اكسب 3 جولات متتالية", 100, "daily"],
            ["task_3", "العب ضد صديق", 75, "daily"],
            ["task_4", "العب في قناة", 60, "daily"],
            ["task_5", "حقق 10 انتصارات إجمالية", 200, "daily"],
            ["clan_1", "فوز العشيرة بـ 10 جولات", 500, "clan"],
            ["clan_2", "ضم عضو جديد للعشيرة", 300, "clan"],
            ["clan_3", "العشيرة تلعب 20 جولة", 400, "clan"],
        ]
        ws.append_rows(default_tasks)
        _cache["tasks"] = [{"task_id": r[0], "description": r[1], "points_reward": r[2], "type": r[3]} for r in default_tasks]
        return
    _cache["tasks"] = ws.get_all_records()

def _load_shop():
    ws = get_sheet("shop")
    if ws.row_values(1) == []:
        ws.append_row(["item_id","name","description","price","emoji"])
        default_items = [
            ["item_1", "درع الحجر", "يحميك من الخسارة مرة واحدة", 500, "🛡️"],
            ["item_2", "قفازات الورقة", "ضاعف نقاطك للجولة القادمة", 300, "🧤"],
            ["item_3", "مقص الأسطورة", "شارة نادرة في ملفك", 1000, "⚡"],
            ["item_4", "تاج البطل", "لقب خاص بجانب اسمك", 2000, "👑"],
            ["item_5", "حذاء السرعة", "العب جولتين بدل واحدة", 750, "👟"],
        ]
        ws.append_rows(default_items)
        _cache["shop"] = [{"item_id": r[0], "name": r[1], "description": r[2], "price": r[3], "emoji": r[4]} for r in default_items]
        return
    _cache["shop"] = ws.get_all_records()

def _load_ratings():
    ws = get_sheet("ratings")
    if ws.row_values(1) == []:
        ws.append_row(["user_id","stars","comment"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["ratings"][str(r["user_id"])] = int(r.get("stars", 0))

# ── Background sync every 30 seconds ────────────────────────────────

def _sync_loop():
    while True:
        time.sleep(30)
        try:
            _flush_users()
            _flush_clans()
            _flush_ratings()
        except Exception as e:
            print(f"Sync error: {e}")

def _flush_users():
    with _lock:
        dirty = list(_dirty["users"])
        _dirty["users"].clear()
    if not dirty:
        return
    ws = get_sheet("users")
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()
    id_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}

    for uid in dirty:
        u = _cache["users"].get(uid)
        if not u:
            continue
        row_data = [str(u.get(h, "")) for h in headers]
        if uid in id_to_row:
            ws.update(f"A{id_to_row[uid]}", [row_data])
        else:
            ws.append_row(row_data)

def _flush_clans():
    with _lock:
        dirty = list(_dirty["clans"])
        _dirty["clans"].clear()
    if not dirty:
        return
    ws = get_sheet("clans")
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()
    name_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}

    for clan_name in dirty:
        c = _cache["clans"].get(clan_name)
        if not c:
            continue
        row_data = [str(c.get(h, "")) for h in headers]
        if clan_name in name_to_row:
            ws.update(f"A{name_to_row[clan_name]}", [row_data])
        else:
            ws.append_row(row_data)

def _flush_ratings():
    with _lock:
        dirty = list(_dirty["ratings"])
        _dirty["ratings"].clear()
    if not dirty:
        return
    ws = get_sheet("ratings")
    all_rows = ws.get_all_values()
    id_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}

    for uid in dirty:
        stars = _cache["ratings"].get(uid, 0)
        if uid in id_to_row:
            ws.update_cell(id_to_row[uid], 2, stars)
        else:
            ws.append_row([uid, stars, ""])

# ── Public API (all from cache) ──────────────────────────────────────

def get_or_create_user(user_id, name, username):
    init_cache()
    uid = str(user_id)
    if uid not in _cache["users"]:
        u = {"user_id": uid, "name": name, "username": username or "",
             "points": 0, "clan": "", "wins": 0, "losses": 0,
             "draws": 0, "rating": 0, "daily_tasks": "", "shop_items": ""}
        _cache["users"][uid] = u
        with _lock:
            _dirty["users"].add(uid)
    return _cache["users"][uid]

def get_user(user_id):
    init_cache()
    return _cache["users"].get(str(user_id))

def update_user(user_id, **kwargs):
    init_cache()
    uid = str(user_id)
    if uid in _cache["users"]:
        _cache["users"][uid].update(kwargs)
        with _lock:
            _dirty["users"].add(uid)

def get_leaderboard(limit=10):
    init_cache()
    users = list(_cache["users"].values())
    return sorted(users, key=lambda x: int(x.get("points", 0) or 0), reverse=True)[:limit]

def get_clan(clan_name):
    init_cache()
    return _cache["clans"].get(clan_name)

def create_clan(clan_name, leader_id, description=""):
    init_cache()
    c = {"clan_name": clan_name, "leader_id": str(leader_id),
         "members": str(leader_id), "points": 0, "description": description}
    _cache["clans"][clan_name] = c
    with _lock:
        _dirty["clans"].add(clan_name)

def update_clan(clan_name, **kwargs):
    init_cache()
    if clan_name in _cache["clans"]:
        _cache["clans"][clan_name].update(kwargs)
        with _lock:
            _dirty["clans"].add(clan_name)

def get_all_clans():
    init_cache()
    clans = list(_cache["clans"].values())
    return sorted(clans, key=lambda x: int(x.get("points", 0) or 0), reverse=True)

def get_tasks(task_type=None):
    init_cache()
    if task_type:
        return [t for t in _cache["tasks"] if t["type"] == task_type]
    return _cache["tasks"]

def get_shop_items():
    init_cache()
    return _cache["shop"]

def add_rating(user_id, stars):
    init_cache()
    uid = str(user_id)
    _cache["ratings"][uid] = stars
    with _lock:
        _dirty["ratings"].add(uid)

def get_avg_rating():
    init_cache()
    ratings = list(_cache["ratings"].values())
    if not ratings:
        return 0, 0
    return round(sum(ratings) / len(ratings), 1), len(ratings)
