import os, random, asyncio, json, logging, threading
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram import error as tg_error
import db
from flask import Flask, jsonify, render_template_string

# ─ـ إعدادات التسجيل ─────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ─ـ الثوابت (من البيئة أو افتراضية) ─────────────────────────
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

try:
    FOUNDER_ID = int(os.environ.get("FOUNDER_ID", "1232067711"))
except (ValueError, TypeError):
    FOUNDER_ID = 1232067711

# ─ـ ثوابت اللعبة ───────────────────────────────────────────
CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
THEME_ICONS = {
    "theme_1": CHOICES,
    "theme_2": {"rock":"🟡 حجر","paper":"🟨 ورقة","scissors":"🟧 مقص"},
    "theme_3": {"rock":"🔥 حجر","paper":"🌪️ ورقة","scissors":"💧 مقص"},
    "theme_4": {"rock":"🌍 حجر","paper":"🌟 ورقة","scissors":"🌙 مقص"}
}
CHOICES_SPOCK = {"rock": "🪨", "paper": "📄", "scissors": "✂️", "lizard": "🦎", "spock": "🖖"}
WIN_MAP_SPOCK = {
    "scissors": ["paper", "lizard"], "paper": ["rock", "spock"],
    "rock": ["lizard", "scissors"], "lizard": ["spock", "paper"],
    "spock": ["scissors", "rock"]
}

# ─ـ ثوابت النقاط ───────────────────────────────────────────
WIN_POINTS_SOLO = 10
LOSS_POINTS_SOLO = -3
DRAW_POINTS_SOLO = 5
WIN_POINTS_MULTI = 15
LOSS_POINTS_MULTI = -3
ROUND_WIN_POINTS = 5
ROUND_LOSS_POINTS = -1
ROUND_DRAW_POINTS = 2
DAILY_REFERRAL_POINTS = 1000

# ─ـ إعدادات اللعبة ─────────────────────────────────────────
GAME_TIMEOUT = 120          # ثواني
CHANNEL_ROUND_INTERVAL = 120 # ثواني
MAX_STREAK_REWARD = 100
MIN_STREAK_MULTIPLIER = 10
MAX_STORY_LEVEL = 3
STORY_LEVELS = {
    1: {"boss": "الرجل الحجري", "emoji": "🗿", "story": "في مملكة الأحجار..."},
    2: {"boss": "ملك الورق", "emoji": "📜", "story": "بعد هزيمة الرجل الحجري..."},
    3: {"boss": "سيد المقصات", "emoji": "⚔️", "story": "أقوى زعيم في المملكة..."}
}

# ─ـ أقفال للبيانات المشتركة ────────────────────────────────
active_games_lock = asyncio.Lock()
pending_matches_lock = asyncio.Lock()
channel_games_lock = asyncio.Lock()
channel_tasks_lock = asyncio.Lock()

# ─ـ هياكل البيانات المشتركة ─────────────────────────────────
pending_matches = []
active_games = {}
channel_tasks = {}
channel_games = {}
channel_last_play = {}

# ─ـ دعم متعدد اللغات ──────────────────────────────────────
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

# ─ـ Flask Dashboard ──────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route('/api/stats')
def api_stats():
    users_count = db.get_users_count()
    clans_count = db.get_clans_count()
    active_channels = len(db.get_active_channels())
    avg_rating, count = db.get_avg_rating()
    return jsonify({
        "users": users_count, "clans": clans_count,
        "channels": active_channels, "avg_rating": avg_rating,
        "rating_count": count
    })

@flask_app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify(db.get_leaderboard(20))

@flask_app.route('/')
def dashboard():
    html = """<!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>لوحة تحكم البوت</title></head>
    <body style="font-family:sans-serif;max-width:800px;margin:auto;">
        <h1>👑 لوحة تحكم البوت</h1>
        <div id="stats"></div>
        <h2>🏆 التصنيف</h2>
        <table id="leaderboard" border="1" width="100%"></table>
        <script>
            fetch('/api/stats').then(r=>r.json()).then(d=>{
                document.getElementById('stats').innerHTML =
                    `<p>👥 المستخدمين: ${d.users} | 🗡️ العشائر: ${d.clans} | 📺 القنوات: ${d.channels} | ⭐ التقييم: ${d.avg_rating}/50 (${d.rating_count})</p>`;
            });
            fetch('/api/leaderboard').then(r=>r.json()).then(d=>{
                let html = '<tr><th>الترتيب</th><th>الاسم</th><th>النقاط</th></tr>';
                d.forEach((u,i)=>html+=`<tr><td>${i+1}</td><td>${u.name}</td><td>${u.points}</td></tr>`);
                document.getElementById('leaderboard').innerHTML = html;
            });
        </script>
    </body></html>"""
    return render_template_string(html)

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False)

# ─ـ Redis Caching (اختياري) ─ـ
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
        if data: return json.loads(data)
    return None

def cache_set(key, value, ttl=300):
    if redis_client:
        redis_client.set(key, json.dumps(value), ex=ttl)

def get_result(p1, p2): return "draw" if p1==p2 else ("win" if WIN_MAP[p1]==p2 else "loss")
def is_founder(user_id): return user_id == FOUNDER_ID

def get_choices_for_user(user_id):
    u = db.get_user(user_id)
    theme = u.get("theme","theme_1") if u else "theme_1"
    return THEME_ICONS.get(theme, CHOICES)

def get_all_user_ids():
    try: return db.get_all_user_ids()
    except Exception as e:
        logging.error(f"خطأ في جلب معرفات المستخدمين: {e}")
        return []

# ─ـ Keyboards ─ـ
def main_menu_keyboard(user_id=None):
    rows = [
        [InlineKeyboardButton("🎮 العب الآن", callback_data="menu_play")],
        [InlineKeyboardButton("🎁 المكافأة اليومية", callback_data="daily_bonus")],
        [InlineKeyboardButton("🏆 التصنيف", callback_data="menu_rank"), InlineKeyboardButton("🗡️ العشائر", callback_data="menu_clans")],
        [InlineKeyboardButton("🎁 المهام", callback_data="menu_tasks"), InlineKeyboardButton("🛒 المتجر", callback_data="menu_shop")],
        [InlineKeyboardButton("👥 الأصدقاء", callback_data="menu_friends"), InlineKeyboardButton("📺 القنوات", callback_data="menu_channels")],
        [InlineKeyboardButton("👤 حسابي", callback_data="menu_profile"), InlineKeyboardButton("❓ طريقة اللعب", callback_data="menu_howto")],
        [InlineKeyboardButton("⭐ تقييم البوت", callback_data="menu_rate"), InlineKeyboardButton("💎 دعم البوت", callback_data="menu_support")],
        [InlineKeyboardButton("🔗 دعوة صديق", callback_data="menu_referral"), InlineKeyboardButton("🏆 انضم للبطولة", callback_data="join_tournament")],
    ]
    if user_id and is_founder(user_id):
        rows.append([InlineKeyboardButton("👑 لوحة المؤسس", callback_data="founder_panel")])
    return InlineKeyboardMarkup(rows)

def back_btn(target="menu_main"): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=target)]])

def play_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 لعب فردي", callback_data="play_solo")],
        [InlineKeyboardButton("👥 لعب مع صديق", callback_data="play_friend")],
        [InlineKeyboardButton("🎲 لعب عشوائي", callback_data="play_random")],
        [InlineKeyboardButton("📺 لعب في قناة/جروب", callback_data="play_channel")],
        [InlineKeyboardButton("🖖 Spock", callback_data="play_spock")],
        [InlineKeyboardButton("📖 وضع القصة", callback_data="story_mode")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

def solo_keyboard(user_id=None):
    choices = get_choices_for_user(user_id)
    return InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=f"solo_{k}") for k,v in choices.items()]])

def mp_keyboard(game_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=f"mp_{game_id}_{k}") for k,v in CHOICES.items()]])

def channel_keyboard(channel_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=f"ch_{channel_id}_{k}") for k,v in CHOICES.items()]])

def stars_keyboard():
    options = [1,5,10,20,30,40,50]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[:4]],
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[4:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
    ])

def founder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة نقاط", callback_data="f_addpts"), InlineKeyboardButton("➖ خصم نقاط", callback_data="f_subpts")],
        [InlineKeyboardButton("🚫 حظر لاعب", callback_data="f_ban"), InlineKeyboardButton("✅ فك حظر", callback_data="f_unban")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="f_broadcast")],
        [InlineKeyboardButton("🛒 إدارة المتجر", callback_data="f_shop"), InlineKeyboardButton("🎁 إدارة المهام", callback_data="f_tasks")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="f_stats"), InlineKeyboardButton("⭐ التقييمات", callback_data="f_ratings")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

# ─ـ دوال اللعبة الأساسية ─────────────────────────────────────
async def game_timeout(game_id, context):
    await asyncio.sleep(GAME_TIMEOUT)
    async with active_games_lock:
        game = active_games.get(game_id)
        if game:
            try:
                await context.bot.send_message(game["p1"], "⌛ انتهت صلاحية التحدي.")
                if game.get("p2"):
                    await context.bot.send_message(game["p2"], "⌛ انتهت صلاحية التحدي.")
            except Exception as e:
                logging.error(f"فشل إرسال انتهاء صلاحية التحدي: {e}")
            del active_games[game_id]

# ─ـ المهام والعشائر ─ـ
async def check_and_complete_task(user_id, task_id, bot_context, progress_increment=1):
    u = db.get_user(user_id)
    if not u: return False
    today = str(date.today())
    progress_data = u.get("tasks_progress")
    if progress_data:
        try: progress = json.loads(progress_data)
        except Exception as e:
            logging.error(f"تقدم مهمة تالف لـ {user_id}: {e}")
            progress = {"date": today, "tasks":{}}
    else: progress = {"date": today, "tasks":{}}
    if progress.get("date") != today: progress = {"date": today, "tasks":{}}
    tasks_progress = progress.setdefault("tasks", {})
    current = tasks_progress.get(task_id, 0) + progress_increment
    tasks_progress[task_id] = current
    all_tasks = db.get_tasks()
    task_def = next((t for t in all_tasks if t["task_id"]==task_id), None)
    rewarded = False
    if task_def:
        required = {"task_1":5,"task_2":3,"task_3":1,"task_4":1,"task_5":10}.get(task_id,1)
        if current >= required and not tasks_progress.get(f"{task_id}_done"):
            pts_reward = int(task_def["points_reward"])
            db.update_user(user_id, points=int(u.get("points",0))+pts_reward)
            tasks_progress[f"{task_id}_done"] = True
            try:
                await bot_context.bot.send_message(user_id, f"🎉 أكملت مهمة *{task_def['description']}* وحصلت على {pts_reward} نقطة!", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"فشل إرسال إشعار مهمة لـ {user_id}: {e}")
            rewarded = True
    db.update_user(user_id, tasks_progress=json.dumps(progress))
    return rewarded

