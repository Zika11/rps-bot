import os
import json
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "13Hy-NBQ8ZRFbcbzWB056Pbi1b2w_0OjWM5VByldeiCU"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

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

# ── Users ──────────────────────────────────────────────────────────────
# Columns: user_id | name | username | points | clan | wins | losses | draws | rating | daily_tasks | shop_items

def ensure_users_header():
    ws = get_sheet("users")
    if ws.row_values(1) == []:
        ws.append_row(["user_id","name","username","points","clan","wins","losses","draws","rating","daily_tasks","shop_items"])

def get_user(user_id):
    ensure_users_header()
    ws = get_sheet("users")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if str(r["user_id"]) == str(user_id):
            r["_row"] = i + 2
            return r
    return None

def create_user(user_id, name, username):
    ensure_users_header()
    ws = get_sheet("users")
    ws.append_row([str(user_id), name, username or "", 0, "", 0, 0, 0, 0, "", ""])
    return get_user(user_id)

def get_or_create_user(user_id, name, username):
    u = get_user(user_id)
    if not u:
        u = create_user(user_id, name, username)
    return u

def update_user(user_id, **kwargs):
    ws = get_sheet("users")
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, r in enumerate(records):
        if str(r["user_id"]) == str(user_id):
            row = i + 2
            for key, val in kwargs.items():
                if key in headers:
                    col = headers.index(key) + 1
                    ws.update_cell(row, col, val)
            return

def get_leaderboard(limit=10):
    ws = get_sheet("users")
    records = ws.get_all_records()
    sorted_users = sorted(records, key=lambda x: int(x.get("points", 0) or 0), reverse=True)
    return sorted_users[:limit]

# ── Clans ──────────────────────────────────────────────────────────────
# Columns: clan_name | leader_id | members | points | description

def ensure_clans_header():
    ws = get_sheet("clans")
    if ws.row_values(1) == []:
        ws.append_row(["clan_name","leader_id","members","points","description"])

def get_clan(clan_name):
    ensure_clans_header()
    ws = get_sheet("clans")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if r["clan_name"] == clan_name:
            r["_row"] = i + 2
            return r
    return None

def create_clan(clan_name, leader_id, description=""):
    ensure_clans_header()
    ws = get_sheet("clans")
    ws.append_row([clan_name, str(leader_id), str(leader_id), 0, description])

def update_clan(clan_name, **kwargs):
    ws = get_sheet("clans")
    records = ws.get_all_records()
    headers = ws.row_values(1)
    for i, r in enumerate(records):
        if r["clan_name"] == clan_name:
            row = i + 2
            for key, val in kwargs.items():
                if key in headers:
                    col = headers.index(key) + 1
                    ws.update_cell(row, col, val)
            return

def get_all_clans():
    ensure_clans_header()
    ws = get_sheet("clans")
    records = ws.get_all_records()
    return sorted(records, key=lambda x: int(x.get("points", 0) or 0), reverse=True)

# ── Tasks ──────────────────────────────────────────────────────────────
# Columns: task_id | description | points_reward | type (daily/clan)

def ensure_tasks_header():
    ws = get_sheet("tasks")
    if ws.row_values(1) == []:
        ws.append_row(["task_id","description","points_reward","type"])
        # Add default tasks
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

def get_tasks(task_type=None):
    ensure_tasks_header()
    ws = get_sheet("tasks")
    records = ws.get_all_records()
    if task_type:
        return [r for r in records if r["type"] == task_type]
    return records

# ── Shop ──────────────────────────────────────────────────────────────
# Columns: item_id | name | description | price | emoji

def ensure_shop_header():
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

def get_shop_items():
    ensure_shop_header()
    ws = get_sheet("shop")
    return ws.get_all_records()

# ── Ratings ──────────────────────────────────────────────────────────
def ensure_ratings_header():
    ws = get_sheet("ratings")
    if ws.row_values(1) == []:
        ws.append_row(["user_id","stars","comment"])

def add_rating(user_id, stars):
    ensure_ratings_header()
    ws = get_sheet("ratings")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if str(r["user_id"]) == str(user_id):
            ws.update_cell(i+2, 2, stars)
            return
    ws.append_row([str(user_id), stars, ""])

def get_avg_rating():
    ensure_ratings_header()
    ws = get_sheet("ratings")
    records = ws.get_all_records()
    if not records:
        return 0, 0
    total = sum(int(r["stars"]) for r in records)
    return round(total / len(records), 1), len(records)
