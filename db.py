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
    "group_challenges": {}, "titles_shop": [], "themes_shop": [],
    "events": [], "clan_wars": {}
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
    _load_group_challenges(); _load_events(); _load_clan_wars()

def _load_users():
    ws = get_sheet("users")
    if not ws.row_values(1):
        ws.append_row([
            "user_id","name","username","points","clan","wins","losses","draws",
            "rating","daily_tasks","shop_items","tasks_progress","referrals",
            "banned","referred","streak_count","last_claim_date","daily_claimed",
            "achievements","solo_games","random_games","friend_games","channel_games",
            "tournament_wins","rock_used","paper_used","scissors_used","win_streak",
            "bo3_wins","bo3_losses","login_streak","days_since_register","gems",
            "title","theme","language","move_history","story_level"
        ])
        return
    records = ws.get_all_records()
    for r in records:
        uid = str(r["user_id"])
        _cache["users"][uid] = {
            "user_id": uid,
            "name": r.get("name",""),
            "username": r.get("username",""),
            "points": _safe_int(r.get("points")),
            "clan": r.get("clan",""),
            "wins": _safe_int(r.get("wins")),
            "losses": _safe_int(r.get("losses")),
            "draws": _safe_int(r.get("draws")),
            "rating": _safe_int(r.get("rating")),
            "daily_tasks": r.get("daily_tasks",""),
            "shop_items": r.get("shop_items",""),
            "tasks_progress": r.get("tasks_progress",""),
            "referrals": _safe_int(r.get("referrals")),
            "banned": _safe_bool(r.get("banned")),
            "referred": _safe_bool(r.get("referred")),
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
            "theme": r.get("theme","theme_1"),
            "language": r.get("language","ar"),
            "move_history": r.get("move_history","[]"),
            "story_level": _safe_int(r.get("story_level"), 1)
        }

def _load_clans():
    ws = get_sheet("clans")
    if not ws.row_values(1):
        ws.append_row(["clan_name","leader_id","members","points","description"])
        return
    records = ws.get_all_records()
    for r in records:
        name = r["clan_name"]
        _cache["clans"][name] = {
            "clan_name": name,
            "leader_id": str(r.get("leader_id","")),
            "members": str(r.get("members","")),
            "points": _safe_int(r.get("points")),
            "description": r.get("description","")
        }

def _load_tasks():
    ws = get_sheet("tasks")
    if not ws.row_values(1):
        ws.append_row(["task_id","description","points_reward","type"])
        default_tasks = [
            ["task_1","العب 5 جولات فردية",50,"daily"],
            ["task_2","اكسب 3 جولات متتالية",100,"daily"],
            ["task_3","العب ضد صديق",75,"daily"],
            ["task_4","العب في قناة",60,"daily"],
            ["task_5","حقق 10 انتصارات إجمالية",200,"daily"],
            ["clan_1","فوز العشيرة بـ 10 جولات",500,"clan"],
            ["clan_2","ضم عضو جديد للعشيرة",300,"clan"],
            ["clan_3","العشيرة تلعب 20 جولة",400,"clan"]
        ]
        ws.append_rows(default_tasks)
        _cache["tasks"] = [{"task_id":r[0],"description":r[1],"points_reward":_safe_int(r[2]),"type":r[3]} for r in default_tasks]
        return
    _cache["tasks"] = [{"task_id":r["task_id"],"description":r["description"],"points_reward":_safe_int(r["points_reward"]),"type":r["type"]} for r in ws.get_all_records()]

def _load_shop():
    ws = get_sheet("shop")
    if not ws.row_values(1):
        ws.append_row(["item_id","name","description","price","emoji"])
        default_items = [
            ["item_1","درع الحجر","يحميك من الخسارة مرة واحدة",500,"🛡️"],
            ["item_2","قفازات الورقة","ضاعف نقاطك للجولة القادمة",300,"🧤"],
            ["item_3","مقص الأسطورة","شارة نادرة في ملفك",1000,"⚡"],
            ["item_4","تاج البطل","لقب خاص بجانب اسمك",2000,"👑"],
            ["item_5","حذاء السرعة","العب جولتين بدل واحدة",750,"👟"],
            ["item_6","صندوق الكنز","يحتوي على جائزة عشوائية",2000,"🎁"]
        ]
        ws.append_rows(default_items)
        _cache["shop"] = [{"item_id":r[0],"name":r[1],"description":r[2],"price":_safe_int(r[3]),"emoji":r[4]} for r in default_items]
        return
    _cache["shop"] = [{"item_id":r["item_id"],"name":r["name"],"description":r["description"],"price":_safe_int(r["price"]),"emoji":r["emoji"]} for r in ws.get_all_records()]

