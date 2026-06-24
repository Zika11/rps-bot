import json, logging, random
from config import *
import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_founder(user_id):
    return user_id == FOUNDER_ID

def get_choices_for_user(user_id):
    u = db.get_user(user_id)
    theme = (u.get("theme") if u else None) or "theme_1"
    return THEME_ICONS.get(theme, CHOICES)

def get_result(p1, p2):
    return "draw" if p1 == p2 else ("win" if WIN_MAP[p1] == p2 else "loss")

def smart_bot_choice(user_id):
    u = db.get_user(user_id)
    if not u: return random.choice(list(CHOICES.keys()))
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except Exception:
        moves = []
    if len(moves) < 5: return random.choice(list(CHOICES.keys()))
    from collections import Counter
    counter = Counter(moves)
    most_common = counter.most_common(1)[0][0]
    for k, v in WIN_MAP.items():
        if v == most_common: return k
    return random.choice(list(CHOICES.keys())

def update_user_moves(user_id, move):
    u = db.get_user(user_id)
    if not u: return
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except Exception:
        moves = []
    moves.append(move)
    if len(moves) > 50: moves = moves[-50:]
    db.update_user(user_id, move_history=json.dumps(moves))

def get_all_user_ids():
    try: return db.get_all_user_ids()
    except Exception as e:
        logging.error(f"خطأ في جلب معرفات المستخدمين: {e}")
        return []
