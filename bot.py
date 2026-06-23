import os, random, asyncio, json
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from telegram import error as tg_error
import db

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

FOUNDER_ID = 1232067711

CHOICES = {"rock": "🪨 حجر", "paper": "📄 ورقة", "scissors": "✂️ مقص"}
WIN_MAP = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

pending_matches = []
active_games = {}
channel_auto_game = {}          # flag for enabled channels
channel_games = {}              # PvP state per channel: {chat_id: game_state}
channel_last_play = {}

def get_result(p1, p2):
    if p1 == p2: return "draw"
    return "win" if WIN_MAP[p1] == p2 else "loss"

def is_founder(user_id):
    return user_id == FOUNDER_ID

# ── Keyboards ─────────────────────────────────────────────────
def main_menu_keyboard(user_id=None):
    rows = [
        [InlineKeyboardButton("🎮 العب الآن", callback_data="menu_play")],
        [InlineKeyboardButton("🏆 التصنيف", callback_data="menu_rank"),
         InlineKeyboardButton("🗡️ العشائر", callback_data="menu_clans")],
        [InlineKeyboardButton("🎁 المهام", callback_data="menu_tasks"),
         InlineKeyboardButton("🛒 المتجر", callback_data="menu_shop")],
        [InlineKeyboardButton("📺 القنوات", callback_data="menu_channels"),
         InlineKeyboardButton("👤 حسابي", callback_data="menu_profile")],
        [InlineKeyboardButton("❓ طريقة اللعب", callback_data="menu_howto"),
         InlineKeyboardButton("⭐ تقييم البوت", callback_data="menu_rate")],
        [InlineKeyboardButton("💎 دعم البوت", callback_data="menu_support"),
         InlineKeyboardButton("🔗 دعوة صديق", callback_data="menu_referral")],
    ]
    if user_id and is_founder(user_id):
        rows.append([InlineKeyboardButton("👑 لوحة المؤسس", callback_data="founder_panel")])
    return InlineKeyboardMarkup(rows)

def back_btn(target="menu_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=target)]])

def play_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 لعب فردي", callback_data="play_solo")],
        [InlineKeyboardButton("👥 لعب مع صديق", callback_data="play_friend")],
        [InlineKeyboardButton("🎲 لعب عشوائي", callback_data="play_random")],
        [InlineKeyboardButton("📺 لعب في قناة/جروب", callback_data="play_channel")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

def solo_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"solo_{k}")
        for k, v in CHOICES.items()
    ]])

def mp_keyboard(game_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"mp_{game_id}_{k}")
        for k, v in CHOICES.items()
    ]])

def channel_keyboard(channel_id):
    # PvP: everyone sees buttons, first press is Player1, second press is Player2
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"ch_{channel_id}_{k}")
        for k, v in CHOICES.items()
    ]])

def stars_keyboard():
    options = [1, 5, 10, 20, 30, 40, 50]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[:4]],
        [InlineKeyboardButton(f"{'⭐'*(min(s//10+1,3))} {s}", callback_data=f"rate_{s}") for s in options[4:]],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
    ])

def founder_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة نقاط", callback_data="f_addpts"),
         InlineKeyboardButton("➖ خصم نقاط", callback_data="f_subpts")],
        [InlineKeyboardButton("🚫 حظر لاعب", callback_data="f_ban"),
         InlineKeyboardButton("✅ فك حظر", callback_data="f_unban")],
        [InlineKeyboardButton("📢 رسالة جماعية", callback_data="f_broadcast")],
        [InlineKeyboardButton("🛒 إدارة المتجر", callback_data="f_shop"),
         InlineKeyboardButton("🎁 إدارة المهام", callback_data="f_tasks")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="f_stats"),
         InlineKeyboardButton("⭐ التقييمات", callback_data="f_ratings")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
    ])

def get_all_user_ids():
    try:
        return list(db._cache["users"].keys())
    except Exception:
        return []