def _load_ratings():
    ws = get_sheet("ratings")
    if not ws.row_values(1):
        ws.append_row(["user_id","stars","comment"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["ratings"][str(r["user_id"])] = _safe_int(r.get("stars"))

def _load_tournaments():
    ws = get_sheet("tournaments")
    if not ws.row_values(1):
        ws.append_row(["tournament_id","status","players","rounds","winner_id","prize","created_at"])
        return
    records = ws.get_all_records()
    for r in records:
        tid = str(r["tournament_id"])
        _cache["tournaments"][tid] = {
            "tournament_id": tid, "status": r.get("status","open"),
            "players": r.get("players",""), "rounds": r.get("rounds","[]"),
            "winner_id": r.get("winner_id",""), "prize": _safe_int(r.get("prize",500)),
            "created_at": r.get("created_at",str(datetime.now()))
        }

def _load_achievements():
    ws = get_sheet("achievements")
    if not ws.row_values(1):
        ws.append_row(["ach_id","name","description","icon","condition_field","condition_value"])
        default_achievements = [
            ["ach_1","أول خطوة","سجل في البوت لأول مرة","🌟","registered","1"],
            ["ach_2","المحارب","العب 10 جولات فردية","⚔️","solo_games","10"],
            ["ach_3","الأسطورة","اكسب 50 جولة","👑","wins","50"],
            ["ach_4","صياد النقاط","اجمع 5000 نقطة","💰","points","5000"],
            ["ach_5","المغامر","العب 5 جولات عشوائية","🎲","random_games","5"],
            ["ach_6","الصديق الوفي","العب 10 جولات مع أصدقاء","🤝","friend_games","10"],
            ["ach_7","ملك القنوات","العب 20 جولة في القنوات","📺","channel_games","20"],
            ["ach_8","النجم اليومي","احصل على مكافأة يومية 7 أيام متتالية","📅","streak","7"],
            ["ach_9","المحترف","اكسب 3 جولات متتالية","🔥","win_streak","3"],
            ["ach_10","بطل البطولة","فوز ببطولة","🏆","tournament_win","1"],
            ["ach_11","الداعم","ادعُ 3 أصدقاء","📢","referrals","3"],
            ["ach_12","الجامع","اجمع 10 بطاقات من المتجر","🎒","items_owned","10"],
            ["ach_13","المقيّم","قيم البوت","⭐","rated","1"],
            ["ach_14","مؤسس العشيرة","أنشئ عشيرة","🏛️","clan_created","1"],
            ["ach_15","عضو العشيرة","انضم لعشيرة","👥","clan_joined","1"],
            ["ach_16","البطل الخارق","اكسب 100 جولة","💪","wins","100"],
            ["ach_17","مليونير النقاط","اجمع 50000 نقطة","💎","points","50000"],
            ["ach_18","المغامر الأسطوري","العب 100 جولة عشوائية","🌍","random_games","100"],
            ["ach_19","صديق الكل","العب 50 جولة مع أصدقاء","💖","friend_games","50"],
            ["ach_20","ملك الشارات","اجمع 15 إنجاز","🎖️","achievements_count","15"],
            ["ach_21","المقاتل الليلي","العب بعد منتصف الليل","🌙","night_play","1"],
            ["ach_22","الصبور","اخسر 20 جولة","😅","losses","20"],
            ["ach_23","المتوازن","تعادل في 10 جولات","⚖️","draws","10"],
            ["ach_24","المثابر","ادخل البوت 5 أيام متتالية","🗓️","login_streak","5"],
            ["ach_25","الوفي","استخدم البوت لمدة 30 يوم","📆","days_since_register","30"],
            ["ach_26","المقامر","اربح جولة عشوائية","🎰","random_win","1"],
            ["ach_27","السريع","اربح جولة في القناة","⚡","channel_win","1"],
            ["ach_28","الخبير","اكسب 5 جولات BO3","🧠","bo3_wins","5"],
            ["ach_29","المقاتل","اخسر جولة BO3","🥊","bo3_losses","1"],
            ["ach_30","ملك الحجر","استخدم الحجر 50 مرة","🪨","rock_used","50"]
        ]
        ws.append_rows(default_achievements)
        _cache["achievements"] = [{"ach_id":r[0],"name":r[1],"description":r[2],"icon":r[3],"condition_field":r[4],"condition_value":_safe_int(r[5])} for r in default_achievements]
        return
    _cache["achievements"] = [{"ach_id":r["ach_id"],"name":r["name"],"description":r["description"],"icon":r["icon"],"condition_field":r["condition_field"],"condition_value":_safe_int(r["condition_value"])} for r in ws.get_all_records()]

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

def _load_events():
    ws = get_sheet("events")
    if not ws.row_values(1):
        ws.append_row(["event_id","name","start_date","end_date","special_tasks","special_bosses"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["events"].append({
            "event_id": r["event_id"], "name": r["name"],
            "start_date": r["start_date"], "end_date": r["end_date"],
            "special_tasks": json.loads(r.get("special_tasks","[]")),
            "special_bosses": json.loads(r.get("special_bosses","[]"))
        })

def _load_clan_wars():
    ws = get_sheet("clan_wars")
    if not ws.row_values(1):
        ws.append_row(["war_id","start_date","end_date","clan_points","winner_clan"])
        return
    records = ws.get_all_records()
    for r in records:
        _cache["clan_wars"][r["war_id"]] = {
            "war_id": r["war_id"], "start_date": r["start_date"],
            "end_date": r["end_date"], "clan_points": json.loads(r.get("clan_points","{}")),
            "winner_clan": r.get("winner_clan","")
        }

# ── API ─────────────────────────────────────────────────────
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
            "gems":0,"title":"","theme":"theme_1","language":"ar",
            "move_history":"[]","story_level":1
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
                  "win_streak","bo3_wins","bo3_losses","login_streak","days_since_register","gems","story_level"):
            if k in kwargs: kwargs[k] = _safe_int(kwargs[k])
        _cache["users"][uid].update(kwargs)
        with _lock: _dirty["users"].add(uid)

def get_user(user_id):
    if not _initialized: init_cache()
    return _cache["users"].get(str(user_id))

def get_leaderboard(limit=10, period="all"):
    if not _initialized: init_cache()
    users = list(_cache["users"].values())
    return sorted(users, key=lambda x: _safe_int(x.get("points")), reverse=True)[:limit]

def get_clan(clan_name):
    if not _initialized: init_cache()
    return _cache["clans"].get(clan_name)

def create_clan(clan_name, leader_id, description=""):
    if not _initialized: init_cache()
    c = {"clan_name": clan_name, "leader_id": str(leader_id), "members": str(leader_id), "points": 0, "description": description}
    _cache["clans"][clan_name] = c
    with _lock: _dirty["clans"].add(clan_name)

def update_clan(clan_name, **kwargs):
    if not _initialized: init_cache()
    if clan_name in _cache["clans"]:
        if "points" in kwargs: kwargs["points"] = _safe_int(kwargs["points"])
        _cache["clans"][clan_name].update(kwargs)
        with _lock: _dirty["clans"].add(clan_name)

def get_all_clans():
    if not _initialized: init_cache()
    clans = list(_cache["clans"].values())
    return sorted(clans, key=lambda x: _safe_int(x.get("points")), reverse=True)

def get_tasks(task_type=None):
    if not _initialized: init_cache()
    if task_type: return [t for t in _cache["tasks"] if t["type"] == task_type]
    return _cache["tasks"]

def get_shop_items():
    if not _initialized: init_cache()
    return _cache["shop"]

def add_rating(user_id, stars):
    if not _initialized: init_cache()
    uid = str(user_id)
    _cache["ratings"][uid] = _safe_int(stars)
    with _lock: _dirty["ratings"].add(uid)

def get_avg_rating():
    if not _initialized: init_cache()
    ratings = list(_cache["ratings"].values())
    if not ratings: return 0,0
    return round(sum(ratings)/len(ratings),1), len(ratings)

def is_banned(user_id):
    u = get_user(user_id)
    return u.get("banned", False) if u else False

def ban_user(user_id): update_user(user_id, banned=True)
def unban_user(user_id): update_user(user_id, banned=False)

def has_been_referred(user_id):
    u = get_user(user_id)
    return u.get("referred", False) if u else False
def mark_referred(user_id): update_user(user_id, referred=True)

def add_active_channel(channel_id, title):
    if not _initialized: init_cache()
    with _lock: _cache["channels"][str(channel_id)] = {"id": channel_id, "title": title}

def remove_active_channel(channel_id):
    with _lock: _cache["channels"].pop(str(channel_id), None)

def get_active_channels():
    with _lock: return list(_cache["channels"].values())

# ─ـ بطولات ─ـ
def create_tournament(tournament_id, prize=500):
    if not _initialized: init_cache()
    t = {"tournament_id": tournament_id, "status":"open", "players":"", "rounds":"[]", "winner_id":"", "prize":prize, "created_at":str(datetime.now())}
    _cache["tournaments"][tournament_id] = t
    with _lock: _dirty["tournaments"].add(tournament_id)
    return t

def get_active_tournament():
    if not _initialized: init_cache()
    for t in _cache["tournaments"].values():
        if t["status"] in ("open","running"): return t
    return None

def get_tournament(tournament_id):
    if not _initialized: init_cache()
    return _cache["tournaments"].get(tournament_id)

def join_tournament(tournament_id, user_id):
    t = _cache["tournaments"].get(tournament_id)
    if not t or t["status"]!="open": return False
    players = t["players"].split(",") if t["players"] else []
    if str(user_id) in players: return False
    players.append(str(user_id))
    t["players"] = ",".join(players)
    with _lock: _dirty["tournaments"].add(tournament_id)
    return True

def update_tournament(tournament_id, **kwargs):
    if tournament_id in _cache["tournaments"]:
        _cache["tournaments"][tournament_id].update(kwargs)
        with _lock: _dirty["tournaments"].add(tournament_id)

# ─ـ إنجازات ─ـ
def get_achievements():
    if not _initialized: init_cache()
    return _cache["achievements"]

def add_achievement(user_id, ach_id):
    if not _initialized: init_cache()
    u = get_user(user_id)
    if not u: return False
    earned = u.get("achievements","").split(",") if u.get("achievements") else []
    if ach_id in earned: return False
    earned.append(ach_id)
    update_user(user_id, achievements=",".join(earned))
    return True

# ─ـ أصدقاء ─ـ
def get_friends(user_id):
    if not _initialized: init_cache()
    return _cache["friends"].get(str(user_id), [])

def add_friend(user_id, friend_id):
    uid, fid = str(user_id), str(friend_id)
    _cache["friends"].setdefault(uid, []).append(fid) if fid not in _cache["friends"][uid] else None
    _cache["friends"].setdefault(fid, []).append(uid) if uid not in _cache["friends"][fid] else None

def remove_friend(user_id, friend_id):
    uid, fid = str(user_id), str(friend_id)
    if uid in _cache["friends"] and fid in _cache["friends"][uid]: _cache["friends"][uid].remove(fid)
    if fid in _cache["friends"] and uid in _cache["friends"][fid]: _cache["friends"][fid].remove(uid)

def send_friend_request(from_id, to_id, from_name):
    if not _initialized: init_cache()
    tid = str(to_id)
    if tid not in _cache["friend_requests"]: _cache["friend_requests"][tid] = []
    for req in _cache["friend_requests"][tid]:
        if req["from"] == str(from_id): return False
    _cache["friend_requests"][tid].append({"from":str(from_id),"name":from_name,"date":str(datetime.now())})
    return True

def get_friend_requests(user_id):
    if not _initialized: init_cache()
    return _cache["friend_requests"].get(str(user_id), [])

def remove_friend_request(user_id, from_id):
    uid = str(user_id)
    if uid in _cache["friend_requests"]:
        _cache["friend_requests"][uid] = [req for req in _cache["friend_requests"][uid] if req["from"]!=str(from_id)]

# ─ـ تحديات جماعية ─ـ
def create_group_challenge(challenge_id, group_id, target_wins, prize, duration_hours=24):
    now = datetime.now(); end = now + timedelta(hours=duration_hours)
    c = {"challenge_id":challenge_id,"group_id":str(group_id),"target_wins":target_wins,"prize":prize,"start_date":str(now),"end_date":str(end),"participants":"{}","winner_id":""}
    _cache["group_challenges"][challenge_id] = c

def get_active_group_challenge(group_id):
    gid = str(group_id); now = datetime.now()
    for c in _cache["group_challenges"].values():
        if c["group_id"] == gid:
            end = datetime.fromisoformat(c["end_date"])
            if end > now and not c["winner_id"]: return c
    return None

def update_group_challenge_participant(challenge_id, user_id, wins):
    c = _cache["group_challenges"].get(challenge_id)
    if not c: return
    participants = json.loads(c["participants"])
    participants[str(user_id)] = wins
    c["participants"] = json.dumps(participants)
    if wins >= c["target_wins"] and not c["winner_id"]:
        c["winner_id"] = str(user_id)

# ─ـ ألقاب وثيمات ─ـ
def get_titles_shop(): return _cache["titles_shop"]
def get_themes_shop(): return _cache["themes_shop"]

# ─ـ أحداث وحروب عشائر ─ـ
def get_active_event():
    now = datetime.now()
    for ev in _cache["events"]:
        start = datetime.fromisoformat(ev["start_date"]); end = datetime.fromisoformat(ev["end_date"])
        if start <= now <= end: return ev
    return None

def get_active_clan_war():
    now = datetime.now()
    for war in _cache["clan_wars"].values():
        start = datetime.fromisoformat(war["start_date"]); end = datetime.fromisoformat(war["end_date"])
        if start <= now <= end: return war
    return None

def add_clan_war_points(clan_name, points):
    war = get_active_clan_war()
    if not war: return
    pts = json.loads(war["clan_points"])
    pts[clan_name] = pts.get(clan_name,0) + points
    war["clan_points"] = json.dumps(pts)

def create_clan_war(duration_days=7, prize_points=10000, prize_gems=50):
    war_id = f"cw_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    start = datetime.now(); end = start + timedelta(days=duration_days)
    war = {"war_id":war_id,"start_date":str(start),"end_date":str(end),"clan_points":"{}","winner_clan":"","prize_points":prize_points,"prize_gems":prize_gems}
    _cache["clan_wars"][war_id] = war
    return war

def end_clan_war(war_id):
    war = _cache["clan_wars"].get(war_id)
    if not war or war["winner_clan"]: return
    cp = json.loads(war["clan_points"])
    if not cp: return
    winner = max(cp, key=cp.get)
    war["winner_clan"] = winner
    clan = get_clan(winner)
    if clan:
        members = clan["members"].split(",")
        for mid in members:
            update_user(int(mid), points=_safe_int(get_user(int(mid)).get("points",0)) + war.get("prize_points",0),
                       gems=_safe_int(get_user(int(mid)).get("gems",0)) + war.get("prize_gems",0))

def _sync_loop():
    while True:
        time.sleep(30)
        _flush_with_retry(_flush_users, "users")
        _flush_with_retry(_flush_clans, "clans")
        _flush_with_retry(_flush_ratings, "ratings")
        _flush_with_retry(_flush_tournaments, "tournaments")

def _flush_with_retry(flush_func, dirty_key):
    try: flush_func()
    except Exception as e:
        print(f"Sync error in {dirty_key}: {e}")
        with _lock:
            if dirty_key in _dirty: _dirty[dirty_key].update(_cache[dirty_key].keys() if isinstance(_cache[dirty_key], dict) else [])

def _flush_users():
    with _lock:
        dirty = list(_dirty["users"]); _dirty["users"].clear()
    if not dirty: return
    ws = get_sheet("users")
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()
    id_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}
    for uid in dirty:
        u = _cache["users"].get(uid)
        if not u: continue
        u_sheet = dict(u)
        u_sheet["banned"] = "TRUE" if u_sheet.get("banned") else "FALSE"
        u_sheet["referred"] = "TRUE" if u_sheet.get("referred") else "FALSE"
        u_sheet["daily_claimed"] = "TRUE" if u_sheet.get("daily_claimed") else "FALSE"
        row_data = [str(u_sheet.get(h, "")) for h in headers]
        if uid in id_to_row: ws.update(f"A{id_to_row[uid]}", [row_data])
        else: ws.append_row(row_data)

def _flush_clans():
    with _lock:
        dirty = list(_dirty["clans"]); _dirty["clans"].clear()
    if not dirty: return
    ws = get_sheet("clans")
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()
    name_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}
    for clan_name in dirty:
        c = _cache["clans"].get(clan_name)
        if not c: continue
        row_data = [str(c.get(h, "")) for h in headers]
        if clan_name in name_to_row: ws.update(f"A{name_to_row[clan_name]}", [row_data])
        else: ws.append_row(row_data)

def _flush_ratings():
    with _lock:
        dirty = list(_dirty["ratings"]); _dirty["ratings"].clear()
    if not dirty: return
    ws = get_sheet("ratings")
    all_rows = ws.get_all_values()
    id_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}
    for uid in dirty:
        stars = _cache["ratings"].get(uid, 0)
        if uid in id_to_row: ws.update_cell(id_to_row[uid], 2, stars)
        else: ws.append_row([uid, str(stars), ""])

def _flush_tournaments():
    with _lock:
        dirty = list(_dirty["tournaments"]); _dirty["tournaments"].clear()
    if not dirty: return
    ws = get_sheet("tournaments")
    headers = ws.row_values(1)
    all_rows = ws.get_all_values()
    id_to_row = {str(row[0]): i+2 for i, row in enumerate(all_rows[1:])}
    for tid in dirty:
        t = _cache["tournaments"].get(tid)
        if not t: continue
        row_data = [str(t.get(h, "")) for h in headers]
        if tid in id_to_row: ws.update(f"A{id_to_row[tid]}", [row_data])
        else: ws.append_row(row_data)