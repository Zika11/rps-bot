import json, logging, random
from datetime import datetime, date, timedelta
from config import *
import db
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ─ـ دوال الترجمة ─────────────────────────────────────────────
translations = {}

def load_translations():
    for lang in ["ar", "en"]:
        try:
            with open(f"lang/{lang}.json", "r", encoding="utf-8") as f:
                translations[lang] = json.load(f)
        except FileNotFoundError:
            logging.warning(f"ملف اللغة {lang}.json غير موجود. سيتم استخدام المفاتيح مباشرة.")
            translations[lang] = {}

def _(key, user_id):
    u = db.get_user(user_id)
    lang = (u or {}).get("language", "ar")
    return translations.get(lang, {}).get(key, key)

# ─ـ دوال مساعدة ─────────────────────────────────────────────
def get_result(p1, p2):
    return "draw" if p1 == p2 else ("win" if WIN_MAP[p1] == p2 else "loss")

def is_founder(user_id):
    return user_id == FOUNDER_ID

def get_choices_for_user(user_id):
    u = db.get_user(user_id)
    theme = u.get("theme", "theme_1") if u else "theme_1"
    return THEME_ICONS.get(theme, CHOICES)

def get_all_user_ids():
    return db.get_all_user_ids()

# ─ـ الذكاء الاصطناعي ──────────────────────────────────────
def smart_bot_choice(user_id):
    u = db.get_user(user_id)
    if not u:
        return random.choice(list(CHOICES.keys()))
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except Exception:
        moves = []
    if len(moves) < 5:
        return random.choice(list(CHOICES.keys()))
    from collections import Counter
    counter = Counter(moves)
    most_common = counter.most_common(1)[0][0]
    for k, v in WIN_MAP.items():
        if v == most_common:
            return k
    return random.choice(list(CHOICES.keys()))

def update_user_moves(user_id, move):
    u = db.get_user(user_id)
    if not u:
        return
    try:
        moves = json.loads(u.get("move_history", "[]"))
    except Exception:
        moves = []
    moves.append(move)
    if len(moves) > 50:
        moves = moves[-50:]
    db.update_user(user_id, move_history=json.dumps(moves))