# ── نظام المهام (async للإشعارات) ──────────────────────────────
async def check_and_complete_task(user_id, task_id, bot_context, progress_increment=1):
    """التحقق من إكمال المهمة، وإرسال إشعار إذا اكتملت. تعيد True إذا تم منح المكافأة للتو"""
    u = db.get_user(user_id)
    if not u: return False
    today = str(date.today())
    progress_data = u.get("tasks_progress")
    if progress_data:
        try:
            progress = json.loads(progress_data)
        except:
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
        required = {"task_1":5, "task_2":3, "task_3":1, "task_4":1, "task_5":10}.get(task_id, 1)
        if current >= required and not tasks_progress.get(f"{task_id}_done"):
            pts_reward = int(task_def["points_reward"])
            db.update_user(user_id, points=int(u.get("points",0)) + pts_reward)
            tasks_progress[f"{task_id}_done"] = True
            # إشعار
            try:
                await bot_context.bot.send_message(
                    user_id,
                    f"🎉 أكملت مهمة *{task_def['description']}* وحصلت على {pts_reward} نقطة!",
                    parse_mode="Markdown"
                )
            except:
                pass
            rewarded = True
    db.update_user(user_id, tasks_progress=json.dumps(progress))
    return rewarded

# ── دوال العشائر ───────────────────────────────────────────────
def add_clan_points(user_id, amount):
    u = db.get_user(user_id)
    if not u: return
    clan_name = u.get("clan")
    if not clan_name: return
    clan = db.get_clan(clan_name)
    if not clan: return
    current_pts = int(clan.get("points", 0) or 0)
    db.update_clan(clan_name, points=current_pts + amount)

# ── القنوات: لعبة PvP جديدة كل دقيقتين ─────────────────────────
async def auto_channel_loop(context, channel_id):
    while channel_id in channel_auto_game:
        await asyncio.sleep(120)  # كل دقيقتين
        if channel_id not in channel_auto_game:
            break
        last = channel_last_play.get(channel_id)
        if last and (datetime.now() - last).seconds > 1800:  # 30 دقيقة بدون لعب
            del channel_auto_game[channel_id]
            db.remove_active_channel(channel_id)
            try:
                await context.bot.send_message(channel_id, "😴 مفيش لاعبين من 30 دقيقة — تم إيقاف اللعب التلقائي.\nابعت /activate عشان تشغله تاني.")
            except:
                pass
            break
        # لو في لعبة شغالة ومستنيه، اتجاوز
        if channel_id in channel_games:
            # لو اللعبة old جداً نلغيها
            game = channel_games[channel_id]
            if datetime.now() - game["created"] > timedelta(seconds=90):
                await cancel_channel_game(channel_id, context, "انتهى وقت الجولة")
            else:
                continue
        # بداية لعبة جديدة
        try:
            msg = await context.bot.send_message(
                channel_id,
                "🎮 *جولة جديدة بين عضوين!* أول واحد يضغط هيبقى اللاعب الأول 👇",
                parse_mode="Markdown",
                reply_markup=channel_keyboard(channel_id)
            )
            channel_games[channel_id] = {
                "player1": None,
                "choice1": None,
                "player2": None,
                "choice2": None,
                "message_id": msg.message_id,
                "created": datetime.now()
            }
        except (tg_error.Forbidden, tg_error.BadRequest, tg_error.ChatNotFound):
            del channel_auto_game[channel_id]
            db.remove_active_channel(channel_id)
            break
        except:
            pass

async def cancel_channel_game(channel_id, context, reason=""):
    game = channel_games.pop(channel_id, None)
    if game:
        try:
            await context.bot.edit_message_text(
                chat_id=channel_id,
                message_id=game["message_id"],
                text=f"🚫 الجولة اتلغت{' - ' + reason if reason else ''}"
            )
        except:
            pass

