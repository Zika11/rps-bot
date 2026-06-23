import os, json, threading, time
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "13Hy-NBQ8ZRFbcbzWB056Pbi1b2w_0OjWM5VByldeiCU"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_client_lock = threading.Lock()

def get_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        creds_json = os.environ.get("GOOGLE_CREDS")
        if not creds_json:
            raise EnvironmentError("❌ GOOGLE_CREDS غير موجود في متغيرات البيئة.")
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        _client = gspread.authorize(creds)
        return _client

def get_sheet(name):
    client = get_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=20)
        return ws

_cache = {
    "users": {}, "clans": {}, "tasks": [], "shop": [], "ratings": {},
    "channels": {}, "tournaments": {}, "achievements": [],
    "friends": {}, "friend_requests": {},
    "group_challenges": {}, "titles_shop": [], "themes_shop": []
}
_dirty = {
    "users": set(), "clans": set(), "ratings": set(), "tournaments": set()
}
_initialized = False
_lock = threading.Lock()

def _safe_int(val, default=0):
    try: return int(val)
    except: return default

def _safe_bool(val, default=False):
    if isinstance(val, bool): return val
    if isinstance(val, str): return val.upper() == "TRUE"
    return default

def init_cache():
    global _initialized
    if _initialized: return
    _load_all()
    with _lock: _initialized = True
    t = threading.Thread(target=_sync_loop, daemon=True)
    t.start()

def _load_all():
    _load_users(); _load_clans(); _load_tasks(); _load_shop(); _load_ratings()
    _load_tournaments(); _load_achievements(); _load_titles(); _load_themes()
    _load_group_challenges()

def _load_users():
    ws = get_sheet("users")
    if not ws.row_values(1):
        ws.append_row(["user_id","name","username","points","clan","wins","losses","draws","rating","daily_tasks","shop_items","tasks_progress","referrals","banned","referred","streak_count","last_claim_date","daily_claimed","achievements","solo_games","random_games","friend_games","channel_games","tournament_wins","rock_used","paper_used","scissors_used","win_streak","bo3_wins","bo3_losses","login_streak","days_since_register","gems","title","theme"])
        return
    records = ws.get_all_records()
    for r in records:
        uid = str(r["user_id"])
        _cache["users"][uid] = {
            "user_id": uid, "name": r.get("name",""), "username": r.get("username",""),
            "points": _safe_int(r.get("points")), "clan": r.get("clan",""),
            "wins": _safe_int(r.get("wins")), "losses": _safe_int(r.get("losses")),
            "draws": _safe_int(r.get("draws")), "rating": _safe_int(r.get("rating")),
            "daily_tasks": r.get("daily_tasks",""), "shop_items": r.get("shop_items",""),
            "tasks_progress": r.get("tasks_progress",""), "referrals": _safe_int(r.get("referrals")),
            "banned": _safe_bool(r.get("banned")), "referred": _safe_bool(r.get("referred")),
            "streak_count": _safe_int(r.get("streak_count")),
            "last_claim_date": r.get("last_claim_date",""),
            "daily_claimed": _safe_bool(r.get("daily_claimed")),
            "achievements": r.get("achievements",""),
            "solo_games": _safe_int(r.get("solo_games")),
            "random_games": _safe_int(r.get("random_games")),
            "friend_games": _safe_int(r.get("friend_games")),
            "channel_games": _safe_int(r.get("channel_games")),
            "tournament_wins": _safe_int(r.get("tournament_wins")),
            "rock_used": _safe_int(r.get("rock_used")),
            "paper_used": _safe_int(r.get("paper_used")),
            "scissors_used": _safe_int(r.get("scissors_used")),
            "win_streak": _safe_int(r.get("win_streak")),
            "bo3_wins": _safe_int(r.get("bo3_wins")),
            "bo3_losses": _safe_int(r.get("bo3_losses")),
            "login_streak": _safe_int(r.get("login_streak")),
            "days_since_register": _safe_int(r.get("days_since_register")),
            "gems": _safe_int(r.get("gems")),
            "title": r.get("title",""),
            "theme": r.get("theme","theme_1")
        }

