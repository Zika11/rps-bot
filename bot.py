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

# استيراد الملفات الجديدة
from state import *
from keyboards import *
from game_logic import *
from handlers import *

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
    try:
        flask_app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logging.error(f"فشل تشغيل Flask: {e}")

# ─ـ Redis Caching (اختياري) ─ـ
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_timeout=2)
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

def is_founder(user_id): return user_id == FOUNDER_ID

def get_choices_for_user(user_id):
    u = db.get_user(user_id)
    theme = (u.get("theme") if u else None) or "theme_1"
    return THEME_ICONS.get(theme, CHOICES)

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
            if game_id in active_games:
                del active_games[game_id]

# ─ـ المكافأة اليومية ─ـ
async def claim_daily(user_id, context):
    u = db.get_user(user_id)
    if not u: return ""
    today = str(date.today())
    if u.get("last_claim_date") != today:
        db.update_user(user_id, daily_claimed=0)
        u = db.get_user(user_id)
    if u.get("daily_claimed"):
        return "✅ استلمت مكافأتك النهارده خلاص! تعالى بكره."
    streak = db._safe_int(u.get("streak_count"))
    last_date = u.get("last_claim_date")
    yesterday = str(date.today() - timedelta(days=1))
    if last_date == yesterday: streak += 1
    else: streak = 1
    reward = min(MIN_STREAK_MULTIPLIER * streak, MAX_STREAK_REWARD)
    db.update_user(user_id, streak_count=streak, last_claim_date=today, daily_claimed=1,
                   points=int(u.get("points",0)) + reward)
    return f"🎁 مكافأة اليوم {streak}! حصلت على {reward} نقطة. النهارده يومك رقم {streak} على التوالي!"

# ─ـ القنوات ─ـ
async def channel_loop(chat_id, context):
    consecutive_errors = 0
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
                msg = await context.bot.send_message(chat_id, "🎮 جولة جديدة بين عضوين! أول واحد يضغط هيبقى اللاعب الأول 👇", reply_markup=channel_keyboard(chat_id))
                channel_games[chat_id] = {"player1":None,"choice1":None,"player2":None,"choice2":None,"message_id":msg.message_id,"created":datetime.now()}
                channel_last_play[chat_id] = datetime.now()
                consecutive_errors = 0
            except (tg_error.Forbidden, tg_error.BadRequest, tg_error.ChatNotFound):
                await stop_channel_internal(chat_id, context); break
            except Exception as e:
                logging.error(f"channel_loop {chat_id}: {e}")
                consecutive_errors += 1
                if consecutive_errors > 5:
                    logging.critical(f"عدد كبير من الأخطاء في القناة {chat_id}، إيقاف.")
                    break

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
                        try: await context.bot.send_message(int(ref_id), f"🎁 المستخدم {user.first_name} دخل عن طريق رابط الدعوة بتاعك! تم إضافة {DAILY_REFERRAL_POINTS} نقطة لك.")
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
            await update.message.reply_text(f"✅ تم قبول التحدي! ⚔️ {game['p1_name']} vs {user.first_name}")
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
            await update.message.reply_text(f"✅ انضممت إلى عشيرة {clan_name}!")
            return
    db.get_or_create_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    if db.is_banned(user.id): await update.message.reply_text("🚫 أنت محظور من استخدام البوت."); return
    points = int(u.get("points", 0))
    leaderboard = db.get_leaderboard(100)
    rank = next((i+1 for i,p in enumerate(leaderboard) if str(p["user_id"])==str(user.id)), "غير مصنف")
    text = (f"أهلاً {user.first_name}! 👋\n\n🎮 لعبة حجر ورقة مقص\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇")
    if ref_bonus: text += "\n\n🎁 تم منح صاحبك 1000 نقطة على دعوتك!"
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user.id))