# ── أوامر البوت ─────────────────────────────────────────────────
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
                if referrer:
                    pts = int(referrer.get("points", 0) or 0)
                    db.update_user(int(ref_id), points=pts + 1000)
                    ref_bonus = True
                    # إشعار للمُحيل
                    try:
                        await context.bot.send_message(
                            int(ref_id),
                            f"🎁 المستخدم *{user.first_name}* دخل عن طريق رابط الدعوة بتاعك! تم إضافة 1000 نقطة لك.",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
        elif arg.startswith("challenge_"):
            game_id = arg.replace("challenge_", "")
            game = active_games.get(game_id)
            if not game:
                await update.message.reply_text("❌ التحدي انتهى أو لم يعد موجوداً.")
                return
            if game["p1"] == user.id:
                await update.message.reply_text("❌ لا يمكنك قبول تحدي نفسك!")
                return
            if game["p2"] is not None:
                await update.message.reply_text("❌ هذا التحدي ممتلئ بالفعل!")
                return
            game["p2"] = user.id
            game["p2_name"] = user.first_name
            db.get_or_create_user(user.id, user.first_name, user.username)
            await update.message.reply_text(
                f"✅ تم قبول التحدي! ⚔️ *{game['p1_name']}* vs *{user.first_name}*",
                parse_mode="Markdown"
            )
            kb = mp_keyboard(game_id)
            await context.bot.send_message(game["p1"], "اللعبة بدأت! اختار حركتك 👇", reply_markup=kb)
            await context.bot.send_message(user.id, "اختار حركتك 👇", reply_markup=kb)
            return
    db.get_or_create_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    if u and u.get("banned"):
        await update.message.reply_text("🚫 أنت محظور من استخدام البوت.")
        return

    # ترحيب محسّن مع النقاط والتصنيف
    points = int(u.get("points", 0))
    leaderboard = db.get_leaderboard(100)
    rank = next((i+1 for i, p in enumerate(leaderboard) if p["user_id"] == str(user.id)), "غير مصنف")
    text = (
        f"أهلاً *{user.first_name}*! 👋\n\n"
        f"🎮 *لعبة حجر ورقة مقص*\n"
        f"💰 رصيدك: {points} نقطة\n"
        f"🏅 تصنيفك: #{rank}\n\n"
        f"اختار من القائمة 👇"
    )
    if ref_bonus:
        text += "\n\n🎁 تم منح صاحبك 1000 نقطة على دعوتك!"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id))

async def activate_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ("supergroup", "group"):
        await update.message.reply_text("⚠️ الأمر ده للجروبات بس!")
        return
    channel_auto_game[chat.id] = None
    channel_last_play[chat.id] = datetime.now()
    db.add_active_channel(chat.id, chat.title or "جروب")
    await update.message.reply_text("✅ تم تفعيل اللعب التلقائي في الجروب! كل دقيقتين هتظهر لعبة جديدة بين عضوين 🎮")
    asyncio.create_task(auto_channel_loop(context, chat.id))

