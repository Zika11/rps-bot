import json, logging, asyncio, random, sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils
import engine.game_engine as game_engine
import state as channel_state
import engine.users as users_engine
import engine.economy as economy
import handlers.channel_handlers as channel_h
import handlers.game_handlers as game_h
import handlers.shop_handlers as shop_h
import handlers.social_handlers as social_h
import handlers.misc_handlers as misc_h

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
        u = users_engine.get_user(user.id)
        if not u:
            users_engine.create_user(user.id, user.username, user.first_name)
            args = context.args
            if args and args[0].startswith("ref"):
                try:
                    ref_id = int(args[0][3:])
                    if ref_id != user.id:
                        ref_user = users_engine.get_user(ref_id)
                        if ref_user:
                            users_engine.update_user(ref_id,
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
            users_engine.update_user(user.id, last_login=datetime.now().isoformat(), login_streak=streak, days_since_register=days)
            await game_logic.check_achievements(user.id, context)
        text = f"أهلاً {user.first_name}! اختر من القائمة:"
        await update.message.reply_text(text, reply_markup=keyboards.main_menu())
    except Exception as e:
        logger.error(f"خطأ في أمر /start: {e}")
        await update.message.reply_text("حدث خطأ، الرجاء المحاولة لاحقاً.")

async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = users_engine.get_user(user.id)
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
    u = users_engine.get_user(user.id)
    refs = u.get("referrals", 0) if u else 0
    text = f"🔗 **رابط الإحالة الخاص بك:**\n{ref_link}\n\nعدد المدعوين: {refs}\nكل من ينضم عبر هذا الرابط يكسبك {config.REFERRAL_REWARD} نقطة."
    await update.message.reply_text(text)

async def wheel_spin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    u = users_engine.get_user(user.id)
    if u["gems"] < config.WHEEL_COST:
        await query.answer("تحتاج 5 جواهر لتدوير العجلة!")
        return
    users_engine.update_user(user.id, gems=u["gems"] - config.WHEEL_COST)
    reward_type, value = db.spin_wheel(user.id)
    if reward_type == "points":
        users_engine.update_user(user.id, points=u["points"] + value)
        msg = f"🎉 ربحت {value} نقطة!"
    elif reward_type == "gems":
        users_engine.update_user(user.id, gems=u["gems"] + value)
        msg = f"🎉 ربحت {value} جوهرة!"
    elif reward_type == "title":
        users_engine.update_user(user.id, title=value)
        msg = f"🎉 حصلت على لقب '{value}'!"
    elif reward_type == "theme":
        users_engine.update_user(user.id, theme=value)
        msg = f"🎉 حصلت على ثيم جديد!"
    elif reward_type == "treasure_box":
        sub = random.choice(config.TREASURE_REWARDS)
        if sub[0] == "points":
            users_engine.update_user(user.id, points=u["points"] + sub[1])
            msg = f"🎁 صندوق كنز: +{sub[1]} نقطة"
        elif sub[0] == "gems":
            users_engine.update_user(user.id, gems=u["gems"] + sub[1])
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
    u = users_engine.get_user(user.id)
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
    success, msg = economy.buy_item(user.id, item_type, item_id)
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

# ---------- معالج الأزرار الرئيسي (مُنسّق) ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    # الملاحة الأساسية
    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
    elif data == "delete_message":
        await query.delete_message()
    elif data == "game":
        await query.edit_message_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())
    elif data == "friends":
        await social_h.friends_menu_handler(update, context)
    elif data == "shop":
        await shop_h.shop_main(update, context)
    elif data == "clans":
        await social_h.clans_menu_handler(update, context)
    elif data == "tasks":
        tasks = db.get_tasks()
        u = users_engine.get_user(user.id)
        progress_data = u.get("tasks_progress")
        progress = {}
        if progress_data:
            try: progress = json.loads(progress_data)
            except: pass
        tasks_progress = progress.get("tasks", {})
        text = "📋 المهام:\n"
        for t in tasks:
            done = tasks_progress.get(f"{t['task_id']}_done", False)
            text += f"{'✅' if done else '⭕'} {t['description']} (+{t['points_reward']} نقطة)\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "achievements":
        all_ach = db.get_achievements()
        u = users_engine.get_user(user.id)
        earned = [a for a in (u.get("achievements") or "").split(",") if a]
        text = "🏅 الإنجازات:\n"
        for a in all_ach:
            icon = a["icon"] if a["ach_id"] in earned else "🔒"
            text += f"{icon} {a['name']} - {a['description']}\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "rating":
        top = db.get_top_ratings(10)
        text = "📊 أفضل 10 لاعبين:\n"
        for i, r in enumerate(top, 1):
            name = r["first_name"] or str(r["user_id"])
            rating_val = r["rating"]
            tier_name, tier_icon = config.get_tier_info(rating_val)
            text += f"{i}. {name} - {rating_val} ({tier_icon} {tier_name})\n"
        await query.edit_message_text(text, reply_markup=keyboards.back_button())
    elif data == "language":
        u = users_engine.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        users_engine.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))

    # أوضاع اللعب
    elif data == "solo":
        await game_h.solo_start(update, context)
    elif data == "random":
        await game_h.random_matchmaking(update, context)
    elif data == "friend":
        await game_h.friend_challenge_prompt(update, context)
    elif data == "channel":
        await query.edit_message_text("تحدي القنوات: أرسل هذه الرسالة في قناة/مجموعة واطلب من شخص الرد بـ /accept")
        context.user_data["channel_challenge_active"] = True
    elif data == "spock":
        from config import SPOCK_CHOICES
        buttons = [InlineKeyboardButton(icon, callback_data=f"spockpick_{key}") for key, icon in SPOCK_CHOICES.items()]
        await query.edit_message_text("اختر حركتك (Spock):", reply_markup=InlineKeyboardMarkup([buttons]))
    elif data == "story":
        await query.edit_message_text("وضع القصة قيد التطوير...", reply_markup=keyboards.back_button())

    # ألعاب المجموعة
    elif data.startswith("group_solo_"):
        chat_id = int(data.split("_")[-1])
        game_id = state.start_solo_game(user.id)
        state.group_solo_games[user.id] = {"chat_id": chat_id, "game_id": game_id}
        keyboard = keyboards.group_choice_buttons(chat_id, user.id, game_id)
        sent = await context.bot.send_message(chat_id, f"🎮 {user.first_name} يلعب ضد البوت. اختر حركتك:", reply_markup=keyboard)
        state.group_solo_games[user.id]["message_id"] = sent.message_id
        await query.answer("ظهرت أزرار الاختيار في المجموعة.")
    elif data.startswith("group_random_join_"):
        chat_id = int(data.split("_")[-1])
        async with state.group_session_lock:
            session = state.group_game_sessions.get(chat_id)
            if not session:
                await query.answer("انتهت الجلسة الحالية. انتظر الجولة القادمة.")
                return
            if user.id in session["players"]:
                await query.answer("أنت مشترك بالفعل!")
                return
            session["players"].add(user.id)
            await query.answer("تم تسجيلك في اللعبة العشوائية! 🎲")
    elif data.startswith("group_friend_"):
        await query.answer("استخدم /challenge في المجموعة.")
    elif data.startswith("group_open_"):
        chat_id = int(data.split("_")[-1])
        await game_h.start_open_challenge(update, context, chat_id)
    elif data.startswith("accept_open_"):
        chat_id = int(data.split("_")[-1])
        await game_h.accept_open_challenge(update, context, chat_id)
    elif data.startswith("spectate_"):
        chat_id = int(data.split("_")[-1])
        await misc_h.spectate_room_create(update, context)

    # اختيار الحركات
    elif data.startswith("pick_"):
        parts = data.split("_", 2)
        if len(parts) < 3: return
        game_type = parts[1]
        tail = parts[2]
        try:
            game_id, move = tail.rsplit("_", 1)
        except ValueError:
            return
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        if game_type == "solo":
            await game_h.process_solo_pick(update, context, move, game_id)
        elif game_type == "random":
            await game_h.process_random_pick(update, context, move, game_id)
        elif game_type == "tournament":
            try:
                tour_id = game_id
                match_index, move = tail.rsplit("_", 1)
                match_index = int(match_index)
            except:
                return
            await game_h.process_tournament_pick(update, context, move, tour_id, match_index)
        elif game_type == "spectate":
            await game_h.process_spectate_pick(update, context, move, game_id)
        elif game_type == "mass":
            chat_id = int(game_id)
            db.add_mass_pick(chat_id, user.id, move)
            await query.edit_message_text("تم تسجيل حركتك في المعركة الجماعية!")
    elif data.startswith("group_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        player_id = int(parts[4])
        game_id = parts[5]
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        await game_h.process_group_solo_pick(update, context, move, chat_id, player_id, game_id)
    elif data.startswith("spockpick_"):
        move = data.split("_", 1)[1]
        await game_h.process_spock_move(update, context, move)
    elif data.startswith("open_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await game_h.process_open_pick(update, context, move, chat_id)
    elif data.startswith("open_accept_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await game_h.process_open_acceptor_pick(update, context, move, chat_id)

    # الميزات الجديدة
    elif data == "wheel":
        await query.edit_message_text("🎡 عجلة الحظ! تدوير بـ 5 جواهر.", reply_markup=keyboards.wheel_button())
    elif data == "wheel_spin":
        await wheel_spin_handler(update, context)
    elif data == "battlepass":
        await battlepass_command(update, context)
    elif data == "battlepass_progress":
        await battlepass_command(update, context)

    # المتجر والاقتصاد
    elif data == "frames_shop":
        await shop_h.frames_shop(update, context)
    elif data.startswith("buy_frame_"):
        await shop_h.buy_frame(update, context)
    elif data == "market":
        await shop_h.market_menu(update, context)
    elif data == "market_browse":
        await shop_h.market_browse(update, context)
    elif data.startswith("market_buy_"):
        await shop_h.market_buy(update, context)
    elif data == "market_sell":
        await shop_h.market_sell_prompt(update, context)
    elif data == "abilities_shop":
        await shop_h.abilities_shop(update, context)
    elif data.startswith("buy_ability_"):
        await shop_h.buy_ability(update, context)
    elif data == "shop_cards":
        await shop_h.shop_cards(update, context)
    elif data.startswith("buy_") and "title" not in data and "theme" not in data and "frame" not in data and "ability" not in data:
        await shop_h.buy_item(update, context)
    elif data == "shop_titles":
        await shop_h.shop_titles(update, context)
    elif data.startswith("buy_title_"):
        await shop_h.buy_title(update, context)
    elif data == "shop_themes":
        await shop_h.shop_themes(update, context)
    elif data.startswith("buy_theme_"):
        await shop_h.buy_theme(update, context)
    elif data == "treasure_box":
        await shop_h.treasure_box(update, context)

    # العشائر
    elif data == "clan_create":
        await social_h.clan_create(update, context)
    elif data == "clan_join":
        await social_h.clan_join(update, context)
    elif data == "clan_ranking":
        await social_h.clan_ranking(update, context)
    elif data == "clan_treasury":
        await social_h.clan_treasury_menu(update, context)
    elif data.startswith("treasury_view_"):
        await social_h.treasury_view(update, context)
    elif data.startswith("treasury_donate_points_"):
        await social_h.treasury_donate_points(update, context)
    elif data.startswith("treasury_donate_gems_"):
        await social_h.treasury_donate_gems(update, context)
    elif data.startswith("treasury_upgrade_"):
        await social_h.treasury_upgrade(update, context)
    elif data.startswith("do_upgrade_"):
        await social_h.do_upgrade(update, context)
    elif data == "clan_war_info":
        await social_h.clan_war_info(update, context)

    # الأصدقاء
    elif data == "add_friend":
        await social_h.add_friend_start(update, context)
    elif data == "friend_requests":
        await social_h.friend_requests_list(update, context)
    elif data == "friend_list":
        await social_h.friend_list_display(update, context)
    elif data.startswith("accept_friend_") or data.startswith("reject_friend_"):
        await social_h.handle_friend_action(update, context)

    # القناة والأزرار التفاعلية
    elif data.startswith("channel_play_"):
        await channel_h.channel_play(update, context)
    elif data.startswith("weekly_leaderboard_"):
        await channel_h.weekly_leaderboard(update, context)
    elif data == "profile":
        await me_command(update, context)
    elif data.startswith("ch_leaderboard_"):
        chat_id = int(data.split("_")[-1])
        top = db.get_channel_leaderboard(chat_id, 10)
        text = "🏆 **أفضل 10 لاعبين في القناة:**\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['first_name']} - {r['points']} نقطة\n"
        await query.edit_message_text(text)

    # التوقعات
    elif data.startswith("predict_"):
        parts = data.split("_")
        chat_id = int(parts[1])
        predicted_move = parts[2]
        if predicted_move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        if await channel_state.is_spam_vote(chat_id, user.id):
            await query.answer("تم استلام توقعك بالفعل!")
            return
        success = await game_engine.predict(chat_id, user.id, predicted_move)
        if success:
            await query.answer("تم تسجيل توقعك! 🔮")
        else:
            await query.answer("التوقع غير متاح الآن.")

    # Admin, World Boss, Tournament, Spectator
    elif data == "admin":
        await admin_panel(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_broadcast":
        await admin_broadcast_prompt(update, context)
    elif data == "admin_set_points":
        await admin_set_points_prompt(update, context)
    elif data == "admin_channels":
        await admin_channels_list(update, context)
    elif data == "admin_reset":
        await admin_reset_games(update, context)
    elif data == "admin_start_channel":
        await channel_h.admin_start_channel_prompt(update, context)
    elif data == "admin_stop_channel":
        await channel_h.admin_stop_channel_prompt(update, context)
    elif data == "boss_attack":
        await misc_h.boss_attack(update, context)
    elif data == "boss_status":
        await misc_h.boss_command(update, context)
    elif data == "tournament":
        await misc_h.tournament_menu(update, context)
    elif data.startswith("join_tournament_"):
        await misc_h.join_tournament_handler(update, context)
    elif data.startswith("accept_challenge_"):
        await misc_h.accept_challenge(update, context)
    elif data.startswith("reject_challenge_"):
        await misc_h.reject_challenge(update, context)
    elif data.startswith("spectate_join_"):
        await misc_h.spectate_join(update, context)

# ---------- Admin Panel ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total_users = len(users_engine.get_all_user_ids())
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
            for uid in users_engine.get_all_user_ids():
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
                users_engine.update_user(uid, points=pts, gems=gems)
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
            target = users_engine.get_user_by_username(username)
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
            users_engine.update_user(uid, points=users_engine.get_user(uid)["points"] + config.MASS_BATTLE_REWARD[0],
                           gems=users_engine.get_user(uid).get("gems",0) + config.MASS_BATTLE_REWARD[1])
        winner_names = ", ".join([users_engine.get_user(uid)["first_name"] for uid in winners[:5]])
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
    app.add_handler(CallbackQueryHandler(channel_h.handle_move, pattern="^move_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_stuck_games())
    loop.create_task(auto_drops(app))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
