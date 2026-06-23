import random, asyncio, json, logging
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram import error as tg_error
import db
from keyboards import *

# ── الثوابت ─────────────────────────────────────────────────
CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
GAME_TIMEOUT = 120
CHANNEL_ROUND_INTERVAL = 120
MAX_STREAK_REWARD = 100
MIN_STREAK_MULTIPLIER = 10
STORY_LEVELS = {
    1: {"boss": "الرجل الحجري", "emoji": "🗿", "story": "في مملكة الأحجار..."},
    2: {"boss": "ملك الورق", "emoji": "📜", "story": "بعد هزيمة الرجل الحجري..."},
    3: {"boss": "سيد المقصات", "emoji": "⚔️", "story": "أقوى زعيم في المملكة..."}
}

# ─ـ هياكل البيانات المشتركة (سيتم استيرادها من bot.py أو وضعها في ملف منفصل لاحقاً) ─ـ
# حالياً سنفترض وجودها في bot.py وتمريرها كوسائط أو استيرادها
# لتجنب التعقيد، سنستوردها من bot نفسه
# لكن التصميم النظيف يتطلب نقلها لملف state.py

# ─ـ دوال مساعدة ─────────────────────────────────────────────
def get_result(p1, p2): return "draw" if p1==p2 else ("win" if WIN_MAP[p1]==p2 else "loss")

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
    if u.get("daily_claimed") and u.get("last_claim_date") == today:
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
    earned = (u.get("achievements","") or "").split(",")
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
            owned = (u.get("shop_items","") or "").split(",")
            current = len([o for o in owned if o])
        elif field == "clan_created":
            for clan in db.get_all_clans():
                if str(clan["leader_id"]) == str(user_id): current = 1; break
        elif field == "clan_joined": current = 1 if u.get("clan") else 0
        elif field == "tournament_win": current = int(u.get("tournament_wins",0))
        elif field == "rated": current = 1 if str(user_id) in db._cache["ratings"] else 0
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
        # ... (سنكمل دوال القنوات لاحقاً، هي الآن في bot.py)
        pass

async def cancel_channel_game(channel_id, context, reason=""):
    # ... (موجودة في bot.py)
    pass

async def stop_channel_internal(chat_id, context):
    # ... (موجودة في bot.py)
    pass

async def check_bot_permissions(chat_id, context):
    # ... (موجودة في bot.py)
    pass

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
        players = t["players"].split(",")
        await update.message.reply_text(f"✅ انضميت للبطولة! ({len(players)}/8)")
        if len(players) >= 8:
            t["status"] = "running"
            await start_tournament(t, context)
    else: await update.message.reply_text("❌ إما البطولة مقفولة أو انت مشترك بالفعل.")

async def start_tournament(t, context):
    # ... (موجودة في bot.py)
    pass

async def handle_tournament_match_result(game, winner_id, context):
    # ... (موجودة في bot.py)
    pass

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

# ─ـ الأوامر الأساسية ─ـ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_bonus = False
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_id = arg.replace("ref_", "")
            existing = db.get_user(user.id)
            if not existing and str(user.id) != ref_id:
                referrer = db.get_user(int(ref_id))
                if referrer and not db.has_been_referred(user.id):
                    pts = int(referrer.get("points", 0) or 0)
                    db.update_user(int(ref_id), points=pts + 1000)
                    db.mark_referred(user.id)
                    ref_bonus = True
                    try: await context.bot.send_message(int(ref_id), f"🎁 المستخدم *{user.first_name}* دخل عن طريق رابط الدعوة بتاعك! تم إضافة 1000 نقطة لك.", parse_mode="Markdown")
                    except Exception as e: logging.error(f"فشل إرسال إشعار الإحالة: {e}")
        # ... (باقي حالات start)
    db.get_or_create_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    if db.is_banned(user.id): await update.message.reply_text("🚫 أنت محظور من استخدام البوت."); return
    points = int(u.get("points", 0))
    leaderboard = db.get_leaderboard(100)
    rank = next((i+1 for i,p in enumerate(leaderboard) if p["user_id"]==str(user.id)), "غير مصنف")
    text = (f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇")
    if ref_bonus: text += "\n\n🎁 تم منح صاحبك 1000 نقطة على دعوتك!"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

async def activate_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (موجودة في bot.py)
    pass

async def stop_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (موجودة في bot.py)
    pass