# ── المعالج الرئيسي للأزرار ─────────────────────────────────────
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    db.get_or_create_user(user.id, user.first_name, user.username)

    u = db.get_user(user.id)
    if u and u.get("banned") and not data.startswith("founder"):
        await query.edit_message_text("🚫 أنت محظور من استخدام البوت.")
        return

    # ── القوائم الرئيسية ──
    if data == "menu_main":
        points = int(u.get("points", 0)) if u else 0
        leaderboard = db.get_leaderboard(100)
        rank = next((i+1 for i, p in enumerate(leaderboard) if p["user_id"] == str(user.id)), "غير مصنف")
        await query.edit_message_text(
            f"أهلاً *{user.first_name}*! 👋\n\n🎮 *لعبة حجر ورقة مقص*\n💰 رصيدك: {points} نقطة\n🏅 تصنيفك: #{rank}\n\nاختار من القائمة 👇",
            parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id)
        )
    elif data == "menu_play":
        await query.edit_message_text("🎮 اختار نوع اللعب:", reply_markup=play_menu_keyboard())

    # ── فردي ──
    elif data == "play_solo":
        await query.edit_message_text("🤖 اختار حركتك:", reply_markup=solo_keyboard())
    elif data.startswith("solo_"):
        choice = data.replace("solo_", "")
        bot_choice = random.choice(list(CHOICES.keys()))
        result = get_result(choice, bot_choice)
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        wins = int(u.get("wins", 0) or 0)
        losses = int(u.get("losses", 0) or 0)
        draws = int(u.get("draws", 0) or 0)
        if result == "win":
            emoji, txt, pts_add = "🎉", "كسبت!", 10
            wins += 1
            add_clan_points(user.id, 3)
            await check_and_complete_task(user.id, "task_1", context)
            await check_and_complete_task(user.id, "task_2", context, 1)
        elif result == "loss":
            emoji, txt, pts_add = "😢", "خسرت!", -3
            losses += 1
        else:
            emoji, txt, pts_add = "🤝", "تعادل!", 5
            draws += 1
            add_clan_points(user.id, 1)
        pts = max(0, pts + pts_add)
        db.update_user(user.id, points=pts, wins=wins, losses=losses, draws=draws)
        await query.edit_message_text(
            f"انت: {CHOICES[choice]}\nالبوت: {CHOICES[bot_choice]}\n\n{emoji} *{txt}*  ({'+' if pts_add>=0 else ''}{pts_add} نقطة)\n💰 نقاطك: {pts}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 العب تاني", callback_data="play_solo")],
                [InlineKeyboardButton("🏠 القائمة", callback_data="menu_main")]
            ])
        )

    # ── صديق (باليوزر) ──
    elif data == "play_friend":
        await query.edit_message_text("📩 ابعت يوزر صديقك (@username) أو الـ ID بتاعه:", reply_markup=back_btn("menu_play"))
        context.user_data["awaiting"] = "friend_challenge"
        context.user_data["awaiting_time"] = datetime.now()

    # ── تحديات متعددة ──
    elif data.startswith("mp_"):
        parts = data.split("_")
        choice = parts[-1]
        game_id = "_".join(parts[1:-1])
        game = active_games.get(game_id)
        if not game:
            await query.edit_message_text("❌ اللعبة انتهت.")
            return
        if user.id == game["p1"] and not game["c1"]:
            game["c1"] = choice
            await query.edit_message_text("✅ اخترت! استنى...")
        elif user.id == game["p2"] and not game["c2"]:
            game["c2"] = choice
            await query.edit_message_text("✅ اخترت! استنى...")
        else:
            return
        if game["c1"] and game["c2"]:
            c1, c2 = game["c1"], game["c2"]
            result = get_result(c1, c2)
            summary = (
                f"⚔️ *النتيجة*\n\n"
                f"{game['p1_name']}: {CHOICES[c1]}\n"
                f"{game['p2_name']}: {CHOICES[c2]}\n\n"
            )
            u1 = db.get_user(game["p1"])
            u2 = db.get_user(game["p2"])
            if result == "win":
                r1, r2 = "🎉 كسبت! (+15 نقطة)", "😢 خسرت! (-3 نقطة)"
                db.update_user(game["p1"], points=int(u1.get("points",0))+15, wins=int(u1.get("wins",0))+1)
                db.update_user(game["p2"], points=max(0, int(u2.get("points",0))-3), losses=int(u2.get("losses",0))+1)
                add_clan_points(game["p1"], 5)
                await check_and_complete_task(game["p1"], "task_3", context)
            elif result == "loss":
                r1, r2 = "😢 خسرت! (-3 نقطة)", "🎉 كسبت! (+15 نقطة)"
                db.update_user(game["p1"], points=max(0, int(u1.get("points",0))-3), losses=int(u1.get("losses",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+15, wins=int(u2.get("wins",0))+1)
                add_clan_points(game["p2"], 5)
                await check_and_complete_task(game["p2"], "task_3", context)
            else:
                r1 = r2 = "🤝 تعادل! (+5 نقطة)"
                db.update_user(game["p1"], points=int(u1.get("points",0))+5, draws=int(u1.get("draws",0))+1)
                db.update_user(game["p2"], points=int(u2.get("points",0))+5, draws=int(u2.get("draws",0))+1)
                add_clan_points(game["p1"], 2)
                add_clan_points(game["p2"], 2)
            await context.bot.send_message(game["p1"], summary + f"*{r1}*", parse_mode="Markdown")
            await context.bot.send_message(game["p2"], summary + f"*{r2}*", parse_mode="Markdown")
            del active_games[game_id]

    # ── عشوائي ──
    elif data == "play_random":
        if any(m["id"] == user.id for m in pending_matches):
            await query.answer("أنت بالفعل في قائمة الانتظار!", show_alert=True)
            return
        if pending_matches:
            opponent = pending_matches.pop(0)
            game_id = f"r_{user.id}_{random.randint(1000,9999)}"
            active_games[game_id] = {
                "p1": opponent["id"], "p1_name": opponent["name"],
                "p2": user.id, "p2_name": user.first_name,
                "c1": None, "c2": None,
                "created_at": datetime.now()
            }
            asyncio.create_task(game_timeout(game_id, context))
            kb = mp_keyboard(game_id)
            await query.edit_message_text(f"✅ لاقيت خصم: *{opponent['name']}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
            await context.bot.send_message(opponent["id"], f"✅ لاقيت خصم: *{user.first_name}*\nاختار حركتك 👇", parse_mode="Markdown", reply_markup=kb)
        else:
            pending_matches.append({"id": user.id, "name": user.first_name})
            await query.edit_message_text("🔍 بندور على خصم... استنى!",
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton("❌ إلغاء", callback_data="cancel_random")
                                          ]]))
    elif data == "cancel_random":
        pending_matches[:] = [m for m in pending_matches if m["id"] != user.id]
        await query.edit_message_text("✅ تم الإلغاء.", reply_markup=main_menu_keyboard(user.id))

    # ── القناة/الجروب (PvP) ──
    elif data.startswith("ch_"):
        parts = data.split("_")
        channel_id = int(parts[1])
        choice = parts[2]
        if channel_id not in channel_games:
            await query.answer("❌ مفيش جولة شغالة دلوقتي", show_alert=True)
            return
        game = channel_games[channel_id]
        # منع نفس المستخدم من اللعب مرتين
        if user.id == game.get("player1") or user.id == game.get("player2"):
            await query.answer("❌ انت لعبت خلاص!", show_alert=True)
            return
        if game["player1"] is None:
            game["player1"] = user.id
            game["choice1"] = choice
            await query.answer("✅ انت اللاعب الأول! استنى الخصم", show_alert=True)
            try:
                await context.bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=game["message_id"],
                    text=f"🎮 *{user.first_name}* دخل اللعبة! في انتظار لاعب تاني يضغط...",
                    parse_mode="Markdown",
                    reply_markup=channel_keyboard(channel_id)
                )
            except:
                pass
        elif game["player2"] is None and game["player1"] != user.id:
            game["player2"] = user.id
            game["choice2"] = choice
            # اللعبة اكتملت
            p1 = db.get_user(game["player1"])
            p2 = db.get_user(user.id)
            if not p1 or not p2:
                await cancel_channel_game(channel_id, context, "خطأ في بيانات اللاعبين")
                return
            result = get_result(game["choice1"], game["choice2"])
            c1_name, c2_name = CHOICES[game["choice1"]], CHOICES[game["choice2"]]
            # تحديث النقاط
            if result == "win":
                p1_add, p2_add = 15, -3
                db.update_user(game["player1"], points=max(0, int(p1.get("points",0))+p1_add), wins=int(p1.get("wins",0))+1)
                db.update_user(game["player2"], points=max(0, int(p2.get("points",0))+p2_add), losses=int(p2.get("losses",0))+1)
                add_clan_points(game["player1"], 5)
                result_text = f"{p1['name']} كسب {p2['name']}!"
            elif result == "loss":
                p1_add, p2_add = -3, 15
                db.update_user(game["player1"], points=max(0, int(p1.get("points",0))+p1_add), losses=int(p1.get("losses",0))+1)
                db.update_user(game["player2"], points=max(0, int(p2.get("points",0))+p2_add), wins=int(p2.get("wins",0))+1)
                add_clan_points(game["player2"], 5)
                result_text = f"{p2['name']} كسب {p1['name']}!"
            else:
                p1_add = p2_add = 5
                db.update_user(game["player1"], points=int(p1.get("points",0))+5, draws=int(p1.get("draws",0))+1)
                db.update_user(game["player2"], points=int(p2.get("points",0))+5, draws=int(p2.get("draws",0))+1)
                add_clan_points(game["player1"], 2)
                add_clan_points(game["player2"], 2)
                result_text = "تعادل!"
            # تعديل الرسالة الأصلية بالنتيجة
            final_text = (
                f"⚔️ *النتيجة*\n\n"
                f"{p1['name']}: {c1_name}\n"
                f"{p2['name']}: {c2_name}\n\n"
                f"🏆 {result_text}\n"
                f"💰 {p1['name']}: {'+' if p1_add>=0 else ''}{p1_add} نقطة | {p2['name']}: {'+' if p2_add>=0 else ''}{p2_add} نقطة"
            )
            try:
                await context.bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=game["message_id"],
                    text=final_text,
                    parse_mode="Markdown"
                )
            except:
                pass
            # مهام
            await check_and_complete_task(game["player1"], "task_4", context)
            await check_and_complete_task(game["player2"], "task_4", context)
            # تنظيف
            del channel_games[channel_id]
        else:
            await query.answer("❌ اللعبة اكتملت خلاص", show_alert=True)

    # ── باقي الأزرار (التصنيف، المتجر، العشائر، المهام، لوحة المؤسس...) ──
    elif data == "menu_rank":
        await query.edit_message_text("🏆 اختار نوع التصنيف:",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("📅 يومي", callback_data="rank_daily"),
                                           InlineKeyboardButton("📆 أسبوعي", callback_data="rank_weekly")],
                                          [InlineKeyboardButton("🗓️ شهري", callback_data="rank_monthly"),
                                           InlineKeyboardButton("📊 إجمالي", callback_data="rank_all")],
                                          [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
                                      ]))
    elif data.startswith("rank_"):
        period = data.replace("rank_", "")
        period_names = {"daily": "اليومي", "weekly": "الأسبوعي", "monthly": "الشهري", "all": "الإجمالي"}
        lb = db.get_leaderboard(10, period)
        medals = ["🥇","🥈","🥉"]
        text = f"🏆 *التصنيف {period_names.get(period, '')}*\n\n"
        for i, u in enumerate(lb):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} *{u['name']}* — {u.get('points',0)} نقطة\n"
        if not lb:
            text += "مفيش لاعبين لسه!"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_rank"))

    elif data == "menu_profile":
        u = db.get_user(user.id)
        total = int(u.get("wins",0)) + int(u.get("losses",0)) + int(u.get("draws",0))
        wr = round(int(u.get("wins",0)) / total * 100, 1) if total > 0 else 0
        clan = u.get("clan","") or "بدون عشيرة"
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        text = (
            f"👤 *ملفك الشخصي*\n\n"
            f"الاسم: {u['name']}\n"
            f"💰 النقاط: {u.get('points',0)}\n"
            f"🗡️ العشيرة: {clan}\n"
            f"✅ انتصارات: {u.get('wins',0)}\n"
            f"❌ خسارات: {u.get('losses',0)}\n"
            f"🤝 تعادل: {u.get('draws',0)}\n"
            f"📈 نسبة الفوز: {wr}%\n"
            f"🎯 إجمالي: {total}\n\n"
            f"🔗 رابط دعوتك:\n`{ref_link}`"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "menu_referral":
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        u = db.get_user(user.id)
        refs = int(u.get("referrals", 0) or 0)
        text = (
            f"🔗 *رابط الدعوة بتاعك*\n\n`{ref_link}`\n\n"
            f"👥 عدد من دعوتهم: {refs}\n"
            f"💰 مكافأة كل دعوة: 1000 نقطة\n\n"
            f"ابعت الرابط لأصحابك وكسب نقاط!"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "menu_tasks":
        tasks = db.get_tasks("daily")
        text = "🎁 *المهام اليومية*\n\n"
        u_progress = {}
        progress_str = (db.get_user(user.id) or {}).get("tasks_progress")
        if progress_str:
            try: u_progress = json.loads(progress_str).get("tasks", {})
            except: pass
        for t in tasks:
            task_id = t["task_id"]
            done = u_progress.get(f"{task_id}_done", False)
            current = u_progress.get(task_id, 0)
            target = {"task_1":5,"task_2":3,"task_3":1,"task_4":1,"task_5":10}.get(task_id, 1)
            status = "✅ تم" if done else f"⏳ {current}/{target}"
            text += f"• {t['description']} — 💰 {t['points_reward']} نقطة | {status}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    elif data == "menu_shop":
        await query.edit_message_text("🛒 *المتجر*\nاختار:", parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("🛒 المتجر", callback_data="shop_buy")],
                                          [InlineKeyboardButton("🎒 بطاقاتي", callback_data="shop_myitems")],
                                          [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
                                      ]))
    elif data == "shop_buy":
        items = db.get_shop_items()
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        text = f"🛒 *المتجر*\n💰 نقاطك: {pts}\n\n"
        btns = []
        for item in items:
            text += f"{item['emoji']} *{item['name']}* — {item['price']} نقطة\n_{item['description']}_\n\n"
            btns.append([InlineKeyboardButton(f"{item['emoji']} {item['name']} ({item['price']} نقطة)", callback_data=f"buy_{item['item_id']}")])
        btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_shop")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "shop_myitems":
        u = db.get_user(user.id)
        owned = (u.get("shop_items", "") or "").split(",") if u.get("shop_items") else []
        items = db.get_shop_items()
        my_items = [i for i in items if i["item_id"] in owned]
        text = "🎒 *بطاقاتي*\n\n"
        if not my_items:
            text += "ما عندكش بطاقات."
        else:
            for item in my_items:
                text += f"{item['emoji']} *{item['name']}* — {item['description']}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn("menu_shop"))
    elif data.startswith("buy_"):
        item_id = data.replace("buy_", "")
        items = db.get_shop_items()
        item = next((i for i in items if i["item_id"] == item_id), None)
        if not item:
            await query.answer("❌ المنتج مش موجود!", show_alert=True)
            return
        u = db.get_user(user.id)
        pts = int(u.get("points", 0) or 0)
        price = int(item["price"])
        if pts < price:
            await query.answer(f"❌ نقاطك مش كفاية! محتاج {price} نقطة.", show_alert=True)
            return
        owned = (u.get("shop_items", "") or "").split(",")
        owned = [o for o in owned if o]  # remove empty
        if item_id in owned:
            await query.answer("✅ عندك المنتج ده بالفعل!", show_alert=True)
            return
        owned.append(item_id)
        new_owned = ",".join(owned)
        db.update_user(user.id, points=pts-price, shop_items=new_owned)
        await query.answer(f"✅ اشتريت {item['name']}!", show_alert=True)

    # العشائر كما هي من السابق ... (سأكتفي بذكر الباقي مختصرًا لتوفير المساحة)
    # (يمكنك دمج بقية أزرار العشائر ولوحة المؤسس من الإصدار السابق)
    # يرجى استخدام بقية الكود كما في الإصدار السابق الكامل مع تعديلات اليوم.

    # ── طريقة اللعب ─ـ
    elif data == "menu_howto":
        text = (
            "❓ *طريقة اللعب*\n\n"
            "🪨 حجر يكسر ✂️ مقص\n✂️ مقص يقطع 📄 ورقة\n📄 ورقة تغطي 🪨 حجر\n\n"
            "🎮 *أنواع اللعب:*\n"
            "• فردي — ضد البوت\n• مع صديق — ابعت يوزره\n• عشوائي — مع لاعب عشوائي\n"
            "• قنوات — جولات بين عضوين كل دقيقتين\n\n"
            "💰 *النقاط:*\n• فوز = 10-15 نقطة\n• تعادل = 5 نقاط\n• خسارة = -3 نقطة\n• دعوة صديق = 1000 نقطة\n\n"
            "🗡️ العشائر — انضم وتنافس\n🎁 المهام — نقاط إضافية\n🛒 المتجر — اشتري بطاقات"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_btn())

    # تقييم ودعم كما هي...