def add_clan_points(user_id, amount):
    u = db.get_user(user_id)
    if not u or not u.get("clan"): return
    clan = db.get_clan(u["clan"])
    if not clan: return
    current_pts = int(clan.get("points",0) or 0) + amount
    db.update_clan(u["clan"], points=current_pts)
    if db.get_active_clan_war():
        db.add_clan_war_points(u["clan"], amount)

# ─ـ المكافأة اليومية ─ـ
async def claim_daily(user_id, context):
    u = db.get_user(user_id)
    if not u: return ""
    today = str(date.today())
    if u.get("last_claim_date") != today:
        db.update_user(user_id, daily_claimed=False)
        u = db.get_user(user_id)

    if u.get("daily_claimed"):
        return "✅ استلمت مكافأتك النهارده خلاص! تعالى بكره."

    streak = db._safe_int(u.get("streak_count"))
    last_date = u.get("last_claim_date")
    yesterday = str(date.today() - timedelta(days=1))
    if last_date == yesterday: streak += 1
    else: streak = 1
    reward = min(MIN_STREAK_MULTIPLIER * streak, MAX_STREAK_REWARD)
    db.update_user(user_id, streak_count=streak, last_claim_date=today, daily_claimed=True,
                   points=int(u.get("points",0)) + reward)
    return f"🎁 مكافأة اليوم {streak}! حصلت على {reward} نقطة. النهارده يومك رقم {streak} على التوالي!"

# ─ـ الإنجازات ─ـ
async def check_achievements(user_id, context):
    u = db.get_user(user_id)
    if not u: return
    all_achs = db.get_achievements()
    earned = [a for a in u.get("achievements","").split(",") if a]
    for ach in all_achs:
        if ach["ach_id"] in earned: continue
        field = ach["condition_field"]; needed = ach["condition_value"]; current = 0
        if field == "wins": current = int(u.get("wins",0))
        elif field == "losses": current = int(u.get("losses",0))
        elif field == "draws": current = int(u.get("draws",0))
        elif field == "points": current = int(u.get("points",0))
        elif field == "streak": current = int(u.get("streak_count",0))
        elif field == "referrals": current = int(u.get("referrals",0))
        elif field == "solo_games": current = int(u.get("solo_games",0))
        elif field == "random_games": current = int(u.get("random_games",0))
        elif field == "friend_games": current = int(u.get("friend_games",0))
        elif field == "channel_games": current = int(u.get("channel_games",0))
        elif field == "items_owned":
            owned = [o for o in u.get("shop_items","").split(",") if o]
            current = len(owned)
        elif field == "clan_created":
            for clan in db.get_all_clans():
                if str(clan["leader_id"]) == str(user_id): current = 1; break
        elif field == "clan_joined": current = 1 if u.get("clan") else 0
        elif field == "tournament_win": current = int(u.get("tournament_wins",0))
        elif field == "rated": current = 1 if str(user_id) in db._cache.get("ratings", {}) else 0
        elif field == "achievements_count": current = len(earned)
        elif field == "rock_used": current = int(u.get("rock_used",0))
        elif field == "win_streak": current = int(u.get("win_streak",0))
        elif field == "bo3_wins": current = int(u.get("bo3_wins",0))
        elif field == "bo3_losses": current = int(u.get("bo3_losses",0))
        elif field == "login_streak": current = int(u.get("login_streak",0))
        elif field == "days_since_register": current = int(u.get("days_since_register",0))
        elif field == "channel_win": current = int(u.get("channel_games",0))
        elif field == "random_win": current = int(u.get("random_games",0))
        elif field == "night_play":
            if datetime.now().hour < 5: current = 1
        if current >= needed:
            if db.add_achievement(user_id, ach["ach_id"]):
                try:
                    await context.bot.send_message(user_id, f"🎖️ إنجاز جديد: {ach['icon']} *{ach['name']}* - {ach['description']}", parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"فشل إرسال إنجاز لـ {user_id}: {e}")

# ─ـ القنوات ─ـ
async def channel_loop(chat_id, context):
    while True:
        await asyncio.sleep(CHANNEL_ROUND_INTERVAL)
        async with channel_tasks_lock:
            if chat_id not in channel_tasks: break
        async with channel_games_lock:
            game = channel_games.get(chat_id)
            if game and datetime.now() - game["created"] > timedelta(seconds=90):
                await cancel_channel_game(chat_id, context)
            if chat_id in channel_games: continue
            try:
                msg = await context.bot.send_message(chat_id, "🎮 *جولة جديدة بين عضوين!* أول واحد يضغط هيبقى اللاعب الأول 👇", parse_mode="Markdown", reply_markup=channel_keyboard(chat_id))
                channel_games[chat_id] = {"player1":None,"choice1":None,"player2":None,"choice2":None,"message_id":msg.message_id,"created":datetime.now()}
                channel_last_play[chat_id] = datetime.now()
            except (tg_error.Forbidden, tg_error.BadRequest, tg_error.ChatNotFound):
                await stop_channel_internal(chat_id, context); break
            except Exception as e:
                logging.error(f"channel_loop {chat_id}: {e}")

async def cancel_channel_game(channel_id, context, reason=""):
    async with channel_games_lock:
        game = channel_games.pop(channel_id, None)
    if game:
        try:
            await context.bot.edit_message_text(chat_id=channel_id, message_id=game["message_id"], text=f"🚫 الجولة اتلغت{' - ' + reason if reason else ''}")
        except Exception as e:
            logging.error(f"فشل إلغاء جولة القناة {channel_id}: {e}")

async def stop_channel_internal(chat_id, context):
    async with channel_tasks_lock:
        task = channel_tasks.pop(chat_id, None)
    if task: task.cancel()
    async with channel_games_lock:
        channel_games.pop(chat_id, None)
    db.remove_active_channel(chat_id)

async def check_bot_permissions(chat_id, context):
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status == 'administrator': return bot_member.can_send_messages if hasattr(bot_member, 'can_send_messages') else True
        return True
    except tg_error.Forbidden:
        return False
    except Exception as e:
        logging.error(f"check_bot_permissions: {e}"); return False

# ─ـ البطولات ─ـ
async def create_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id): await update.message.reply_text("❌ مش مسموحلك."); return
    tourney_id = f"t_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    prize = int(context.args[0]) if context.args and context.args[0].isdigit() else 500
    db.create_tournament(tourney_id, prize)
    await update.message.reply_text(f"🏆 تم إنشاء بطولة جديدة!\nID: `{tourney_id}`\nالجائزة: {prize} نقطة\nالعدد المطلوب: 8 لاعبين\nاستخدم /join عشان تنضم!")

async def join_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    t = db.get_active_tournament()
    if not t: await update.message.reply_text("❌ مفيش بطولة مفتوحة حالياً."); return
    if db.join_tournament(t["tournament_id"], user.id):
        players = [p for p in t["players"].split(",") if p]
        await update.message.reply_text(f"✅ انضميت للبطولة! ({len(players)}/8)")
        if len(players) >= 8:
            t["status"] = "running"
            await start_tournament(t, context)
    else: await update.message.reply_text("❌ إما البطولة مقفولة أو انت مشترك بالفعل.")

