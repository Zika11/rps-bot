import json, logging, asyncio, random, sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils
import engine.game_engine as game_engine
import state as channel_state
import handlers.channel_handlers as channel_h
import handlers.game_handlers as game_h
import handlers.shop_handlers as shop_h
import handlers.social_handlers as social_h
import handlers.misc_handlers as misc_h

# استيراد معالجات الأزرار الجديدة
from handlers.callbacks import navigation, game, channel, shop, social, admin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.init_db()

# ---------- المهام الدورية (خلفية) ----------
async def cleanup_stuck_games():
    while True:
        await asyncio.sleep(60)
        try:
            conn = sqlite3.connect(config.DB_NAME)
            cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
            conn.execute("DELETE FROM active_games WHERE created_at < ?", (cutoff,))
            conn.execute("DELETE FROM pending_matches")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطأ في تنظيف الألعاب: {e}")

async def auto_drops(app):
    while True:
        await asyncio.sleep(600)
        if random.random() < config.DROP_CHANCE:
            for chat_id in list(channel_state.channel_settings.keys()):
                reward = random.choice(config.DROP_REWARDS)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]])
                try:
                    await app.bot.send_message(chat_id, "💥 صندوق مفاجئ! أول واحد يضغط يربح:", reply_markup=keyboard)
                except:
                    pass

# ---------- أوامر أساسية ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        u = db.get_user(user.id)
        if not u:
            db.create_user(user.id, user.username, user.first_name)
            args = context.args
            if args and args[0].startswith("ref"):
                try:
                    ref_id = int(args[0][3:])
                    if ref_id != user.id:
                        ref_user = db.get_user(ref_id)
                        if ref_user:
                            db.update_user(ref_id,
                                           referrals=int(ref_user.get("referrals",0)) + 1,
                                           points=int(ref_user.get("points",0)) + config.REFERRAL_REWARD)
                            await context.bot.send_message(ref_id, f"🎉 {user.first_name} انضم عبر رابط الإحالة الخاص بك! ربحت {config.REFERRAL_REWARD} نقطة.")
                except:
                    pass
        else:
            today = date.today().isoformat()
            last = u.get("last_login")
            streak = int(u.get("login_streak",0))
            if last:
                last_date = date.fromisoformat(last[:10])
                diff = (date.today() - last_date).days
                if diff == 1: streak += 1
                elif diff > 1: streak = 1
            else:
                streak = 1
            days = (date.today() - date.fromisoformat(u["registered_date"][:10])).days if u.get("registered_date") else 0
            db.update_user(user.id, last_login=datetime.now().isoformat(), login_streak=streak, days_since_register=days)
            await game_logic.check_achievements(user.id, context)
        text = f"أهلاً {user.first_name}! اختر من القائمة:"
        await update.message.reply_text(text, reply_markup=keyboards.main_menu())
    except Exception as e:
        logger.error(f"خطأ في أمر /start: {e}")
        await update.message.reply_text("حدث خطأ، الرجاء المحاولة لاحقاً.")

async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        await update.message.reply_text("سجّل دخولك أولاً باستخدام /start")
        return
    rating = db.get_user_rating(user.id) or config.DEFAULT_RATING
    tier_name, tier_icon = config.get_tier_info(rating)
    frame = db.get_user_frame(user.id)
    frame_icon = config.AVATAR_FRAMES.get(frame, "⬛")
    wins = u.get("wins", 0)
    losses = u.get("losses", 0)
    draws = u.get("draws", 0)
    total = wins + losses + draws
    winrate = f"{(wins / total * 100):.1f}%" if total > 0 else "0%"
    xp = u.get("xp", 0)
    level = u.get("level", 1)
    level_title, level_icon = "مبتدئ", "🥉"
    for lvl in sorted(config.LEVEL_TITLES.keys(), reverse=True):
        if level >= lvl:
            level_title, level_icon = config.LEVEL_TITLES[lvl]
            break
    profile_text = (
        f"{frame_icon} {u['first_name']}\n"
        f"🏅 التصنيف: {rating} نقطة\n"
        f"{tier_icon} الرانك: {tier_name}\n"
        f"⬆️ المستوى: {level} {level_icon} ({level_title})\n"
        f"⚔️ الإنتصارات: {wins}\n"
        f"💀 الهزائم: {losses}\n"
        f"🤝 التعادلات: {draws}\n"
        f"📈 نسبة الفوز: {winrate}\n"
        f"💎 الجواهر: {u.get('gems', 0)}\n"
        f"🎖 الإنجازات: {len((u.get('achievements') or '').split(',')) if u.get('achievements') else 0}\n"
        f"🏘️ العشيرة: {u.get('clan', 'لا يوجد')}"
    )
    await update.message.reply_text(profile_text)