def _load_clans(): ... # كما في الإصدارات السابقة
def _load_tasks(): ... # كما سبق
def _load_shop():
    ws = get_sheet("shop")
    if not ws.row_values(1):
        ws.append_row(["item_id","name","description","price","emoji"])
        default_items = [
            ["item_1", "درع الحجر", "يحميك من الخسارة مرة واحدة", 500, "🛡️"],
            ["item_2", "قفازات الورقة", "ضاعف نقاطك للجولة القادمة", 300, "🧤"],
            ["item_3", "مقص الأسطورة", "شارة نادرة في ملفك", 1000, "⚡"],
            ["item_4", "تاج البطل", "لقب خاص بجانب اسمك", 2000, "👑"],
            ["item_5", "حذاء السرعة", "العب جولتين بدل واحدة", 750, "👟"],
            ["item_6", "صندوق الكنز", "يحتوي على جائزة عشوائية", 2000, "🎁"]
        ]
        ws.append_rows(default_items)
        _cache["shop"] = [{"item_id":r[0],"name":r[1],"description":r[2],"price":_safe_int(r[3]),"emoji":r[4]} for r in default_items]
        return
    _cache["shop"] = [{"item_id":r["item_id"],"name":r["name"],"description":r["description"],"price":_safe_int(r["price"]),"emoji":r["emoji"]} for r in ws.get_all_records()]

def _load_ratings(): ... # كما سبق
def _load_tournaments(): ... # كما سبق
def _load_achievements(): ... # كما سبق
def _load_titles():
    ws = get_sheet("titles")
    if not ws.row_values(1):
        ws.append_row(["title_id","name","description","cost_gems"])
        default_titles = [
            ["title_1","المحارب","لقب أساسي",0],
            ["title_2","الأسطورة","للفائزين بـ 100 جولة",50],
            ["title_3","ملك الحجر","لمن استخدم الحجر 200 مرة",30],
            ["title_4","الوفي","للأصدقاء المخلصين",20],
            ["title_5","الخبير","للفائزين بـ 5 بطولات",100]
        ]
        ws.append_rows(default_titles)
        _cache["titles_shop"] = [{"title_id":r[0],"name":r[1],"description":r[2],"cost_gems":_safe_int(r[3])} for r in default_titles]
        return
    _cache["titles_shop"] = [{"title_id":r["title_id"],"name":r["name"],"description":r["description"],"cost_gems":_safe_int(r["cost_gems"])} for r in ws.get_all_records()]

def _load_themes():
    ws = get_sheet("themes")
    if not ws.row_values(1):
        ws.append_row(["theme_id","name","description","cost_gems","icon_set"])
        default_themes = [
            ["theme_1","كلاسيكي","الشكل الافتراضي",0,"🪨📄✂️"],
            ["theme_2","الذهب","رموز ذهبية",50,"🟡🟨🟧"],
            ["theme_3","النار","رموز نارية",80,"🔥🌪️💧"],
            ["theme_4","الفضاء","كواكب ونجوم",120,"🌍🌟🌙"]
        ]
        ws.append_rows(default_themes)
        _cache["themes_shop"] = [{"theme_id":r[0],"name":r[1],"description":r[2],"cost_gems":_safe_int(r[3]),"icon_set":r[4]} for r in default_themes]
        return
    _cache["themes_shop"] = [{"theme_id":r["theme_id"],"name":r["name"],"description":r["description"],"cost_gems":_safe_int(r["cost_gems"]),"icon_set":r["icon_set"]} for r in ws.get_all_records()]