async def start_tournament(t, context):
    players = [p for p in t["players"].split(",") if p]; random.shuffle(players)
    rounds = []; round1 = []
    for i in range(0,8,2):
        match = {"p1":players[i],"p2":players[i+1],"winner":None,"status":"pending"}
        round1.append(match)
        try:
            await context.bot.send_message(int(players[i]), f"🏆 مباراتك في البطولة ضد {db.get_user(int(players[i+1]))['name']}!")
            await context.bot.send_message(int(players[i+1]), f"🏆 مباراتك في البطولة ضد {db.get_user(int(players[i]))['name']}!")
            async with active_games_lock:
                game_id = f"t_{players[i]}_{players[i+1]}"
                active_games[game_id] = {"p1":int(players[i]),"p1_name":db.get_user(int(players[i]))["name"],
                                         "p2":int(players[i+1]),"p2_name":db.get_user(int(players[i+1]))["name"],
                                         "c1":None,"c2":None,"created_at":datetime.now(),"best_of":1,"p1_wins":0,"p2_wins":0,
                                         "tournament_match":True,"tournament_id":t["tournament_id"],"match_index":i//2}
            kb = mp_keyboard(game_id)
            await context.bot.send_message(int(players[i]), "اختار حركتك:", reply_markup=kb)
            await context.bot.send_message(int(players[i+1]), "اختار حركتك:", reply_markup=kb)
        except Exception as e: logging.error(f"خطأ بدء مباراة البطولة: {e}")
    rounds.append(round1)
    t["rounds"] = json.dumps(rounds)
    db.update_tournament(t["tournament_id"], rounds=t["rounds"], status="running")

async def handle_tournament_match_result(game, winner_id, context):
    t = db.get_tournament(game["tournament_id"])
    if not t or t["status"]!="running": return
    rounds = json.loads(t["rounds"])
    current_round = rounds[-1]; match = current_round[game["match_index"]]
    match["winner"] = str(winner_id); match["status"] = "finished"
    if all(m["status"]=="finished" for m in current_round):
        winners = [m["winner"] for m in current_round if m["winner"]]
        if len(winners)==1:
            t["winner_id"] = winners[0]; t["status"] = "finished"; prize = t["prize"]
            db.update_user(int(winners[0]), points=int(db.get_user(int(winners[0])).get("points",0))+prize, tournament_wins=int(db.get_user(int(winners[0])).get("tournament_wins",0))+1)
            try: await context.bot.send_message(int(winners[0]), f"🎉 مبروك! أنت بطل البطولة وكسبت {prize} نقطة!")
            except: pass
        else:
            next_round = []
            for i in range(0,len(winners),2):
                next_round.append({"p1":winners[i],"p2":winners[i+1],"winner":None,"status":"pending"})
                async with active_games_lock:
                    game_id = f"t_{winners[i]}_{winners[i+1]}"
                    active_games[game_id] = {"p1":int(winners[i]),"p1_name":db.get_user(int(winners[i]))["name"],
                                             "p2":int(winners[i+1]),"p2_name":db.get_user(int(winners[i+1]))["name"],
                                             "c1":None,"c2":None,"created_at":datetime.now(),"best_of":1,"p1_wins":0,"p2_wins":0,
                                             "tournament_match":True,"tournament_id":t["tournament_id"],"match_index":i//2}
                kb = mp_keyboard(game_id)
                await context.bot.send_message(int(winners[i]), "اختار حركتك للجولة القادمة:", reply_markup=kb)
                await context.bot.send_message(int(winners[i+1]), "اختار حركتك للجولة القادمة:", reply_markup=kb)
            rounds.append(next_round); t["rounds"] = json.dumps(rounds)
    db.update_tournament(t["tournament_id"], rounds=t["rounds"], status=t["status"], winner_id=t["winner_id"])

# ─ـ الأصدقاء ─ـ
async def handle_friend_request(update, context, action, from_id):
    user = update.effective_user
    if action == "accept":
        db.add_friend(user.id, int(from_id))
        db.remove_friend_request(user.id, int(from_id))
        await update.callback_query.answer("✅ تم قبول الصداقة!", show_alert=True)
    elif action == "reject":
        db.remove_friend_request(user.id, int(from_id))
        await update.callback_query.answer("❌ تم رفض الطلب.", show_alert=True)
    await show_friend_list(update, context)

async def show_friend_list(update, context):
    query = update.callback_query
    user = query.from_user
    friends = db.get_friends(user.id)
    requests = db.get_friend_requests(user.id)
    text = "👥 *قائمة الأصدقاء*\n\n"
    if friends:
        for fid in friends:
            fuser = db.get_user(int(fid))
            if fuser: text += f"• {fuser['name']}\n"
    else: text += "لا يوجد أصدقاء بعد.\n"
    if requests: text += f"\n📥 طلبات الصداقة ({len(requests)}):\n"
    btns = []
    if friends:
        for fid in friends:
            fuser = db.get_user(int(fid))
            if fuser: btns.append([InlineKeyboardButton(f"⚔️ تحدي {fuser['name']}", callback_data=f"friend_challenge_{fid}")])
    btns.append([InlineKeyboardButton("➕ إضافة صديق", callback_data="add_friend")])
    if requests: btns.append([InlineKeyboardButton("📥 عرض الطلبات", callback_data="view_requests")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

# ─ـ التحديات الجماعية ─ـ
async def group_challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ("supergroup", "group"): await update.message.reply_text("⚠️ الأمر ده للجروبات بس!"); return
    if not is_founder(user.id):
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ لازم تكون مشرف."); return
    args = context.args
    if len(args) < 2: await update.message.reply_text("استخدام: /groupchallenge <عدد_الانتصارات> <المدة_بالساعات> [الجائزة]"); return
    try: target_wins = int(args[0]); hours = int(args[1]); prize = int(args[2]) if len(args) > 2 else 500
    except: await update.message.reply_text("أرقام غير صحيحة."); return
    challenge_id = f"gc_{chat.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.create_group_challenge(challenge_id, chat.id, target_wins, prize, hours)
    await update.message.reply_text(f"🏆 تم بدء تحدي جماعي!\nالهدف: {target_wins} انتصارات\nالمدة: {hours} ساعة\nالجائزة: {prize} نقطة")

async def update_group_challenge(group_id, user_id, wins, context):
    challenge = db.get_active_group_challenge(group_id)
    if challenge:
        db.update_group_challenge_participant(challenge["challenge_id"], user_id, wins)
        if challenge["winner_id"]:
            winner_id = int(challenge["winner_id"])
            db.update_user(winner_id, points=int(db.get_user(winner_id).get("points",0)) + challenge["prize"])
            try:
                await context.bot.send_message(
                    group_id,
                    f"🎉 {db.get_user(winner_id)['name']} فاز بالتحدي الجماعي وحصل على {challenge['prize']} نقطة!"
                )
            except Exception as e:
                logging.error(f"فشل إرسال إشعار فوز تحدي جماعي: {e}")

# ─ـ الألقاب والثيمات ─ـ
async def titles_shop_handler(update, context):
    query = update.callback_query
    titles = db.get_titles_shop()
    u = db.get_user(query.from_user.id)
    gems = u.get("gems", 0)
    text = f"🏅 *متجر الألقاب*\n💎 جواهرك: {gems}\n\n"
    btns = []
    for t in titles:
        owned = (u.get("title") == t["title_id"])
        if owned: text += f"✅ {t['name']} - {t['description']}\n"
        else: text += f"🔒 {t['name']} - {t['description']} ({t['cost_gems']} جوهرة)\n"; btns.append([InlineKeyboardButton(f"شراء {t['name']} ({t['cost_gems']}💎)", callback_data=f"buytitle_{t['title_id']}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

async def buy_title_handler(update, context, title_id):
    query = update.callback_query; user = query.from_user
    u = db.get_user(user.id)
    titles = db.get_titles_shop()
    title = next((t for t in titles if t["title_id"] == title_id), None)
    if not title: await query.answer("لقب غير موجود", show_alert=True); return
    if u.get("gems", 0) < title["cost_gems"]: await query.answer("جواهر غير كافية", show_alert=True); return
    db.update_user(user.id, gems=u["gems"] - title["cost_gems"], title=title_id)
    await query.answer(f"اشتريت لقب {title['name']}!", show_alert=True)

async def themes_shop_handler(update, context):
    query = update.callback_query
    themes = db.get_themes_shop()
    u = db.get_user(query.from_user.id)
    gems = u.get("gems", 0)
    text = f"🎨 *متجر الثيمات*\n💎 جواهرك: {gems}\n\n"
    btns = []
    for th in themes:
        owned = (u.get("theme") == th["theme_id"])
        if owned: text += f"✅ {th['name']} - {th['description']}\n"
        else: text += f"🔒 {th['name']} - {th['description']} ({th['cost_gems']} جوهرة)\n"; btns.append([InlineKeyboardButton(f"شراء {th['name']} ({th['cost_gems']}💎)", callback_data=f"buytheme_{th['theme_id']}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

async def buy_theme_handler(update, context, theme_id):
    query = update.callback_query; user = query.from_user
    u = db.get_user(user.id)
    themes = db.get_themes_shop()
    theme = next((t for t in themes if t["theme_id"] == theme_id), None)
    if not theme: await query.answer("ثيم غير موجود", show_alert=True); return
    if u.get("gems", 0) < theme["cost_gems"]: await query.answer("جواهر غير كافية", show_alert=True); return
    db.update_user(user.id, gems=u["gems"] - theme["cost_gems"], theme=theme_id)
    await query.answer(f"اشتريت ثيم {theme['name']}!", show_alert=True)

# ─ـ صندوق الغنائم ─ـ
async def open_loot_box(update, context):
    query = update.callback_query; user = query.from_user
    u = db.get_user(user.id)
    owned = [o for o in (u.get("shop_items", "") or "").split(",") if o]
    if "item_6" not in owned: await query.answer("❌ ما عندكش صندوق كنز.", show_alert=True); return
    owned.remove("item_6")
    db.update_user(user.id, shop_items=",".join(owned))
    roll = random.random()
    if roll < 0.5:
        points_won = random.randint(500, 1500)
        db.update_user(user.id, points=int(u.get("points",0)) + points_won)
        msg = f"🎁 فتحت صندوق الكنز وكسبت {points_won} نقطة!"
    elif roll < 0.8:
        all_items = db.get_shop_items()
        cards = [i for i in all_items if i["item_id"] != "item_6"]
        if cards:
            chosen = random.choice(cards)
            new_owned = [o for o in (u.get("shop_items", "") or "").split(",") if o] + [chosen["item_id"]]
            db.update_user(user.id, shop_items=",".join(new_owned))
            msg = f"🎁 فتحت صندوق الكنز وحصلت على {chosen['emoji']} *{chosen['name']}*!"
        else:
            points_won = random.randint(500, 1500)
            db.update_user(user.id, points=int(u.get("points",0)) + points_won)
            msg = f"🎁 فتحت صندوق الكنز وكسبت {points_won} نقطة!"
    else:
        gems_won = random.randint(1, 5)
        db.update_user(user.id, gems=int(u.get("gems",0)) + gems_won)
        msg = f"🎁 فتحت صندوق الكنز وكسبت {gems_won} جوهرة 💎!"
    await query.answer(msg, show_alert=True)
    await show_my_items(update, context)

async def show_my_items(update, context):
    query = update.callback_query; user = query.from_user
    u = db.get_user(user.id)
    owned = [o for o in (u.get("shop_items", "") or "").split(",") if o]
    items = db.get_shop_items()
    counts = {}
    for o in owned: counts[o] = counts.get(o, 0) + 1
    text = "🎒 *بطاقاتي*\n\n"
    if not owned: text += "ما عندكش بطاقات."
    else:
        for item_id, count in counts.items():
            item = next((i for i in items if i["item_id"] == item_id), None)
            if item: text += f"{item['emoji']} *{item['name']}* (x{count})\n"
    btns = []
    if owned:
        for item_id in set(owned):
            item = next((i for i in items if i["item_id"] == item_id), None)
            if item:
                if item_id == "item_6": btns.append([InlineKeyboardButton(f"🎁 فتح صندوق الكنز", callback_data="open_box")])
                else: btns.append([InlineKeyboardButton(f"استخدام {item['name']}", callback_data=f"use_{item_id}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

# ─ـ الأحداث الموسمية ─ـ
async def event_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ev = db.get_active_event()
    if not ev: await update.message.reply_text("لا يوجد حدث حالي."); return
    tasks_str = ""
    if ev["special_tasks"]:
        for t in ev["special_tasks"]: tasks_str += f"• {t['description']} — {t['reward']} نقطة\n"
    text = f"🎉 *الحدث الحالي: {ev['name']}*\nينتهي: {ev['end_date']}\n\n🎯 *مهام خاصة:*\n{tasks_str}"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─ـ حرب العشائر ─ـ
async def clan_war_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    war = db.get_active_clan_war()
    if not war: await update.message.reply_text("لا توجد حرب عشائر حالية."); return
    cp = json.loads(war["clan_points"])
    sorted_clans = sorted(cp.items(), key=lambda x: x[1], reverse=True)
    text = "⚔️ *حرب العشائر*\n\n"
    for i, (clan, pts) in enumerate(sorted_clans[:10], 1): text += f"{i}. {clan}: {pts} نقطة\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def start_clan_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id): await update.message.reply_text("❌ غير مسموح."); return
    days = int(context.args[0]) if context.args else 7
    war = db.create_clan_war(duration_days=days)
    await update.message.reply_text(f"⚔️ بدأت حرب العشائر! تنتهي بعد {days} يوم.")

async def end_war_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_founder(update.effective_user.id): await update.message.reply_text("❌ غير مسموح."); return
    war = db.get_active_clan_war()
    if not war: await update.message.reply_text("لا توجد حرب نشطة."); return
    db.end_clan_war(war["war_id"])
    await update.message.reply_text(f"🏆 انتهت حرب العشائر! العشيرة الفائزة: {war.get('winner_clan','?')}")

# ─ـ وضع القصة ─ـ
async def story_mode_handler(update, context):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    level = u.get("story_level", 1)
    boss = STORY_LEVELS.get(level)
    if not boss:
        await query.edit_message_text("🎉 لقد أكملت كل المستويات!")
        return
    text = f"📖 *المستوى {level}*\n\n{boss['story']}\nالزعيم: {boss['emoji']} *{boss['boss']}*\nاختار حركتك:"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=solo_keyboard(user.id))
    context.user_data["in_story_mode"] = True

# ─ـ Spock ─ـ
async def play_spock_handler(update, context):
    query = update.callback_query
    choices = CHOICES_SPOCK
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=f"spock_{k}") for k,v in choices.items()]])
    await query.edit_message_text("🖖 اختار حركتك (Spock):", reply_markup=kb)

async def handle_spock_choice(update, context, choice):
    query = update.callback_query; user = query.from_user
    bot_choice = random.choice(list(CHOICES_SPOCK.keys()))
    if choice == bot_choice: result = "draw"
    elif bot_choice in WIN_MAP_SPOCK[choice]: result = "win"
    else: result = "loss"
    u = db.get_user(user.id)
    pts = int(u.get("points",0) or 0)
    if result == "win": pts_add = 10; wins = int(u.get("wins",0))+1; losses = int(u.get("losses",0)); draws = int(u.get("draws",0))
    elif result == "loss": pts_add = -3; wins = int(u.get("wins",0)); losses = int(u.get("losses",0))+1; draws = int(u.get("draws",0))
    else: pts_add = 5; wins = int(u.get("wins",0)); losses = int(u.get("losses",0)); draws = int(u.get("draws",0))+1
    pts = max(0, pts+pts_add)
    db.update_user(user.id, points=pts, wins=wins, losses=losses, draws=draws)
    await query.edit_message_text(
        f"انت: {CHOICES_SPOCK[choice]}\nالبوت: {CHOICES_SPOCK[bot_choice]}\n\n"
        f"{'🎉 كسبت!' if result=='win' else '😢 خسرت!' if result=='loss' else '🤝 تعادل!'} ({'+' if pts_add>=0 else ''}{pts_add} نقطة)\n💰 نقاطك: {pts}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 العب تاني", callback_data="play_spock")], [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]])
    )

# ─ـ الذكاء الاصطناعي ─ـ
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
    return random.choice(list(CHOICES.keys()))

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

# ─ـ الأوامر الأساسية ─ـ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_bonus = False
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_id = arg.replace("ref_", "")
            if ref_id.isdigit():
                existing = db.get_user(user.id)
                if not existing and str(user.id) != ref_id:
                    referrer = db.get_user(int(ref_id))
                    if referrer and not db.has_been_referred(user.id):
                        pts = int(referrer.get("points", 0) or 0)
                        db.update_user(int(ref_id), points=pts + DAILY_REFERRAL_POINTS)
                        db.mark_referred(user.id)
                        ref_bonus = True
                        try: await context.bot.send_message(int(ref_id), f"🎁 المستخدم *{user.first_name}* دخل عن طريق رابط الدعوة بتاعك! تم إضافة {DAILY_REFERRAL_POINTS} نقطة لك.", parse_mode="Markdown")
                        except Exception as e: logging.error(f"فشل إرسال إشعار الإحالة: {e}")
        elif arg.startswith("challenge_"):
            async with active_games_lock:
                game_id = arg.replace("challenge_", "")
                game = active_games.get(game_id)
            if not game: await update.message.reply_text("❌ التحدي انتهى أو لم يعد موجوداً."); return
            if game["p1"] == user.id: await update.message.reply_text("❌ لا يمكنك قبول تحدي نفسك!"); return
            if game["p2"] is not None: await update.message.reply_text("❌ هذا التحدي ممتلئ بالفعل!"); return
            async with active_games_lock:
                game["p2"] = user.id; game["p2_name"] = user.first_name
            db.get_or_create_user(user.id, user.first_name, user.username)
            await update.message.reply_text(f"✅ تم قبول التحدي! ⚔️ *{game['p1_name']}* vs *{user.first_name}*", parse_mode="Markdown")
            kb = mp_keyboard(game_id)
            await context.bot.send_message(game["p1"], "اللعبة بدأت! اختار حركتك 👇", reply_markup=kb)
            await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)
            return
        elif arg.startswith("joinclan_"):
            clan_name = arg.replace("joinclan_", "")
            clan = db.get_clan(clan_name)
            if not clan: await update.message.reply_text("❌ العشيرة غير موجودة."); return
            u = db.get_user(user.id)
            if not u: db.get_or_create_user(user.id, user.first_name, user.username); u = db.get_user(user.id)
            if u.get("clan"): await update.message.reply_text("❌ أنت بالفعل في عشيرة أخرى."); return
            members = [m for m in str(clan.get("members","")).split(",") if m]
            if str(user.id) in members: await update.message.reply_text("❌ أنت بالفعل عضو."); return
            members.append(str(user.id))
            db.update_clan(clan_name, members=",".join(members))
            db.update_user(user.id, clan=clan_name)
            await update.message.reply_text(f"✅ انضممت إلى عشيرة *{clan_name}*!", parse_mode="Markdown")
            return

    db.get_or_create_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    if db.is_banned(user.id): await update.message.reply_text("🚫 أنت محظور من استخدام البوت."); return
    points = int(u.get("points", 0))
    leaderboard = db.get_leaderboard(100)
    rank = next((i+1 for i,p in enumerate(leaderboard) if str(p["user_id"])==str(user.id)), "غير مصنف")
    text = (f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇")
    if ref_bonus: text += "\n\n🎁 تم منح صاحبك 1000 نقطة على دعوتك!"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u: return
    all_achs = db.get_achievements()
    earned = [a for a in u.get("achievements","").split(",") if a]
    text = "🎖️ *قائمة الإنجازات:*\n\n"
    for ach in all_achs:
        status = "✅" if ach["ach_id"] in earned else "🔒"
        text += f"{status} {ach['icon']} *{ach['name']}* - {ach['description']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def activate_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("supergroup", "group"): await update.message.reply_text("⚠️ الأمر ده للجروبات بس!"); return
    channel_id = chat.id
    has_perm = await check_bot_permissions(channel_id, context)
    if not has_perm: await update.message.reply_text("❌ البوت مش قادر يبعت رسايل..."); return
    await stop_channel_internal(channel_id, context)
    db.add_active_channel(channel_id, chat.title or "جروب")
    channel_last_play[channel_id] = datetime.now()
    async with channel_tasks_lock:
        task = asyncio.create_task(channel_loop(channel_id, context))
        channel_tasks[channel_id] = task
    await update.message.reply_text("✅ تم تفعيل اللعب التلقائي!\nكل دقيقتين هتظهر لعبة جديدة بين عضوين 🎮")

async def stop_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("supergroup", "group"): await update.message.reply_text("⚠️ الأمر ده للجروبات بس!"); return
    channel_id = chat.id
    async with channel_tasks_lock:
        if channel_id in channel_tasks: await stop_channel_internal(channel_id, context)
        else: await update.message.reply_text("ℹ️ الجروب مش مفعّل أصلاً."); return
    await update.message.reply_text("✅ تم إيقاف اللعب التلقائي.")

# ─ـ معالج الأزرار ─ـ
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; user = query.from_user
    db.get_or_create_user(user.id, user.first_name, user.username)
    if db.is_banned(user.id): await query.edit_message_text("🚫 أنت محظور."); return
    u = db.get_user(user.id)

    if data == "menu_main":
        points = int(u.get("points",0)) if u else 0; leaderboard = db.get_leaderboard(100)
        rank = next((i+1 for i,p in enumerate(leaderboard) if str(p["user_id"])==str(user.id)), "غير مصنف")
        await query.edit_message_text(f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇", parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))
    elif data == "daily_bonus":
        msg = await claim_daily(user.id, context)
        await query.answer(msg, show_alert=True); await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user.id))
    elif data == "menu_play": await query.edit_message_text("🎮 اختار نوع اللعب:", reply_markup=play_menu_keyboard())

    # فردي
    elif data == "play_solo": await query.edit_message_text("🤖 اختار حركتك:", reply_markup=solo_keyboard(user.id))
    elif data.startswith("solo_"):
        choice = data.replace("solo_", ""); bot_choice = smart_bot_choice(user.id)
        result = get_result(choice, bot_choice)
        u = db.get_user(user.id)
        pts = int(u.get("points",0) or 0); wins = int(u.get("wins",0) or 0); losses = int(u.get("losses",0) or 0); draws = int(u.get("draws",0) or 0)
        solo_games = int(u.get("solo_games",0)) + 1
        rock_used = int(u.get("rock_used",0)) + (1 if choice=="rock" else 0)
        paper_used = int(u.get("paper_used",0)) + (1 if choice=="paper" else 0)
        scissors_used = int(u.get("scissors_used",0)) + (1 if choice=="scissors" else 0)
        if result == "win":
            emoji, txt, pts_add = "🎉", "كسبت!", WIN_POINTS_SOLO
            wins += 1; win_streak = int(u.get("win_streak",0))+1
            add_clan_points(user.id, 3)
            await check_and_complete_task(user.id, "task_1", context)
            await check_and_complete_task(user.id, "task_2", context, 1)
        elif result == "loss":
            emoji, txt, pts_add = "😢", "خسرت!", LOSS_POINTS_SOLO
            losses += 1; win_streak = 0
        else:
            emoji, txt, pts_add = "🤝", "تعادل!", DRAW_POINTS_SOLO
            draws += 1; win_streak = int(u.get("win_streak",0))
            add_clan_points(user.id, 1)
        pts = max(0, pts+pts_add)
        db.update_user(user.id, points=pts, wins=wins, losses=losses, draws=draws, solo_games=solo_games,
                       rock_used=rock_used, paper_used=paper_used, scissors_used=scissors_used, win_streak=win_streak)
        update_user_moves(user.id, choice); await check_achievements(user.id, context)
        await query.edit_message_text(
            f"انت: {get_choices_for_user(user.id)[choice]}\nالبوت: {get_choices_for_user(user.id)[bot_choice]}\n\n"
            f"{emoji} *{txt}*  ({'+' if pts_add>=0 else ''}{pts_add} نقطة)\n💰 نقاطك: {pts}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 العب تاني", callback_data="play_solo")],
                [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]
            ])
        )

    # صديق (اختيار الوضع)
    elif data == "play_friend":
        await query.edit_message_text("اختار نوع التحدي:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ جولة واحدة", callback_data="friend_bo1")],
                [InlineKeyboardButton("🔥 أفضل من 3", callback_data="friend_bo3")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_play")]
            ]))
    elif data in ("friend_bo1", "friend_bo3"):
        best_of = 1 if data=="friend_bo1" else 3; context.user_data["friend_best_of"] = best_of
        await query.edit_message_text("📩 ابعت يوزر صديقك (@username) أو الـ ID بتاعه:", reply_markup=back_btn("menu_play"))
        context.user_data["awaiting"] = "friend_challenge"; context.user_data["awaiting_time"] = datetime.now()

    # قبول تحدي
    elif data.startswith("join_"):
        async with active_games_lock:
            game_id = data.replace("join_", ""); game = active_games.get(game_id)
            if not game: await query.edit_message_text("❌ التحدي انتهى."); return
            if game["p1"] == user.id: await query.answer("❌ مش ممكن تقبل تحدي نفسك!", show_alert=True); return
            if game["p2"] is not None: await query.answer("❌ التحدي ممتلئ!", show_alert=True); return
            game["p2"] = user.id; game["p2_name"] = user.first_name
        db.get_or_create_user(user.id, user.first_name, user.username)
        await query.edit_message_text(f"⚔️ *{game['p1_name']}* vs *{user.first_name}*\nاللعبة بدأت!", parse_mode="Markdown")
        kb = mp_keyboard(game_id)
        await context.bot.send_message(game["p1"], "اختار حركتك 👇", reply_markup=kb)
        await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)

    # متعددة
    elif data.startswith("mp_"):
        parts = data.split("_"); choice = parts[-1]; game_id = "_".join(parts[1:-1])
        async with active_games_lock:
            game = active_games.get(game_id)
            if not game: await query.edit_message_text("❌ اللعبة انتهت."); return
            if user.id == game["p1"] and not game["c1"]: game["c1"] = choice; await query.edit_message_text("✅ اخترت! استنى...")
            elif user.id == game["p2"] and not game["c2"]: game["c2"] = choice; await query.edit_message_text("✅ اخترت! استنى...")
            else: return
            if game["c1"] and game["c2"]:
                c1, c2 = game["c1"], game["c2"]; result = get_result(c1, c2)
                summary = f"⚔️ *النتيجة*\n\n{game['p1_name']}: {CHOICES[c1]}\n{game['p2_name']}: {CHOICES[c2]}\n\n"
                u1 = db.get_user(game["p1"]); u2 = db.get_user(game["p2"])
                if result == "win":
                    p1_add, p2_add = ROUND_WIN_POINTS, ROUND_LOSS_POINTS
                    game["p1_wins"] = game.get("p1_wins",0)+1; r1, r2 = "🎉 كسب الجولة!", "😢 خسر الجولة!"
                    add_clan_points(game["p1"], 2)
                elif result == "loss":
                    p1_add, p2_add = ROUND_LOSS_POINTS, ROUND_WIN_POINTS
                    game["p2_wins"] = game.get("p2_wins",0)+1; r1, r2 = "😢 خسر الجولة!", "🎉 كسب الجولة!"
                    add_clan_points(game["p2"], 2)
                else:
                    p1_add = p2_add = ROUND_DRAW_POINTS; r1 = r2 = "🤝 تعادل الجولة!"
                db.update_user(game["p1"], points=max(0, int(u1.get("points",0))+p1_add))
                db.update_user(game["p2"], points=max(0, int(u2.get("points",0))+p2_add))
                required_wins = (game.get("best_of",1)+1)//2
                if game.get("p1_wins",0) >= required_wins or game.get("p2_wins",0) >= required_wins:
                    winner_id = game["p1"] if game["p1_wins"] >= required_wins else game["p2"]
                    loser_id = game["p2"] if winner_id == game["p1"] else game["p1"]
                    db.update_user(winner_id, points=int(db.get_user(winner_id).get("points",0))+WIN_POINTS_MULTI, wins=int(db.get_user(winner_id).get("wins",0))+1)
                    db.update_user(loser_id, points=max(0, int(db.get_user(loser_id).get("points",0)))+LOSS_POINTS_MULTI, losses=int(db.get_user(loser_id).get("losses",0))+1)
                    add_clan_points(winner_id, 5); await check_and_complete_task(winner_id, "task_3", context)
                    if game.get("game_type")=="friend":
                        db.update_user(game["p1"], friend_games=int(u1.get("friend_games",0))+1)
                        db.update_user(game["p2"], friend_games=int(u2.get("friend_games",0))+1)
                    elif game.get("game_type")=="random":
                        db.update_user(game["p1"], random_games=int(u1.get("random_games",0))+1)
                        db.update_user(game["p2"], random_games=int(u2.get("random_games",0))+1)
                    if game.get("best_of")==3:
                        db.update_user(winner_id, bo3_wins=int(db.get_user(winner_id).get("bo3_wins",0))+1)
                        db.update_user(loser_id, bo3_losses=int(db.get_user(loser_id).get("bo3_losses",0))+1)
                    if game.get("tournament_match"): await handle_tournament_match_result(game, winner_id, context)
                    final_msg = f"🏆 *الماتش انتهى!*\nالنتيجة النهائية: {game['p1_wins']} - {game['p2_wins']}\nالفائز: {db.get_user(winner_id)['name']} (+{WIN_POINTS_MULTI} نقطة)"
                    await context.bot.send_message(game["p1"], final_msg, parse_mode="Markdown")
                    await context.bot.send_message(game["p2"], final_msg, parse_mode="Markdown")
                    del active_games[game_id]
                else:
                    game["c1"] = None; game["c2"] = None; kb = mp_keyboard(game_id)
                    round_msg = f"الجولة القادمة! النتيجة: {game['p1_wins']} - {game['p2_wins']}"
                    await context.bot.send_message(game["p1"], round_msg, reply_markup=kb)
                    await context.bot.send_message(game["p2"], round_msg, reply_markup=kb)

    # عشوائي
    elif data == "play_random":
        async with pending_matches_lock:
            if any(m["id"]==user.id for m in pending_matches): await query.answer("أنت بالفعل في قائمة الانتظار!", show_alert=True); return
            if pending_matches:
                opponent = pending_matches.pop(0)
                async with active_games_lock:
                    game_id = f"r_{user.id}_{random.randint(1000,9999)}"
                    active_games[game_id] = {"p1":opponent["id"],"p1_name":opponent["name"],"p2":user.id,"p2_name":user.first_name,"c1":None,"c2":None,"created_at":datetime.now(),"best_of":1,"p1_wins":0,"p2_wins":0,"game_type":"random"}
                asyncio.create_task(game_timeout(game_id, context))
                kb = mp_keyboard(game_id)
                await query.edit_message_text(f"✅ لاقيت خصم: *{opponent['name']}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
                await context.bot.send_message(opponent["id"], f"✅ لاقيت خصم: *{user.first_name}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
            else:
                pending_matches.append({"id":user.id,"name":user.first_name})
                await query.edit_message_text("🔍 بندور على خصم... استنى!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_random")]]))
    elif data == "cancel_random":
        async with pending_matches_lock:
            pending_matches[:] = [m for m in pending_matches if m["id"]!=user.id]
        await query.edit_message_text("✅ تم الإلغاء.", reply_markup=main_menu_keyboard(user.id))

    # القناة (PvP)
    elif data.startswith("ch_"):
        parts = data.split("_", 2); channel_id = int(parts[1]); choice = parts[2]
        async with channel_games_lock:
            game = channel_games.get(channel_id)
            if not game: await query.answer("❌ انتهت الجولة.", show_alert=True); return
            if user.id == game.get("player1") or user.id == game.get("player2"): await query.answer("❌ انت لعبت خلاص!", show_alert=True); return
            if game["player1"] is None:
                game["player1"] = user.id; game["choice1"] = choice
                await query.answer("✅ انت اللاعب الأول! استنى الخصم", show_alert=True)
                try: await context.bot.edit_message_text(chat_id=channel_id, message_id=game["message_id"], text=f"🎮 *{user.first_name}* دخل اللعبة! في انتظار لاعب تاني يضغط...", parse_mode="Markdown", reply_markup=channel_keyboard(channel_id))
                except Exception as e: logging.error(f"فشل تعديل رسالة القناة: {e}")
            elif game["player2"] is None and game["player1"] != user.id:
                game["player2"] = user.id; game["choice2"] = choice
                p1 = db.get_user(game["player1"]); p2 = db.get_user(user.id)
                if not p1 or not p2: await cancel_channel_game(channel_id, context, "خطأ في بيانات اللاعبين"); return
                result = get_result(game["choice1"], game["choice2"]); c1_name, c2_name = CHOICES[game["choice1"]], CHOICES[game["choice2"]]
                if result == "win":
                    p1_add, p2_add = WIN_POINTS_MULTI, LOSS_POINTS_MULTI
                    db.update_user(game["player1"], points=max(0,int(p1.get("points",0))+p1_add), wins=int(p1.get("wins",0))+1)
                    db.update_user(game["player2"], points=max(0,int(p2.get("points",0))+p2_add), losses=int(p2.get("losses",0))+1)
                    add_clan_points(game["player1"], 5); result_text = f"{p1['name']} كسب {p2['name']}!"
                elif result == "loss":
                    p1_add, p2_add = LOSS_POINTS_MULTI, WIN_POINTS_MULTI
                    db.update_user(game["player1"], points=max(0,int(p1.get("points",0))+p1_add), losses=int(p1.get("losses",0))+1)
                    db.update_user(game["player2"], points=max(0,int(p2.get("points",0))+p2_add), wins=int(p2.get("wins",0))+1)
                    add_clan_points(game["player2"], 5); result_text = f"{p2['name']} كسب {p1['name']}!"
                else:
                    p1_add = p2_add = DRAW_POINTS_SOLO
                    db.update_user(game["player1"], points=int(p1.get("points",0))+5, draws=int(p1.get("draws",0))+1)
                    db.update_user(game["player2"], points=int(p2.get("points",0))+5, draws=int(p2.get("draws",0))+1)
                    add_clan_points(game["player1"], 2); add_clan_points(game["player2"], 2); result_text = "تعادل!"
                db.update_user(game["player1"], channel_games=int(p1.get("channel_games",0))+1)
                db.update_user(game["player2"], channel_games=int(p2.get("channel_games",0))+1)
                await update_group_challenge(channel_id, game["player1"], int(p1.get("wins",0)), context)
                await update_group_challenge(channel_id, game["player2"], int(p2.get("wins",0)), context)
                await check_achievements(game["player1"], context); await check_achievements(game["player2"], context)
                final_text = f"⚔️ *النتيجة*\n\n{p1['name']}: {c1_name}\n{p2['name']}: {c2_name}\n\n🏆 {result_text}\n💰 {p1['name']}: {'+' if p1_add>=0 else ''}{p1_add} نقطة | {p2['name']}: {'+' if p2_add>=0 else ''}{p2_add} نقطة"
                try: await context.bot.edit_message_text(chat_id=channel_id, message_id=game["message_id"], text=final_text, parse_mode="Markdown")
                except Exception as e: logging.error(f"فشل عرض نتيجة القناة: {e}")
                del channel_games[channel_id]
            else: await query.answer("❌ اللعبة اكتملت خلاص", show_alert=True)

    # قسم القنوات (معلومات)
    elif data == "play_channel":
        channels = db.get_active_channels()
        bot_username = context.bot.username
        text = "📺 *اللعب في القنوات والجروبات*\n\n"
        if channels:
            text += "الجروبات النشطة الآن:\n"
            for ch in channels: text += f"• {ch['title']}\n"
            text += "\n"
        text += (f"عشان تفعّل البوت في جروبك:\n1️⃣ أضف البوت للجروب\n2️⃣ اعمله Admin\n3️⃣ ابعت /activate في الجروب\n\n🔗 لينك البوت: @{bot_username}")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_play"))

    # التصنيف
    elif data == "menu_rank":
        await query.edit_message_text("🏆 اختار نوع التصنيف:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 يومي", callback_data="rank_daily"), InlineKeyboardButton("📆 أسبوعي", callback_data="rank_weekly")],
                [InlineKeyboardButton("🗓️ شهري", callback_data="rank_monthly"), InlineKeyboardButton("📊 إجمالي", callback_data="rank_all")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
            ]))
    elif data.startswith("rank_"):
        period = data.replace("rank_","")
        period_names = {"daily":"اليومي","weekly":"الأسبوعي","monthly":"الشهري","all":"الإجمالي"}
        lb = db.get_leaderboard(10, period)
        medals = ["🥇","🥈","🥉"]
        text = f"🏆 *التصنيف {period_names.get(period,'')}*\n\n"
        for i, u in enumerate(lb):
            medal = medals[i] if i<3 else f"{i+1}."
            text += f"{medal} *{u['name']}* — {u.get('points',0)} نقطة\n"
        if not lb: text += "مفيش لاعبين لسه!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_rank"))

    # الملف الشخصي
    elif data == "menu_profile":
        u = db.get_user(user.id)
        total = int(u.get("wins",0)) + int(u.get("losses",0)) + int(u.get("draws",0))
        wr = round(int(u.get("wins",0))/total*100,1) if total>0 else 0
        clan = u.get("clan","") or "بدون عشيرة"
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        text = (f"👤 *ملفك الشخصي*\n\nالاسم: {u['name']}\n💰 النقاط: {u.get('points',0)}\n💎 الجواهر: {u.get('gems',0)}\n"
                f"🗡️ العشيرة: {clan}\n✅ انتصارات: {u.get('wins',0)}\n❌ خسارات: {u.get('losses',0)}\n🤝 تعادل: {u.get('draws',0)}\n"
                f"📈 نسبة الفوز: {wr}%\n🎯 إجمالي: {total}\n\n🔗 رابط دعوتك:\n`{ref_link}`")
        achievements_str = u.get("achievements","")
        earned_ach_ids = [a for a in achievements_str.split(",") if a] if achievements_str else []
        all_achs = db.get_achievements()
        earned_achs = [a for a in all_achs if a["ach_id"] in earned_ach_ids]
        ach_text = "\n🎖️ *الإنجازات:*\n"
        if earned_achs:
            for a in earned_achs[:12]: ach_text += f"{a['icon']} {a['name']}\n"
        else: ach_text += "لا توجد بعد.\n"
        text += ach_text
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # الإحالة
    elif data == "menu_referral":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        refs = int(u.get("referrals",0) or 0)
        text = f"🔗 *رابط الدعوة بتاعك*\n\n`{ref_link}`\n\n👥 عدد من دعوتهم: {refs}\n💰 مكافأة كل دعوة: 1000 نقطة\n\nابعت الرابط لأصحابك وكسب نقاط!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # المهام
    elif data == "menu_tasks":
        tasks = db.get_tasks("daily")
        text = "🎁 *المهام اليومية*\n\n"
        u_progress = {}
        progress_str = (db.get_user(user.id) or {}).get("tasks_progress")
        if progress_str:
            try: u_progress = json.loads(progress_str).get("tasks",{})
            except: pass
        for t in tasks:
            task_id = t["task_id"]
            done = u_progress.get(f"{task_id}_done", False)
            current = u_progress.get(task_id, 0)
            target = {"task_1":5,"task_2":3,"task_3":1,"task_4":1,"task_5":10}.get(task_id,1)
            status = "✅ تم" if done else f"⏳ {current}/{target}"
            text += f"• {t['description']} — 💰 {t['points_reward']} نقطة | {status}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # المتجر
    elif data == "menu_shop":
        await query.edit_message_text("🛒 *المتجر*\nاختار:", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 المتجر (بطاقات)", callback_data="shop_buy")],
                [InlineKeyboardButton("🎒 بطاقاتي", callback_data="shop_myitems")],
                [InlineKeyboardButton("🏅 متجر الألقاب", callback_data="titles_shop")],
                [InlineKeyboardButton("🎨 متجر الثيمات", callback_data="themes_shop")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
            ]))
    elif data == "shop_buy":
        items = db.get_shop_items()
        pts = int(u.get("points",0) or 0)
        text = f"🛒 *المتجر*\n💰 نقاطك: {pts}\n\n"
        btns = []
        for item in items:
            text += f"{item['emoji']} *{item['name']}* — {item['price']} نقطة\n_{item['description']}_\n\n"
            btns.append([InlineKeyboardButton(f"{item['emoji']} {item['name']} ({item['price']} نقطة)", callback_data=f"buy_{item['item_id']}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "shop_myitems":
        await show_my_items(update, context)
    elif data.startswith("buy_"):
        item_id = data.replace("buy_","")
        items = db.get_shop_items()
        item = next((i for i in items if i["item_id"]==item_id), None)
        if not item: await query.answer("❌ المنتج مش موجود!", show_alert=True); return
        pts = int(u.get("points",0) or 0)
        price = int(item["price"])
        if pts < price: await query.answer(f"❌ نقاطك مش كفاية! محتاج {price} نقطة.", show_alert=True); return
        owned = [o for o in (u.get("shop_items","") or "").split(",") if o]
        owned.append(item_id)
        db.update_user(user.id, points=pts-price, shop_items=",".join(owned))
        await query.answer(f"✅ اشتريت {item['name']}!", show_alert=False)
    elif data.startswith("use_"):
        item_id = data.replace("use_","")
        owned = [o for o in (u.get("shop_items","") or "").split(",") if o]
        if item_id not in owned: await query.answer("❌ معندكش البطاقة دي!", show_alert=True); return
        owned.remove(item_id)
        db.update_user(user.id, shop_items=",".join(owned))
        item = next((i for i in db.get_shop_items() if i["item_id"]==item_id), None)
        await query.answer(f"✅ تم استخدام {item['name']}!" if item else "✅ تم استخدام البطاقة!", show_alert=False)

    # الألقاب والثيمات
    elif data == "titles_shop": await titles_shop_handler(update, context)
    elif data.startswith("buytitle_"): await buy_title_handler(update, context, data.replace("buytitle_",""))
    elif data == "themes_shop": await themes_shop_handler(update, context)
    elif data.startswith("buytheme_"): await buy_theme_handler(update, context, data.replace("buytheme_",""))
    elif data == "open_box": await open_loot_box(update, context)

    # الأصدقاء
    elif data == "menu_friends": await show_friend_list(update, context)
    elif data == "add_friend":
        await query.edit_message_text("📩 ابعت يوزر أو ID الصديق:", reply_markup=back_btn("menu_friends"))
        context.user_data["awaiting"] = "add_friend"; context.user_data["awaiting_time"] = datetime.now()
    elif data == "view_requests":
        requests = db.get_friend_requests(user.id)
        if not requests: await query.answer("لا توجد طلبات.", show_alert=True); return
        text = "📥 *طلبات الصداقة:*\n\n"
        btns = []
        for req in requests:
            text += f"• {req['name']}\n"
            btns.append([InlineKeyboardButton(f"✅ قبول {req['name']}", callback_data=f"accept_friend_{req['from']}"),
                         InlineKeyboardButton(f"❌ رفض {req['name']}", callback_data=f"reject_friend_{req['from']}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_friends")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    elif data.startswith("accept_friend_"): await handle_friend_request(update, context, "accept", data.replace("accept_friend_",""))
    elif data.startswith("reject_friend_"): await handle_friend_request(update, context, "reject", data.replace("reject_friend_",""))
    elif data.startswith("friend_challenge_"):
        friend_id = int(data.replace("friend_challenge_",""))
        context.user_data["challenge_target"] = friend_id
        await query.edit_message_text("اختار نوع التحدي:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ جولة واحدة", callback_data="quick_bo1")],
                [InlineKeyboardButton("🔥 أفضل من 3", callback_data="quick_bo3")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_friends")]
            ]))
    elif data in ("quick_bo1","quick_bo3"):
        best_of = 1 if data=="quick_bo1" else 3
        friend_id = context.user_data.get("challenge_target")
        if not friend_id: await query.answer("❌ انتهت الجلسة.", show_alert=True); return
        async with active_games_lock:
            game_id = f"f_{user.id}_{random.randint(1000,9999)}"
            active_games[game_id] = {"p1":user.id,"p1_name":user.first_name,"p2":friend_id,"p2_name":db.get_user(friend_id)["name"],
                                     "c1":None,"c2":None,"created_at":datetime.now(),"best_of":best_of,"p1_wins":0,"p2_wins":0,"game_type":"friend"}
        asyncio.create_task(game_timeout(game_id, context))
        accept_btn = InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التحدي", callback_data=f"join_{game_id}")]])
        await context.bot.send_message(friend_id, f"⚔️ *{user.first_name}* بيتحداك من قائمة أصدقائه ({'أفضل من ٣' if best_of==3 else 'جولة واحدة'})!\nاضغط قبول 👇", parse_mode="Markdown", reply_markup=accept_btn)
        await query.edit_message_text("✅ تم إرسال التحدي لصديقك!")

    # العشائر
    elif data == "menu_clans":
        clans = db.get_all_clans()
        user_clan = u.get("clan","") or ""
        text = "🗡️ *العشائر*\n\n"
        if clans:
            for i, c in enumerate(clans[:10]):
                medal = ["🥇","🥈","🥉"][i] if i<3 else f"{i+1}."
                members = len([m for m in c.get("members","").split(",") if m])
                text += f"{medal} *{c['clan_name']}* — {c.get('points',0)} نقطة — {members} عضو\n"
        else: text += "مفيش عشائر لسه!\n"
        btns = []
        if user_clan: btns.append([InlineKeyboardButton(f"🗡️ عشيرتي: {user_clan}", callback_data=f"clan_view_{user_clan}")])
        else: btns.append([InlineKeyboardButton("➕ إنشاء عشيرة", callback_data="clan_create")]); btns.append([InlineKeyboardButton("🚪 انضم لعشيرة", callback_data="clan_join_menu")]) if clans else None
        btns.append([InlineKeyboardButton("🏆 تصنيف العشائر", callback_data="rank_clans")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data == "rank_clans":
        clans = db.get_all_clans()
        text = "🏆 *تصنيف العشائر*\n\n"
        if not clans: text += "لا توجد عشائر بعد."
        else:
            for i, c in enumerate(clans[:10]):
                medal = ["🥇","🥈","🥉"][i] if i<3 else f"{i+1}."
                members = len([m for m in c.get("members","").split(",") if m])
                text += f"{medal} *{c['clan_name']}* — {c.get('points',0)} نقطة — {members} عضو\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_clans"))

    elif data == "clan_create":
        await query.edit_message_text("✏️ ابعت اسم العشيرة (من 2 لـ 20 حرف):", reply_markup=back_btn("menu_clans"))
        context.user_data["awaiting"] = "clan_name"; context.user_data["awaiting_time"] = datetime.now()

    elif data == "clan_join_menu":
        clans = db.get_all_clans()
        btns = [[InlineKeyboardButton(c["clan_name"], callback_data=f"clan_join_{c['clan_name']}")] for c in clans]
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")])
        await query.edit_message_text("اختار العشيرة:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("clan_join_"):
        clan_name = data.replace("clan_join_","")
        clan = db.get_clan(clan_name)
        if not clan: await query.answer("❌ العشيرة مش موجودة!", show_alert=True); return
        if u.get("clan"): await query.answer("❌ انت في عشيرة بالفعل!", show_alert=True); return
        members = [m for m in clan.get("members","").split(",") if m]
        members.append(str(user.id))
        db.update_clan(clan_name, members=",".join(members))
        db.update_user(user.id, clan=clan_name)
        await query.edit_message_text(f"✅ انضممت لعشيرة *{clan_name}*!", parse_mode="Markdown", reply_markup=back_btn("menu_clans"))

    elif data.startswith("clan_view_"):
        clan_name = data.replace("clan_view_","")
        clan = db.get_clan(clan_name)
        if not clan: await query.edit_message_text("❌ العشيرة مش موجودة!"); return
        members = [m for m in clan.get("members","").split(",") if m]
        members_count = len(members)
        is_leader = str(user.id) == str(clan.get("leader_id",""))
        bot_username = context.bot.username
        join_link = f"https://t.me/{bot_username}?start=joinclan_{clan_name}"
        text = f"🗡️ *{clan_name}*\n\n👥 الأعضاء: {members_count}\n💰 النقاط: {clan.get('points',0)}\n📝 الوصف: {clan.get('description','') or 'لا يوجد'}\n"
        if is_leader: text += f"\n🔗 رابط الدعوة: `{join_link}`"
        btns = []
        if is_leader: btns.append([InlineKeyboardButton("⚙️ إدارة العشيرة", callback_data=f"clan_manage_{clan_name}")]); btns.append([InlineKeyboardButton("📤 دعوة للعشيرة", callback_data=f"clan_invite_{clan_name}")])
        btns.append([InlineKeyboardButton("🚪 مغادرة العشيرة", callback_data=f"clan_leave_{clan_name}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_clans")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("clan_invite_"):
        clan_name = data.replace("clan_invite_","")
        bot_username = context.bot.username
        join_link = f"https://t.me/{bot_username}?start=joinclan_{clan_name}"
        await query.answer(f"رابط الدعوة: {join_link}", show_alert=True)

    elif data.startswith("clan_leave_"):
        clan_name = data.replace("clan_leave_","")
        db.update_user(user.id, clan="")
        clan = db.get_clan(clan_name)
        if clan:
            members = [m for m in clan.get("members","").split(",") if m != str(user.id)]
            db.update_clan(clan_name, members=",".join(members))
        await query.edit_message_text("✅ غادرت العشيرة.", reply_markup=back_btn("menu_clans"))

    elif data.startswith("clan_manage_"):
        clan_name = data.replace("clan_manage_","")
        await query.edit_message_text(f"⚙️ *إدارة عشيرة {clan_name}*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ تعديل الوصف", callback_data=f"clan_desc_{clan_name}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data=f"clan_view_{clan_name}")]
            ]))

    elif data.startswith("clan_desc_"):
        clan_name = data.replace("clan_desc_","")
        context.user_data["awaiting"] = f"clan_desc:{clan_name}"; context.user_data["awaiting_time"] = datetime.now()
        await query.edit_message_text("✏️ ابعت الوصف الجديد للعشيرة:", reply_markup=back_btn(f"clan_manage_{clan_name}"))

    # طريقة اللعب
    elif data == "menu_howto":
        text = ("❓ *طريقة اللعب*\n\n🪨 حجر يكسر ✂️ مقص\n✂️ مقص يقطع 📄 ورقة\n📄 ورقة تغطي 🪨 حجر\n\n"
                "🎮 *أنواع اللعب:*\n• فردي — ضد البوت\n• مع صديق — جولة واحدة أو أفضل من 3\n• عشوائي — مع لاعب عشوائي\n"
                "• قنوات — جولات بين عضوين كل دقيقتين\n• Spock — النسخة الموسعة\n• وضع القصة — رحلة بمستويات\n\n"
                "💰 *النقاط:*\n• فوز = 10-15 نقطة\n• تعادل = 5 نقاط\n• خسارة = -3 نقطة\n• دعوة صديق = 1000 نقطة\n\n"
                "🎁 المكافأة اليومية — اكسب نقاط متزايدة كل يوم\n🏆 البطولات — تنافس مع 8 لاعبين\n🎖️ الإنجازات — افتح شارات جديدة\n"
                "🗡️ العشائر — انضم وتنافس\n🎁 المهام — نقاط إضافية\n🛒 المتجر — اشتري بطاقات")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # تقييم
    elif data == "menu_rate":
        avg, count = db.get_avg_rating()
        await query.edit_message_text(f"⭐ *تقييم البوت*\n\nالتقييم الحالي: {avg}/50 ⭐ ({count} تقييم)\n\nاختار تقييمك:", parse_mode="Markdown", reply_markup=stars_keyboard())
    elif data.startswith("rate_"):
        stars = int(data.replace("rate_",""))
        db.add_rating(user.id, stars)
        await query.edit_message_text(f"✅ شكراً! ديت {stars} نجمة ⭐", reply_markup=back_btn())

    # دعم
    elif data == "menu_support":
        await query.edit_message_text("💎 *دعم البوت*\n\n⭐ قيّم البوت\n📢 شارك مع أصحابك\n💬 ابعت اقتراحاتك", parse_mode="Markdown", reply_markup=back_btn())

    # القنوات
    elif data == "menu_channels":
        channels = db.get_active_channels()
        text = "📺 *القنوات والجروبات النشطة*\n\n"
        if channels:
            for ch in channels: text += f"🟢 {ch['title']}\n"
        else: text += "مفيش جروبات نشطة دلوقتي.\n"
        text += "\nعشان تفعّل في جروبك:\n1. ضيف البوت واعمله Admin\n2. ابعت /activate"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # لوحة المؤسس
    elif data == "founder_panel":
        if not is_founder(user.id): await query.answer("❌ مش مسموحلك!", show_alert=True); return
        users_count = db.get_users_count()
        await query.edit_message_text(f"👑 *لوحة المؤسس*\n\n👥 إجمالي اللاعبين: {users_count}", parse_mode="Markdown", reply_markup=founder_keyboard())

    elif data == "f_stats":
        if not is_founder(user.id): return
        users_count = db.get_users_count()
        clans_count = db.get_clans_count()
        avg, count = db.get_avg_rating()
        text = (f"📊 *إحصائيات البوت*\n\n👥 اللاعبين: {users_count}\n🗡️ العشائر: {clans_count}\n"
                f"⭐ متوسط التقييم: {avg}/50 ({count} تقييم)\n📺 جروبات نشطة: {len(channel_tasks)}")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("founder_panel"))

    elif data == "f_ratings":
        if not is_founder(user.id): return
        avg, count = db.get_avg_rating()
        await query.edit_message_text(f"⭐ *التقييمات*\n\nمتوسط: {avg}/50\nعدد التقييمات: {count}", parse_mode="Markdown", reply_markup=back_btn("founder_panel"))

    elif data == "f_addpts":
        if not is_founder(user.id): return
        await query.edit_message_text("👑 ابعت ID المستخدم اللي عايز تضيفله نقاط:", reply_markup=back_btn("founder_panel"))
        context.user_data["awaiting"] = "f_addpts_uid"; context.user_data["awaiting_time"] = datetime.now()

    elif data == "f_subpts":
        if not is_founder(user.id): return
        await query.edit_message_text("👑 ابعت ID المستخدم اللي عايز تخصم منه نقاط:", reply_markup=back_btn("founder_panel"))
        context.user_data["awaiting"] = "f_subpts_uid"; context.user_data["awaiting_time"] = datetime.now()

    elif data in ("f_ban", "f_unban"):
        if not is_founder(user.id): return
        action = "حظر" if data=="f_ban" else "فك حظر"
        await query.edit_message_text(f"👑 ابعت ID المستخدم عشان {action}:", reply_markup=back_btn("founder_panel"))
        context.user_data["awaiting"] = f"{data}_uid"; context.user_data["awaiting_time"] = datetime.now()

    elif data == "f_broadcast":
        if not is_founder(user.id): return
        await query.edit_message_text("📢 ابعت الرسالة اللي عايز تبعتا لكل اللاعبين:", reply_markup=back_btn("founder_panel"))
        context.user_data["awaiting"] = "f_broadcast_msg"; context.user_data["awaiting_time"] = datetime.now()

    elif data in ("f_shop", "f_tasks"):
        if not is_founder(user.id): return
        await query.edit_message_text("🔧 إدارة المتجر والمهام قريباً!", reply_markup=back_btn("founder_panel"))

    # وضع القصة
    elif data == "story_mode": await story_mode_handler(update, context)
    # Spock
    elif data == "play_spock": await play_spock_handler(update, context)
    elif data.startswith("spock_"): await handle_spock_choice(update, context, data.replace("spock_",""))
    # الانضمام للبطولة
    elif data == "join_tournament":
        t = db.get_active_tournament()
        if not t: await query.answer("❌ مفيش بطولة مفتوحة حالياً.", show_alert=True)
        else:
            if db.join_tournament(t["tournament_id"], user.id):
                players = [p for p in t["players"].split(",") if p]
                await query.answer(f"✅ انضميت! ({len(players)}/8)", show_alert=True)
                if len(players) >= 8: t["status"] = "running"; await start_tournament(t, context)
            else: await query.answer("❌ إما البطولة مقفولة أو انت مشترك بالفعل.", show_alert=True)

# ─ـ معالج النصوص ─────────────────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    awaiting = context.user_data.get("awaiting","")
    text = update.message.text.strip()
    awaiting_time = context.user_data.get("awaiting_time")
    if awaiting and awaiting_time:
        if (datetime.now() - awaiting_time).total_seconds() > 120:
            context.user_data.pop("awaiting",None); context.user_data.pop("awaiting_time",None)
            await update.message.reply_text("⌛ انتهت صلاحية العملية السابقة.")
            return

    if awaiting == "friend_challenge":
        target = text.lstrip("@")
        target_user = None
        if target.isdigit(): target_user = db.get_user(int(target))
        else:
            for uid, u in db._cache["users"].items():
                if u.get("username","").lower() == target.lower(): target_user = u; break
        if not target_user: await update.message.reply_text("❌ المستخدم مش موجود."); context.user_data["awaiting"] = None; return
        if str(target_user["user_id"]) == str(user.id): await update.message.reply_text("❌ ما ينفعش تتحدى نفسك!"); context.user_data["awaiting"] = None; return
        best_of = context.user_data.get("friend_best_of",1)
        async with active_games_lock:
            game_id = f"f_{user.id}_{random.randint(1000,9999)}"
            active_games[game_id] = {"p1":user.id,"p1_name":user.first_name,"p2":None,"p2_name":None,"c1":None,"c2":None,"created_at":datetime.now(),"best_of":best_of,"p1_wins":0,"p2_wins":0,"game_type":"friend"}
        asyncio.create_task(game_timeout(game_id, context))
        accept_btn = InlineKeyboardMarkup([[InlineKeyboardButton("✅ قبول التحدي", callback_data=f"join_{game_id}")]])
        await context.bot.send_message(int(target_user["user_id"]), f"⚔️ *{user.first_name}* بيتحداك ({'أفضل من ٣' if best_of==3 else 'جولة واحدة'})!\nاضغط قبول 👇", parse_mode="Markdown", reply_markup=accept_btn)
        await update.message.reply_text(f"✅ تم إرسال التحدي إلى {target_user['name']}!")
        context.user_data["awaiting"] = None

    elif awaiting == "add_friend":
        target = text.lstrip("@")
        target_user = None
        if target.isdigit(): target_user = db.get_user(int(target))
        else:
            for uid, u in db._cache["users"].items():
                if u.get("username","").lower() == target.lower(): target_user = u; break
        if not target_user: await update.message.reply_text("❌ المستخدم مش موجود."); context.user_data["awaiting"] = None; return
        if str(target_user["user_id"]) == str(user.id): await update.message.reply_text("❌ ما ينفعش تضيف نفسك!"); context.user_data["awaiting"] = None; return
        if db.send_friend_request(user.id, target_user["user_id"], user.first_name):
            await update.message.reply_text(f"✅ تم إرسال طلب الصداقة إلى {target_user['name']}.")
            try: await context.bot.send_message(int(target_user["user_id"]), f"📥 {user.first_name} بعتلك طلب صداقة!")
            except: pass
        else: await update.message.reply_text("❌ تم إرسال طلب بالفعل.")
        context.user_data["awaiting"] = None

    elif awaiting == "clan_name":
        if len(text)<2 or len(text)>20: await update.message.reply_text("❌ الاسم لازم بين 2 و 20 حرف!"); return
        if db.get_clan(text): await update.message.reply_text("❌ الاسم موجود بالفعل!"); return
        u = db.get_user(user.id)
        if u and u.get("clan"): await update.message.reply_text("❌ انت في عشيرة بالفعل!"); return
        db.create_clan(text, user.id)
        db.update_user(user.id, clan=text)
        context.user_data["awaiting"] = None
        await update.message.reply_text(f"✅ تم إنشاء عشيرة *{text}*! 🗡️", parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

    elif awaiting and awaiting.startswith("clan_desc:"):
        clan_name = awaiting.split(":")[1]
        db.update_clan(clan_name, description=text)
        context.user_data["awaiting"] = None
        await update.message.reply_text("✅ تم تحديث الوصف!", reply_markup=main_menu_keyboard(user.id))

    # أوامر المؤسس
    elif awaiting == "f_addpts_uid" and is_founder(user.id):
        if not text.isdigit(): await update.message.reply_text("❌ ID رقمي."); return
        context.user_data["f_addpts_uid"] = int(text)
        context.user_data["awaiting"] = "f_addpts_amount"
        await update.message.reply_text("👌 ابعت عدد النقاط:")
    elif awaiting == "f_addpts_amount" and is_founder(user.id):
        if not text.lstrip('-').isdigit(): await update.message.reply_text("❌ رقم صحيح."); return
        amount = int(text); uid = context.user_data.get("f_addpts_uid")
        if uid:
            u = db.get_user(uid)
            if u: db.update_user(uid, points=int(u.get("points",0))+amount); await update.message.reply_text(f"✅ تم إضافة {amount} نقطة للاعب {u['name']}.")
            else: await update.message.reply_text("❌ اللاعب مش موجود.")
        context.user_data["awaiting"] = None
    elif awaiting == "f_subpts_uid" and is_founder(user.id):
        if not text.isdigit(): await update.message.reply_text("❌ ID رقمي."); return
        context.user_data["f_subpts_uid"] = int(text)
        context.user_data["awaiting"] = "f_subpts_amount"
        await update.message.reply_text("👌 ابعت عدد النقاط:")
    elif awaiting == "f_subpts_amount" and is_founder(user.id):
        if not text.isdigit(): await update.message.reply_text("❌ رقم صحيح."); return
        amount = int(text); uid = context.user_data.get("f_subpts_uid")
        if uid:
            u = db.get_user(uid)
            if u: db.update_user(uid, points=max(0,int(u.get("points",0))-amount)); await update.message.reply_text(f"✅ تم خصم {amount} نقطة من {u['name']}.")
            else: await update.message.reply_text("❌ اللاعب مش موجود.")
        context.user_data["awaiting"] = None
    elif awaiting == "f_ban_uid" and is_founder(user.id):
        if not text.isdigit(): await update.message.reply_text("❌ ID."); return
        db.ban_user(int(text)); await update.message.reply_text("✅ تم الحظر."); context.user_data["awaiting"] = None
    elif awaiting == "f_unban_uid" and is_founder(user.id):
        if not text.isdigit(): await update.message.reply_text("❌ ID."); return
        db.unban_user(int(text)); await update.message.reply_text("✅ تم فك الحظر."); context.user_data["awaiting"] = None
    elif awaiting == "f_broadcast_msg" and is_founder(user.id):
        sent = 0
        user_ids = db.get_all_user_ids()
        for uid in user_ids:
            try: await context.bot.send_message(int(uid), text, disable_notification=True); sent += 1
            except: pass
        await update.message.reply_text(f"✅ تم الإرسال لـ {sent} لاعب.")
        context.user_data["awaiting"] = None

# ─ـ معالج الأخطاء ─ـ
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"استثناء غير معالج: {context.error}")
    try: await context.bot.send_message(FOUNDER_ID, f"⚠️ خطأ غير معالج:\n`{context.error}`\nالحدث: {update}", parse_mode="Markdown")
    except Exception as e: logging.error(f"فشل إرسال إشعار الخطأ للمؤسس: {e}")

def main():
    if not TOKEN: raise ValueError("BOT_TOKEN غير موجود!")
    db.init_cache()
    load_translations()
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("activate", activate_channel))
    app.add_handler(CommandHandler("stopchannel", stop_channel))
    app.add_handler(CommandHandler("tournament", create_tournament))
    app.add_handler(CommandHandler("join", join_tournament))
    app.add_handler(CommandHandler("achievements", achievements_command))
    app.add_handler(CommandHandler("event", event_info))
    app.add_handler(CommandHandler("clanwar", clan_war_status))
    app.add_handler(CommandHandler("startwar", start_clan_war))
    app.add_handler(CommandHandler("endwar", end_war_command))
    app.add_handler(CommandHandler("groupchallenge", group_challenge_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logging.info("✅ البوت شغال...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