# ---------- الأوامر الجديدة ----------
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    result = db.claim_daily(user.id)
    if result is None:
        await update.message.reply_text("لقد حصلت على مكافأتك اليومية بالفعل! ⏳")
        return
    day = result["day"]
    points = result["points"]
    gems = result["gems"]
    text = f"🎁 **مكافأة اليوم {day}**\n+{points} نقطة"
    if gems > 0:
        text += f" +{gems} جوهرة"
    await update.message.reply_text(text)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref{user.id}"
    u = db.get_user(user.id)
    refs = u.get("referrals", 0) if u else 0
    text = f"🔗 **رابط الإحالة الخاص بك:**\n{ref_link}\n\nعدد المدعوين: {refs}\nكل من ينضم عبر هذا الرابط يكسبك {config.REFERRAL_REWARD} نقطة."
    await update.message.reply_text(text)

async def wheel_spin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = db.get_user(user.id)
    if u["gems"] < config.WHEEL_COST:
        await query.answer("تحتاج 5 جواهر لتدوير العجلة!")
        return
    db.update_user(user.id, gems=u["gems"] - config.WHEEL_COST)
    reward_type, value = db.spin_wheel(user.id)
    if reward_type == "points":
        db.update_user(user.id, points=u["points"] + value)
        msg = f"🎉 ربحت {value} نقطة!"
    elif reward_type == "gems":
        db.update_user(user.id, gems=u["gems"] + value)
        msg = f"🎉 ربحت {value} جوهرة!"
    elif reward_type == "title":
        db.update_user(user.id, title=value)
        msg = f"🎉 حصلت على لقب '{value}'!"
    elif reward_type == "theme":
        db.update_user(user.id, theme=value)
        msg = f"🎉 حصلت على ثيم جديد!"
    elif reward_type == "treasure_box":
        sub = random.choice(config.TREASURE_REWARDS)
        if sub[0] == "points":
            db.update_user(user.id, points=u["points"] + sub[1])
            msg = f"🎁 صندوق كنز: +{sub[1]} نقطة"
        elif sub[0] == "gems":
            db.update_user(user.id, gems=u["gems"] + sub[1])
            msg = f"🎁 صندوق كنز: +{sub[1]} جوهرة"
        else:
            msg = "🎁 صندوق كنز!"
    db.add_battle_pass_xp(user.id, 5)
    await query.edit_message_text(f"🎡 العجلة توقفت عند: {msg}", reply_markup=keyboards.wheel_button())

async def battlepass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bp = db.get_battle_pass(user.id)
    level = bp["level"]
    xp = bp["xp"]
    required_xp = level * config.BATTLE_PASS_XP_PER_LEVEL
    text = f"📊 **Battle Pass - الموسم 1**\n"
    text += f"المستوى: {level}/{config.MAX_BATTLE_PASS_LEVEL}\n"
    text += f"الخبرة: {xp}/{required_xp}\n\n"
    for lvl in range(1, min(level+1, config.MAX_BATTLE_PASS_LEVEL+1)):
        rewards = config.BATTLE_PASS_REWARDS.get(lvl, {})
        free = rewards.get("free")
        prem = rewards.get("premium")
        text += f"م {lvl}: مجاني - {free[0]} {free[1] if free[1] else ''}"
        if prem:
            text += f" | مميز - {prem[0]} {prem[1] if prem[1] else ''}"
        text += "\n"
    await update.message.reply_text(text, reply_markup=keyboards.battlepass_button())