async def achievements_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u: return
    all_achs = db.get_achievements()
    earned = [a for a in u.get("achievements","").split(",") if a]
    text = "🎖️ قائمة الإنجازات:\n\n"
    for ach in all_achs:
        status = "✅" if ach["ach_id"] in earned else "🔒"
        text += f"{status} {ach['icon']} {ach['name']} - {ach['description']}\n"
    await update.message.reply_text(text)

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
        await query.edit_message_text(f"أهلاً {user.first_name}! 👋\n\n🎮 لعبة حجر ورقة مقص\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇", reply_markup=main_menu_keyboard(user.id))
    elif data == "daily_bonus":
        msg = await claim_daily(user.id, context)
        await query.answer(msg, show_alert=True); await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user.id))
    elif data == "menu_play": await query.edit_message_text("🎮 اختار نوع اللعب:", reply_markup=play_menu_keyboard())

    # فردي
    elif data == "play_solo": await query.edit_message_text("🤖 اختار حركتك:", reply_markup=solo_keyboard(user.id))
    elif data.startswith("solo_"):
        choice = data.replace("solo_", "")
        if choice not in CHOICES:
            await query.answer("حركة غير صحيحة", show_alert=True)
            return
        if context.user_data.get("solo_played"):
            await query.answer("انت لعبت خلاص الجولة دي", show_alert=True)
            return
        context.user_data["solo_played"] = True
        bot_choice = smart_bot_choice(user.id)
        result = get_result(choice, bot_choice)
        u = db.get_user(user.id)
        pts = int(u.get("points",0) or 0); wins = int(u.get("wins",0) or 0); losses = int(u.get("losses",0) or 0); draws = int(u.get("draws",0) or 0)
        solo_games = int(u.get("solo_games",0)) + 1
        rock_used = int(u.get("rock_used",0)) + (1 if choice=="rock" else 0)
        paper_used = int(u.get("paper_used",0)) + (1 if choice=="paper" else 0)
        scissors_used = int(u.get("scissors_used",0)) + (1 if choice=="scissors" else 0)
        win_streak = int(u.get("win_streak",0))
        if result == "win":
            emoji, txt, pts_add = "🎉", "كسبت!", WIN_POINTS_SOLO
            wins += 1; win_streak += 1
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
        try:
            await query.edit_message_text(
                f"انت: {get_choices_for_user(user.id)[choice]}\nالبوت: {get_choices_for_user(user.id)[bot_choice]}\n\n"
                f"{emoji} {txt}  ({'+' if pts_add>=0 else ''}{pts_add} نقطة)\n💰 نقاطك: {pts}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 العب تاني", callback_data="play_solo")],
                    [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]
                ])
            )
        except Exception as e:
            logging.error(f"فشل تعديل رسالة الجولة: {e}")
        context.user_data["solo_played"] = False

    # صديق
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
        await query.edit_message_text(f"⚔️ {game['p1_name']} vs {user.first_name}\nاللعبة بدأت!")
        kb = mp_keyboard(game_id)
        await context.bot.send_message(game["p1"], "اختار حركتك 👇", reply_markup=kb)
        await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)

    # متعددة
    elif data.startswith("mp_"):
        parts = data.split("_"); choice = parts[-1]; game_id = "_".join(parts[1:-1])
        if choice not in CHOICES:
            await query.answer("حركة غير صحيحة", show_alert=True)
            return
        async with active_games_lock:
            game = active_games.get(game_id)
            if not game: await query.edit_message_text("❌ اللعبة انتهت."); return
            if user.id == game["p1"] and not game["c1"]: game["c1"] = choice; await query.edit_message_text("✅ اخترت! استنى...")
            elif user.id == game["p2"] and not game["c2"]: game["c2"] = choice; await query.edit_message_text("✅ اخترت! استنى...")
            else: return
            if game["c1"] and game["c2"]:
                c1, c2 = game["c1"], game["c2"]; result = get_result(c1, c2)
                summary = f"⚔️ النتيجة\n\n{game['p1_name']}: {CHOICES[c1]}\n{game['p2_name']}: {CHOICES[c2]}\n\n"
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
                    final_msg = f"🏆 الماتش انتهى!\nالنتيجة النهائية: {game['p1_wins']} - {game['p2_wins']}\nالفائز: {db.get_user(winner_id)['name']} (+{WIN_POINTS_MULTI} نقطة)"
                    await context.bot.send_message(game["p1"], final_msg)
                    await context.bot.send_message(game["p2"], final_msg)
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
                await query.edit_message_text(f"✅ لاقيت خصم: {opponent['name']}\nاختار حركتك 👇", reply_markup=kb)
                await context.bot.send_message(opponent["id"], f"✅ لاقيت خصم: {user.first_name}\nاختار حركتك 👇", reply_markup=kb)
            else:
                pending_matches.append({"id":user.id,"name":user.first_name})
                await query.edit_message_text("🔍 بندور على خصم... استنى!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_random")]]))
    elif data == "cancel_random":
        async with pending_matches_lock:
            pending_matches[:] = [m for m in pending_matches if m["id"]!=user.id]
        await query.edit_message_text("✅ تم الإلغاء.", reply_markup=main_menu_keyboard(user.id))

    # القناة
    elif data.startswith("ch_"):
        parts = data.split("_", 2); channel_id = int(parts[1]); choice = parts[2]
        if choice not in CHOICES:
            await query.answer("حركة غير صحيحة", show_alert=True)
            return
        async with channel_games_lock:
            game = channel_games.get(channel_id)
            if not game: await query.answer("❌ انتهت الجولة.", show_alert=True); return
            if user.id == game.get("player1") or user.id == game.get("player2"): await query.answer("❌ انت لعبت خلاص!", show_alert=True); return
            if game["player1"] is None:
                game["player1"] = user.id; game["choice1"] = choice
                await query.answer("✅ انت اللاعب الأول! استنى الخصم", show_alert=True)
                try: await context.bot.edit_message_text(chat_id=channel_id, message_id=game["message_id"], text=f"🎮 {user.first_name} دخل اللعبة! في انتظار لاعب تاني يضغط...", reply_markup=channel_keyboard(channel_id))
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
                final_text = f"⚔️ النتيجة\n\n{p1['name']}: {c1_name}\n{p2['name']}: {c2_name}\n\n🏆 {result_text}\n💰 {p1['name']}: {'+' if p1_add>=0 else ''}{p1_add} نقطة | {p2['name']}: {'+' if p2_add>=0 else ''}{p2_add} نقطة"
                try: await context.bot.edit_message_text(chat_id=channel_id, message_id=game["message_id"], text=final_text)
                except Exception as e: logging.error(f"فشل عرض نتيجة القناة: {e}")
                del channel_games[channel_id]
            else: await query.answer("❌ اللعبة اكتملت خلاص", show_alert=True)

    # باقي الأزرار (التصنيف، الملف، المتجر، العشائر...) تستدعي دوال من handlers و keyboards
    # ...

# ─ـ معالج النصوص ─ـ
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
    # حالات text_handler الكاملة (friend_challenge, add_friend, clan_name, clan_desc, أوامر المؤسس...)
    # موجودة في النسخ السابقة ويمكن نسخها كما هي.
    # ...

# ─ـ معالج الأخطاء ─ـ
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("استثناء غير معالج")
    try: await context.bot.send_message(FOUNDER_ID, f"⚠️ خطأ غير معالج:\n{context.error}\nالحدث: {update}")
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