# ─ـ المهام اليومية ───────────────────────────────────────
async def check_and_complete_task(user_id, task_id, bot_context, progress_increment=1):
    u = db.get_user(user_id)
    if not u:
        return False
    today = str(date.today())
    progress_data = u.get("tasks_progress")
    if progress_data:
        try:
            progress = json.loads(progress_data)
        except Exception as e:
            logging.error(f"تقدم مهمة تالف لـ {user_id}: {e}")
            progress = {"date": today, "tasks": {}}
    else:
        progress = {"date": today, "tasks": {}}
    if progress.get("date") != today:
        progress = {"date": today, "tasks": {}}
    tasks_progress = progress.setdefault("tasks", {})
    current = tasks_progress.get(task_id, 0) + progress_increment
    tasks_progress[task_id] = current
    all_tasks = db.get_tasks()
    task_def = next((t for t in all_tasks if t["task_id"] == task_id), None)
    rewarded = False
    if task_def:
        required = {"task_1": 5, "task_2": 3, "task_3": 1, "task_4": 1, "task_5": 10}.get(task_id, 1)
        if current >= required and not tasks_progress.get(f"{task_id}_done"):
            pts_reward = int(task_def["points_reward"])
            db.update_user(user_id, points=int(u.get("points", 0)) + pts_reward)
            tasks_progress[f"{task_id}_done"] = True
            try:
                await bot_context.bot.send_message(
                    user_id,
                    f"🎉 أكملت مهمة *{task_def['description']}* وحصلت على {pts_reward} نقطة!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"فشل إرسال إشعار مهمة لـ {user_id}: {e}")
            rewarded = True
    db.update_user(user_id, tasks_progress=json.dumps(progress))
    return rewarded

# ─ـ نقاط العشائر ─────────────────────────────────────────
def add_clan_points(user_id, amount):
    u = db.get_user(user_id)
    if not u or not u.get("clan"):
        return
    clan = db.get_clan(u["clan"])
    if not clan:
        return
    current_pts = int(clan.get("points", 0) or 0) + amount
    db.update_clan(u["clan"], points=current_pts)
    if db.get_active_clan_war():
        db.add_clan_war_points(u["clan"], amount)

# ─ـ المكافأة اليومية ─────────────────────────────────────
async def claim_daily(user_id, context):
    u = db.get_user(user_id)
    if not u:
        return ""
    today = str(date.today())
    if u.get("last_claim_date") != today:
        db.update_user(user_id, daily_claimed=0)
        u = db.get_user(user_id)
    if u.get("daily_claimed"):
        return "✅ استلمت مكافأتك النهارده خلاص! تعالى بكره."
    streak = db._safe_int(u.get("streak_count"))
    last_date = u.get("last_claim_date")
    yesterday = str(date.today() - timedelta(days=1))
    if last_date == yesterday:
        streak += 1
    else:
        streak = 1
    reward = min(MIN_STREAK_MULTIPLIER * streak, MAX_STREAK_REWARD)
    db.update_user(user_id, streak_count=streak, last_claim_date=today, daily_claimed=True,
                   points=int(u.get("points", 0)) + reward)
    return f"🎁 مكافأة اليوم {streak}! حصلت على {reward} نقطة. النهارده يومك رقم {streak} على التوالي!"

# ─ـ الإنجازات ────────────────────────────────────────────
async def check_achievements(user_id, context):
    u = db.get_user(user_id)
    if not u:
        return
    all_achs = db.get_achievements()
    earned = [a for a in u.get("achievements", "").split(",") if a]
    for ach in all_achs:
        if ach["ach_id"] in earned:
            continue
        field = ach["condition_field"]
        needed = ach["condition_value"]
        current = 0
        if field == "wins": current = int(u.get("wins", 0))
        elif field == "losses": current = int(u.get("losses", 0))
        elif field == "draws": current = int(u.get("draws", 0))
        elif field == "points": current = int(u.get("points", 0))
        elif field == "streak": current = int(u.get("streak_count", 0))
        elif field == "referrals": current = int(u.get("referrals", 0))
        elif field == "solo_games": current = int(u.get("solo_games", 0))
        elif field == "random_games": current = int(u.get("random_games", 0))
        elif field == "friend_games": current = int(u.get("friend_games", 0))
        elif field == "channel_games": current = int(u.get("channel_games", 0))
        elif field == "items_owned":
            owned = [o for o in u.get("shop_items", "").split(",") if o]
            current = len(owned)
        elif field == "clan_created":
            for clan in db.get_all_clans():
                if str(clan["leader_id"]) == str(user_id):
                    current = 1
                    break
        elif field == "clan_joined": current = 1 if u.get("clan") else 0
        elif field == "tournament_win": current = int(u.get("tournament_wins", 0))
        elif field == "rated":
            rating = db.get_user_rating(user_id)
            current = 1 if rating else 0
        elif field == "achievements_count": current = len(earned)
        elif field == "rock_used": current = int(u.get("rock_used", 0))
        elif field == "win_streak": current = int(u.get("win_streak", 0))
        elif field == "bo3_wins": current = int(u.get("bo3_wins", 0))
        elif field == "bo3_losses": current = int(u.get("bo3_losses", 0))
        elif field == "login_streak": current = int(u.get("login_streak", 0))
        elif field == "days_since_register": current = int(u.get("days_since_register", 0))
        elif field == "channel_win": current = int(u.get("channel_games", 0))
        elif field == "random_win": current = int(u.get("random_games", 0))
        elif field == "night_play":
            if datetime.now().hour < 5: current = 1
        if current >= needed:
            if db.add_achievement(user_id, ach["ach_id"]):
                try:
                    await context.bot.send_message(
                        user_id,
                        f"🎖️ إنجاز جديد: {ach['icon']} *{ach['name']}* - {ach['description']}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logging.error(f"فشل إرسال إنجاز لـ {user_id}: {e}")

# ─ـ وظائف Redis ──────────────────────────────────────────
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logging.warning(f"Redis غير متاح: {e}")
    redis_client = None

def cache_get(key):
    if redis_client:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    return None

def cache_set(key, value, ttl=300):
    if redis_client:
        redis_client.set(key, json.dumps(value), ex=ttl)