async def market_sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 4:
        await update.message.reply_text("استخدم: /sell <نوع> <معرف> <سعر> <عملة points/gems>\nمثال: /sell frame gold 300 points")
        return
    item_type = args[0]
    item_id = args[1]
    price = int(args[2])
    price_type = args[3].lower()
    if price_type not in ["points", "gems"]:
        await update.message.reply_text("العملة يجب أن تكون points أو gems")
        return
    owned = False
    u = db.get_user(user.id)
    if item_type == "theme" and u.get("theme") == item_id:
        owned = True
    elif item_type == "title" and u.get("title") == item_id:
        owned = True
    elif item_type == "frame":
        conn = sqlite3.connect(config.DB_NAME)
        row = conn.execute("SELECT owned_frames FROM user_frames WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        if row and item_id in row[0].split(","):
            owned = True
    elif item_type == "booster":
        owned_items = (u.get("shop_items") or "").split(",")
        if item_id in owned_items:
            owned = True
    if not owned:
        await update.message.reply_text("لا تملك هذا العنصر.")
        return
    db.create_listing(user.id, item_type, item_id, price_type, price)
    await update.message.reply_text(f"تم عرض {item_type} {item_id} للبيع بـ {price} {price_type}")

# ---------- اقتصاد (Shop / Buy) ----------
async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛒 **متجر RPS**\n\n"
        "لشراء عنصر استخدم الأمر:\n"
        "/buy <نوع> <معرف>\n\n"
        "الأنواع المتاحة:\n"
        "- booster (مثل: double_points_1h)\n"
        "- title (مثل: title_king)\n"
        "- theme (مثل: theme_2)\n"
        "- frame (مثل: gold)\n"
        "- ability (مثل: shield)\n\n"
        "أمثلة:\n"
        "/buy booster double_points_1h\n"
        "/buy title title_legend\n"
        "/buy frame gold"
    )
    await update.message.reply_text(text)

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("استخدم: /buy <نوع> <معرف>\nمثال: /buy frame gold")
        return
    item_type = args[0].lower()
    item_id = args[1]
    success, msg = db.buy_item(user.id, item_type, item_id)
    await update.message.reply_text(msg)

# ---------- أمر الويب ----------
async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    base_url = "https://rps-bot-six.vercel.app"
    web_link = f"{base_url}/?chat={chat_id}"
    await update.message.reply_text(f"🔗 رابط اللعبة على الويب:\n{web_link}")

# ---------- أمر /game لفتح Mini App ----------
async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اضغط للعب:", reply_markup=keyboards.mini_app_button())

# ---------- Admin Panel (للأوامر) ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())

# دوال الإدارة (مستوردة من bot.py القديم لكن نتركها هنا للاستخدام المباشر)
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total_users = len(db.get_all_user_ids())
    conn = sqlite3.connect(config.DB_NAME)
    total_games = conn.execute("SELECT COUNT(*) FROM active_games").fetchone()[0]
    total_clans = conn.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
    conn.close()
    text = (f"👥 المستخدمين: {total_users}\n"
            f"🎮 المباريات النشطة: {total_games}\n"
            f"🏰 العشائر: {total_clans}")
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل الرسالة التي تريد إرسالها للجميع:", reply_markup=keyboards.back_button("admin"))
    context.user_data["awaiting_broadcast"] = True

async def admin_set_points_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("أرسل:\n`user_id points gems`", reply_markup=keyboards.back_button("admin"))
    context.user_data["awaiting_set_points"] = True

async def admin_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    async with channel_state.channel_settings_lock:
        chans = list(channel_state.channel_settings.keys())
    text = "القنوات المفعلة:\n" + "\n".join([str(c) for c in chans]) if chans else "لا توجد"
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_reset_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect(config.DB_NAME)
    conn.execute("DELETE FROM active_games")
    conn.execute("DELETE FROM pending_matches")
    conn.commit()
    conn.close()
    await query.answer("تم مسح المباريات العالقة.")

# ---------- معالج النصوص ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text.strip() if update.message.text else ""
    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower()
    entities = update.message.entities or update.message.caption_entities

    if entities and chat_type in ["group", "supergroup"]:
        for ent in entities:
            if ent.type == MessageEntity.MENTION:
                mention = msg[ent.offset:ent.offset+ent.length]
                if mention.lower() == f"@{bot_username}":
                    await handle_group_mention(update, context, update.effective_chat.id)
                    return
            elif ent.type == MessageEntity.TEXT_MENTION:
                if ent.user.id == context.bot.id:
                    await handle_group_mention(update, context, update.effective_chat.id)
                    return

    if chat_type == "private":
        if context.user_data.get("awaiting_broadcast"):
            broadcast_msg = update.message.text
            success, fail = 0, 0
            for uid in db.get_all_user_ids():
                try:
                    await context.bot.send_message(uid, broadcast_msg)
                    success += 1
                except:
                    fail += 1
            await update.message.reply_text(f"تم: {success} نجاح, {fail} فشل")
            context.user_data["awaiting_broadcast"] = False
            return

        if context.user_data.get("awaiting_set_points"):
            try:
                parts = update.message.text.split()
                uid = int(parts[0])
                pts = int(parts[1])
                gems = int(parts[2])
                db.update_user(uid, points=pts, gems=gems)
                await update.message.reply_text("تم التحديث")
            except:
                await update.message.reply_text("صيغة خاطئة")
            context.user_data["awaiting_set_points"] = False
            return

        if context.user_data.get("awaiting_start_channel"):
            await channel_h.process_start_channel_text(update, context)
            return

        if context.user_data.get("awaiting_stop_channel"):
            await channel_h.process_stop_channel_text(update, context)
            return

        if len(msg) > 100:
            await update.message.reply_text("النص طويل جداً.")
            return

        if context.user_data.get("awaiting_friend_username"):
            await social_h.process_friend_username(update, context)
        elif context.user_data.get("awaiting_clan_name"):
            await social_h.process_clan_name(update, context)
        elif context.user_data.get("awaiting_join_clan"):
            await social_h.process_join_clan(update, context)
        elif context.user_data.get("awaiting_friend_challenge"):
            username = msg.lstrip("@")
            target = db.get_user_by_username(username)
            if not target:
                await update.message.reply_text("المستخدم غير موجود.")
            else:
                await update.message.reply_text(f"تحدي صديق قيد التطوير (سيتم إعلام {target['first_name']}).")
            context.user_data["awaiting_friend_challenge"] = False