def _load_group_challenges():
    ws = get_sheet("group_challenges")
    if not ws.row_values(1):
        ws.append_row(["challenge_id","group_id","target_wins","prize","start_date","end_date","participants","winner_id"])
        return
    records = ws.get_all_records()
    for r in records:
        cid = r["challenge_id"]
        _cache["group_challenges"][cid] = {
            "challenge_id": cid, "group_id": r["group_id"],
            "target_wins": _safe_int(r["target_wins"]), "prize": _safe_int(r["prize"]),
            "start_date": r["start_date"], "end_date": r["end_date"],
            "participants": r.get("participants","{}"), "winner_id": r.get("winner_id","")
        }

# ── واجهة API ─────────────────────────────────────────────
def get_or_create_user(user_id, name, username):
    if not _initialized: init_cache()
    uid = str(user_id)
    if uid not in _cache["users"]:
        u = {
            "user_id": uid, "name": name, "username": username or "",
            "points":0,"clan":"","wins":0,"losses":0,"draws":0,"rating":0,
            "daily_tasks":"","shop_items":"","tasks_progress":"","referrals":0,
            "banned":False,"referred":False,"streak_count":0,"last_claim_date":"",
            "daily_claimed":False,"achievements":"","solo_games":0,"random_games":0,
            "friend_games":0,"channel_games":0,"tournament_wins":0,
            "rock_used":0,"paper_used":0,"scissors_used":0,"win_streak":0,
            "bo3_wins":0,"bo3_losses":0,"login_streak":0,"days_since_register":0,
            "gems":0,"title":"","theme":"theme_1"
        }
        _cache["users"][uid] = u
        with _lock: _dirty["users"].add(uid)
    return _cache["users"][uid]

def update_user(user_id, **kwargs):
    if not _initialized: init_cache()
    uid = str(user_id)
    if uid in _cache["users"]:
        for k in ("points","wins","losses","draws","rating","referrals","streak_count",
                  "solo_games","random_games","friend_games","channel_games",
                  "tournament_wins","rock_used","paper_used","scissors_used",
                  "win_streak","bo3_wins","bo3_losses","login_streak","days_since_register","gems"):
            if k in kwargs: kwargs[k] = _safe_int(kwargs[k])
        _cache["users"][uid].update(kwargs)
        with _lock: _dirty["users"].add(uid)

def get_user(user_id):
    if not _initialized: init_cache()
    return _cache["users"].get(str(user_id))

# بقية دوال API (clans, leaderboard, tasks, shop, ratings, channels, tournaments, achievements, friends, challenges, titles, themes)
# مذكورة في الإصدارات السابقة، نكتفي بإدراج المهم منها لتجنب الإطالة، مع العلم أنها موجودة في الملف الكامل.

def get_friends(user_id):
    if not _initialized: init_cache()
    return _cache["friends"].get(str(user_id), [])

def add_friend(user_id, friend_id):
    uid, fid = str(user_id), str(friend_id)
    _cache["friends"].setdefault(uid, []).append(fid) if fid not in _cache["friends"][uid] else None
    _cache["friends"].setdefault(fid, []).append(uid) if uid not in _cache["friends"][fid] else None

def remove_friend(user_id, friend_id): ... # مشابه
def send_friend_request(from_id, to_id, from_name): ... # مشابه
def get_friend_requests(user_id): ... # مشابه
def remove_friend_request(user_id, from_id): ... # مشابه

def create_group_challenge(challenge_id, group_id, target_wins, prize, duration_hours=24):
    now = datetime.now()
    end = now + timedelta(hours=duration_hours)
    c = {"challenge_id":challenge_id,"group_id":str(group_id),"target_wins":target_wins,
         "prize":prize,"start_date":str(now),"end_date":str(end),"participants":"{}","winner_id":""}
    _cache["group_challenges"][challenge_id] = c

def get_active_group_challenge(group_id): ... # تنفيذ
def update_group_challenge_participant(challenge_id, user_id, wins): ... # تنفيذ

def get_titles_shop(): return _cache["titles_shop"]
def get_themes_shop(): return _cache["themes_shop"]

# _flush_* functions كما في الإصدارات السابقة
# ...