async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    async with state.group_session_lock:
        if chat_id in state.group_game_sessions: return
    await context.bot.send_message(chat_id, "مرحباً بك في RPS Arena!", reply_markup=keyboards.channel_main_menu(chat_id))

# ---------- أوامر القناة (قديمة، للاحتياط) ----------
async def start_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("استخدم: /start_channel @channelname interval=60 ttl=30")
        return
    channel_name = args[0]
    interval = 60
    ttl = 30
    for a in args[1:]:
        if a.startswith("interval="): interval = int(a.split("=")[1])
        elif a.startswith("ttl="): ttl = int(a.split("=")[1])
    try:
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id
        async with channel_state.channel_settings_lock:
            if chat_id in channel_state.channel_settings:
                old_task = channel_state.channel_settings[chat_id].get("task")
                if old_task: old_task.cancel()
                del channel_state.channel_settings[chat_id]
        task = asyncio.create_task(channel_h.channel_voting_loop(chat_id, context))
        async with channel_state.channel_settings_lock:
            channel_state.channel_settings[chat_id] = {"interval": interval, "ttl": ttl, "task": task}
        await update.message.reply_text(f"تم بدء جولات التصويت التلقائي في {chat.title}\nالفاصل: {interval}s | حذف الرسالة: {ttl}s")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

async def stop_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("استخدم: /stop_channel @channelname")
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        chat_id = chat.id
        async with channel_state.channel_settings_lock:
            if chat_id in channel_state.channel_settings:
                task = channel_state.channel_settings[chat_id].get("task")
                if task: task.cancel()
                del channel_state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف جولات التصويت في {chat.title}")
            else:
                await update.message.reply_text("لا توجد جولات نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ---------- الأوامر الجماعية ----------
async def massbattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    battle_id = db.start_mass_battle(chat_id)
    await context.bot.send_message(chat_id, "⚡ معركة جماعية! اختر حركتك خلال 30 ثانية:",
                                   reply_markup=keyboards.mass_battle_start_button(chat_id))
    await asyncio.sleep(config.MASS_BATTLE_DURATION)
    winners = db.get_mass_battle_results(battle_id)
    if winners:
        for uid in winners:
            user_data = db.get_user(uid)
            db.update_user(uid, points=user_data["points"] + config.MASS_BATTLE_REWARD[0],
                           gems=user_data.get("gems",0) + config.MASS_BATTLE_REWARD[1])
        winner_names = ", ".join([db.get_user(uid)["first_name"] for uid in winners[:5]])
        await context.bot.send_message(chat_id, f"🎉 انتهت المعركة! الفائزون: {winner_names} (+{config.MASS_BATTLE_REWARD[0]} نقطة، +{config.MASS_BATTLE_REWARD[1]} جوهرة)")
    else:
        await context.bot.send_message(chat_id, "لم ينضم أحد للمعركة!")

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id): return
    chat_id = update.effective_chat.id
    reward = random.choice(config.DROP_REWARDS)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]])
    await context.bot.send_message(chat_id, "💥 صندوق مفاجئ! أول واحد يضغط يربح:", reply_markup=keyboard)

async def teambattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("استخدم: /teambattle اسم_الفريق_الأحمر اسم_الفريق_الأزرق")
        return
    team1, team2 = context.args[0], context.args[1]
    battle_id = db.create_team_battle(chat_id, team1, team2)
    await update.message.reply_text(f"🔴 {team1} vs {team2} 🔵\nاضغط للانضمام لفريق:",
                                   reply_markup=keyboards.team_battle_team_buttons(battle_id))
    await asyncio.sleep(60)
    conn = sqlite3.connect(config.DB_NAME)
    battle = conn.execute("SELECT * FROM team_battles WHERE battle_id=?", (battle_id,)).fetchone()
    if not battle: return
    chat_id = battle["chat_id"]
    team1_players = db.get_team_players(battle_id, "red")
    team2_players = db.get_team_players(battle_id, "blue")
    for uid in team1_players:
        await context.bot.send_message(uid, "اختر حركتك لمعركة الفريق:", reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}"))
    for uid in team2_players:
        await context.bot.send_message(uid, "اختر حركتك لمعركة الفريق:", reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}"))
    state.team_battle_moves[battle_id] = {}
    await asyncio.sleep(60)
    team1_score, team2_score = 0, 0
    if battle_id in state.team_battle_moves:
        for uid, move in state.team_battle_moves[battle_id].items():
            if uid in team1_players:
                team1_score += 1 if move == "rock" else 0
            elif uid in team2_players:
                team2_score += 1 if move == "rock" else 0
    winner_team = "red" if team1_score > team2_score else "blue" if team2_score > team1_score else "draw"
    await context.bot.send_message(chat_id, f"نتيجة المعركة: {'🔴 فاز الفريق الأحمر' if winner_team=='red' else '🔵 فاز الفريق الأزرق' if winner_team=='blue' else 'تعادل'}")

# ---------- تشغيل البوت ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("battlepass", battlepass_command))
    app.add_handler(CommandHandler("sell", market_sell_command))
    app.add_handler(CommandHandler("shop", shop_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("season", misc_h.season_command))
    app.add_handler(CommandHandler("boss", misc_h.boss_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("start_channel", start_channel_command))
    app.add_handler(CommandHandler("stop_channel", stop_channel_command))
    app.add_handler(CommandHandler("challenge", misc_h.challenge_start))
    app.add_handler(CommandHandler("massbattle", massbattle_command))
    app.add_handler(CommandHandler("drop", drop_command))
    app.add_handler(CommandHandler("teambattle", teambattle_command))
    app.add_handler(CommandHandler("web", web_command))
    app.add_handler(CommandHandler("game", game_command))
    
    # معالجات الأزرار - كل بادئة تذهب لملفها الخاص
    app.add_handler(CallbackQueryHandler(channel_h.handle_move, pattern="^move_"))
    app.add_handler(CallbackQueryHandler(navigation.handle, pattern="^(back_main|delete_message|language|profile|tasks|achievements|rating)"))
    app.add_handler(CallbackQueryHandler(game.handle, pattern="^(game|solo|random|friend|channel|spock|story|pick_|group_pick_|spockpick_|open_pick_|open_accept_|group_solo_|group_random_join_|group_friend_|group_open_|accept_open_|spectate_)"))
    app.add_handler(CallbackQueryHandler(channel.handle, pattern="^(channel_play_|weekly_leaderboard_|ch_leaderboard_|predict_)"))
    app.add_handler(CallbackQueryHandler(shop.handle, pattern="^(shop|frames_shop|buy_frame_|market|market_browse|market_buy_|market_sell|abilities_shop|buy_ability_|shop_cards|buy_|shop_titles|buy_title_|shop_themes|buy_theme_|treasure_box|wheel|wheel_spin|battlepass|battlepass_progress)"))
    app.add_handler(CallbackQueryHandler(social.handle, pattern="^(friends|add_friend|friend_requests|friend_list|accept_friend_|reject_friend_|clans|clan_create|clan_join|clan_ranking|clan_treasury|treasury_view_|treasury_donate_points_|treasury_donate_gems_|treasury_upgrade_|do_upgrade_|clan_war_info)"))
    app.add_handler(CallbackQueryHandler(admin.handle, pattern="^(admin|admin_stats|admin_broadcast|admin_set_points|admin_channels|admin_reset|admin_start_channel|admin_stop_channel|boss_attack|boss_status|tournament|join_tournament_|accept_challenge_|reject_challenge_|spectate_join_)"))
    
    # معالج النصوص
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # المهام الخلفية
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_stuck_games())
    loop.create_task(auto_drops(app))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
