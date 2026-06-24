import json, logging, asyncio, random, sqlite3
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils, handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.init_db()

# ---------- المهام الدورية (خلفية) ----------
async def cleanup_stuck_games():
    while True:
        await asyncio.sleep(60)
        try:
            conn = sqlite3.connect("rps_bot.db")
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
            for chat_id in list(state.channel_settings.keys()):
                reward = random.choice(config.DROP_REWARDS)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]])
                try:
                    await app.bot.send_message(chat_id, "💥 صندوق مفاجئ! أول واحد يضغط يربح:", reply_markup=keyboard)
                except:
                    pass

# ---------- أوامر أساسية ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                                       points=int(ref_user.get("points",0)) + 50)
                        await context.bot.send_message(ref_id, f"🎉 {user.first_name} انضم عبر رابط الإحالة الخاص بك! ربحت 50 نقطة.")
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
    profile_text = (
        f"{frame_icon} {u['first_name']}\n"
        f"🏅 التصنيف: {rating} نقطة\n"
        f"{tier_icon} الرانك: {tier_name}\n"
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
    text = f"🔗 **رابط الإحالة الخاص بك:**\n{ref_link}\n\nعدد المدعوين: {refs}\nكل من ينضم عبر هذا الرابط يكسبك 50 نقطة."
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
        conn = sqlite3.connect("rps_bot.db")
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

# ---------- معالج الأزرار الرئيسي ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
    elif data == "delete_message":
        await query.delete_message()
    elif data == "game":
        await query.edit_message_text("اختر نمط اللعب:", reply_markup=keyboards.game_mode_menu())
    elif data == "friends":
        await handlers.friends_menu_handler(update, context)
    elif data == "shop":
        await handlers.shop_main(update, context)
    elif data == "clans":
        await handlers.clans_menu_handler(update, context)
    elif data == "tasks":
        tasks = db.get_tasks()
        u = db.get_user(user.id)
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
        u = db.get_user(user.id)
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
        u = db.get_user(user.id)
        new_lang = "en" if u["language"] == "ar" else "ar"
        db.update_user(user.id, language=new_lang)
        await query.edit_message_text("تم تغيير اللغة", reply_markup=keyboards.main_menu(new_lang))

    # أوضاع اللعب الخاص
    elif data == "solo":
        game_id = state.start_solo_game(user.id)
        await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons(f"solo_{game_id}"))
    elif data == "random":
        result = await state.add_pending(user.id)
        if result is None:
            await query.answer("أنت بالفعل في قائمة الانتظار أو مشغول بلعبة!")
        elif result is True:
            await query.edit_message_text("بانتظار لاعب آخر...")
        else:
            opp_id = result
            game = state.get_game_by_player(user.id)
            if game:
                await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))
                await context.bot.send_message(opp_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons(f"random_{game['game_id']}"))
    elif data == "friend":
        await query.edit_message_text("أرسل معرف الصديق (@username) لتحديه:")
        context.user_data["awaiting_friend_challenge"] = True
    elif data == "channel":
        await handlers.channel_challenge(update, context)
    elif data == "spock":
        await handlers.spock_mode(update, context)
    elif data == "story":
        await handlers.story_mode(update, context)

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
        await start_open_challenge(update, context, chat_id)
    elif data.startswith("accept_open_"):
        chat_id = int(data.split("_")[-1])
        await accept_open_challenge(update, context, chat_id)
    elif data.startswith("spectate_"):
        chat_id = int(data.split("_")[-1])
        await handlers.spectate_room_create(update, context)

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
            await process_solo_pick(update, context, move, game_id)
        elif game_type == "random":
            await process_random_pick(update, context, move, game_id)
        elif game_type == "tournament":
            try:
                tour_id = game_id
                match_index, move = tail.rsplit("_", 1)
                match_index = int(match_index)
            except:
                return
            await process_tournament_pick(update, context, move, tour_id, match_index)
        elif game_type == "spectate":
            await process_spectate_pick(update, context, move, game_id)
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
        await process_group_solo_pick(update, context, move, chat_id, player_id, game_id)
    elif data.startswith("spockpick_"):
        move = data.split("_", 1)[1]
        await process_spock_move(update, context, move)
    elif data.startswith("open_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await process_open_pick(update, context, move, chat_id)
    elif data.startswith("open_accept_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        await process_open_acceptor_pick(update, context, move, chat_id)

    # الميزات الجديدة
    elif data == "wheel":
        await query.edit_message_text("🎡 عجلة الحظ! تدوير بـ 5 جواهر.", reply_markup=keyboards.wheel_button())
    elif data == "wheel_spin":
        await wheel_spin_handler(update, context)
    elif data == "battlepass":
        await battlepass_command(update, context)
    elif data == "battlepass_progress":
        await battlepass_command(update, context)
    elif data == "frames_shop":
        await query.edit_message_text("اختر إطاراً:", reply_markup=keyboards.frame_shop())
    elif data.startswith("buy_frame_"):
        frame = data.split("_")[-1]
        price = config.FRAME_PRICES.get(frame, 200)
        u = db.get_user(user.id)
        if u["points"] < price:
            await query.answer("نقاط غير كافية")
            return
        db.update_user(user.id, points=u["points"] - price)
        db.set_user_frame(user.id, frame)
        await query.answer("تم شراء الإطار! استخدم /me لرؤيته.")
    elif data == "market":
        await query.edit_message_text("السوق:", reply_markup=keyboards.market_menu())
    elif data == "market_browse":
        listings = db.get_active_listings()
        if not listings:
            await query.edit_message_text("لا توجد عروض حالياً.")
            return
        text = "📊 **عروض السوق:**\n"
        buttons = []
        for l in listings[:5]:
            seller = db.get_user(l["seller_id"])
            name = seller["first_name"] if seller else "مجهول"
            text += f"{l['listing_id']}. {l['item_type']} {l['item_id']} - {l['price']} {l['price_type']} (من {name})\n"
            buttons.append([InlineKeyboardButton(f"شراء {l['listing_id']}", callback_data=f"market_buy_{l['listing_id']}")])
        buttons.append([InlineKeyboardButton("رجوع", callback_data="market")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("market_buy_"):
        lid = int(data.split("_")[-1])
        success = db.buy_listing(lid, user.id)
        if success:
            await query.answer("تم الشراء بنجاح!")
        else:
            await query.answer("فشل الشراء (رصيد غير كاف أو العنصر بيع).")
    elif data == "market_sell":
        await query.answer("استخدم /sell <نوع> <معرف> <سعر> <عملة>")

    # Mini Game Platform
    elif data == "abilities_shop":
        await query.edit_message_text("🛡️ متجر القدرات:", reply_markup=keyboards.abilities_shop())
    elif data.startswith("buy_ability_"):
        ability = data.split("_")[-1]
        if db.buy_ability(user.id, ability):
            await query.answer(f"تم شراء {config.ABILITIES[ability]['name']}!")
        else:
            await query.answer("نقاط غير كافية")
    elif data.startswith("mass_join_"):
        chat_id = int(data.split("_")[-1])
        await context.bot.send_message(user.id, "اختر حركتك للمعركة الجماعية:", reply_markup=keyboards.choice_buttons(f"mass_{chat_id}"))
        await query.answer("اختر في الخاص!")
    elif data.startswith("claim_drop_"):
        parts = data.split("_")
        rtype, value = parts[2], parts[3]
        if rtype == "points":
            db.update_user(user.id, points=db.get_user(user.id)["points"] + int(value))
            await query.answer(f"ربحت {value} نقطة!")
        elif rtype == "gems":
            db.update_user(user.id, gems=db.get_user(user.id).get("gems",0) + int(value))
            await query.answer(f"ربحت {value} جوهرة!")
        elif rtype == "title":
            db.update_user(user.id, title=value)
            await query.answer(f"حصلت على لقب {value}!")
        elif rtype == "theme":
            db.update_user(user.id, theme=value)
            await query.answer("حصلت على ثيم جديد!")
        await query.edit_message_text(f"🎁 {user.first_name} حصل على الجائزة!")
    elif data.startswith("team_join_"):
        parts = data.split("_")
        battle_id = int(parts[2])
        team = parts[3]
        db.add_team_player(battle_id, user.id, team)
        await query.answer(f"انضممت لفريق {'الأحمر' if team=='red' else 'الأزرق'}!")

    # الأصدقاء
    elif data == "add_friend":
        await handlers.add_friend_start(update, context)
    elif data == "friend_requests":
        await handlers.friend_requests_list(update, context)
    elif data == "friend_list":
        await handlers.friend_list_display(update, context)
    elif data.startswith("accept_friend_") or data.startswith("reject_friend_"):
        await handlers.handle_friend_action(update, context)

    # المتجر
    elif data == "shop_cards":
        await handlers.shop_cards(update, context)
    elif data.startswith("buy_") and "title" not in data and "theme" not in data and "frame" not in data and "ability" not in data:
        await handlers.buy_item(update, context)
    elif data == "shop_titles":
        await handlers.shop_titles(update, context)
    elif data.startswith("buy_title_"):
        await handlers.buy_title(update, context)
    elif data == "shop_themes":
        await handlers.shop_themes(update, context)
    elif data.startswith("buy_theme_"):
        await handlers.buy_theme(update, context)
    elif data == "treasure_box":
        await handlers.treasure_box(update, context)

    # العشائر
    elif data == "clan_create":
        await handlers.clan_create(update, context)
    elif data == "clan_join":
        await handlers.clan_join(update, context)
    elif data == "clan_ranking":
        await handlers.clan_ranking(update, context)
    elif data == "clan_treasury":
        await handlers.clan_treasury_menu(update, context)
    elif data.startswith("treasury_view_"):
        await handlers.treasury_view(update, context)
    elif data.startswith("treasury_donate_points_"):
        await handlers.treasury_donate_points(update, context)
    elif data.startswith("treasury_donate_gems_"):
        await handlers.treasury_donate_gems(update, context)
    elif data.startswith("treasury_upgrade_"):
        await handlers.treasury_upgrade(update, context)
    elif data.startswith("do_upgrade_"):
        await handlers.do_upgrade(update, context)
    elif data == "clan_war_info":
        await handlers.clan_war_info(update, context)

    # البطولات
    elif data == "tournament":
        await handlers.tournament_menu(update, context)
    elif data.startswith("join_tournament_"):
        await handlers.join_tournament_handler(update, context)

    # تحديات المشاهدة
    elif data.startswith("accept_challenge_"):
        await handlers.accept_challenge(update, context)
    elif data.startswith("reject_challenge_"):
        await handlers.reject_challenge(update, context)
    elif data.startswith("spectate_join_"):
        await handlers.spectate_join(update, context)

    # World Boss
    elif data == "boss_attack":
        await handlers.boss_attack(update, context)
    elif data == "boss_status":
        await handlers.boss_command(update, context)

    # لوحة تحكم الأدمن
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

    # تصويت القناة
    elif data.startswith("channel_vote_"):
        parts = data.split("_")
        chat_id = int(parts[2])
        move = parts[3]
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        lock = await state.get_vote_lock(chat_id)
        async with lock:
            success = db.record_channel_vote(chat_id, user.id, move)
        if success:
            await query.answer("تم تسجيل اختيارك! ✅")
        else:
            await query.answer("الجولة الحالية غير نشطة.")

    elif data.startswith("ch_leaderboard_"):
        chat_id = int(data.split("_")[-1])
        top = db.get_channel_leaderboard(chat_id, 10)
        text = "🏆 **أفضل 10 لاعبين في القناة:**\n"
        for i, r in enumerate(top, 1):
            text += f"{i}. {r['first_name']} - {r['points']} نقطة\n"
        await query.edit_message_text(text)

# ---------- دوال اللعب الأساسية ----------
async def process_solo_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or game["player1"] != user.id:
        await query.edit_message_text("انتهت اللعبة.")
        return
    bot_move = utils.markov_bot_choice(user.id)
    result = game_logic.get_result(move, bot_move)
    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)
    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = f"أنت: {user_icon} vs البوت: {bot_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

async def process_random_pick(update, context, move, game_id):
    query = update.callback_query
    user = query.from_user
    game = state.get_game(game_id)
    if not game or (game["player1"] != user.id and game["player2"] != user.id):
        await query.edit_message_text("انتهت اللعبة.")
        return
    state.set_game_move(game_id, user.id, move)
    moves = state.get_game_moves(game_id)
    p1, p2 = game["player1"], game["player2"]
    if str(p1) in moves and str(p2) in moves:
        m1 = moves[str(p1)]
        m2 = moves[str(p2)]
        res1 = game_logic.get_result(m1, m2)
        res2 = game_logic.get_result(m2, m1)
        db.apply_game_result(p1, res1, m1, p2)
        db.apply_game_result(p2, res2, m2, p1)
        utils.update_user_moves(p1, m1)
        utils.update_user_moves(p2, m2)
        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)
        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)
        text = f"⚔️ {db.get_user(p1)['first_name']} اختار {icon1} vs {db.get_user(p2)['first_name']} اختار {icon2}\nالنتيجة: {res1} لصالح {db.get_user(p1)['first_name']}"
        await query.edit_message_text(text)
        try:
            await context.bot.send_message(p2, text)
        except: pass
        await state.remove_game(game_id)
    else:
        await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")

async def process_spock_move(update, context, move):
    query = update.callback_query
    user = query.from_user
    from config import SPOCK_CHOICES, SPOCK_WIN_MAP
    bot_move = random.choice(list(SPOCK_CHOICES.keys()))
    if move == bot_move:
        result = "draw"
    elif bot_move in SPOCK_WIN_MAP[move]:
        result = "win"
    else:
        result = "loss"
    game_id = state.start_solo_game(user.id)
    db.apply_game_result(user.id, result, move, None)
    utils.update_user_moves(user.id, move)
    theme = utils.get_choices_for_user(user.id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = f"أنت: {user_icon} vs البوت: {bot_icon}\nالنتيجة: {result}"
    await query.edit_message_text(text)
    state.finish_solo_game(game_id)

async def process_group_solo_pick(update, context, move, chat_id, player_id, game_id):
    query = update.callback_query
    user = query.from_user
    if user.id != player_id:
        await query.answer("هذه اللعبة ليست لك!")
        return
    game = state.group_solo_games.get(player_id)
    if not game or game["game_id"] != game_id:
        await query.answer("انتهت اللعبة.")
        return
    try:
        await context.bot.delete_message(chat_id, game["message_id"])
    except: pass
    bot_move = utils.markov_bot_choice(player_id)
    result = game_logic.get_result(move, bot_move)
    db.apply_game_result(player_id, result, move, None)
    utils.update_user_moves(player_id, move)
    theme = utils.get_choices_for_user(player_id)
    user_icon = theme.get(move, move)
    bot_icon = theme.get(bot_move, bot_move)
    text = (f"🎮 **نتيجة اللعبة الفردية**\n"
            f"{user.first_name} اختار {user_icon}\n"
            f"البوت اختار {bot_icon}\n"
            f"النتيجة: {result}")
    await context.bot.send_message(chat_id, text)
    state.finish_solo_game(game_id)
    state.group_solo_games.pop(player_id, None)
    await query.answer("تم إرسال النتيجة إلى المجموعة.")

# ---------- التحدي المفتوح ----------
async def start_open_challenge(update, context, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        if chat_id in state.open_challenges:
            await query.answer("يوجد بالفعل تحدي مفتوح في هذه المجموعة!")
            return
        await context.bot.send_message(user.id, "اختر حركتك للتحدي المفتوح:", reply_markup=keyboards.choice_buttons(f"open_{chat_id}_temp"))
        state.open_challenges[chat_id] = {"initiator": user.id, "move": None, "message_id": None}
    await query.answer("تم إرسال خيارات الحركة في الخاص.")

async def process_open_pick(update, context, move, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge or challenge["initiator"] != user.id:
            await query.edit_message_text("لا يوجد تحدي بهذا المعرف.")
            return
        challenge["move"] = move
        await query.edit_message_text("تم اختيار حركتك. سيتم الإعلان في المجموعة...")
        msg = await context.bot.send_message(chat_id, f"🎯 **تحدي مفتوح!**\n{user.first_name} اختار حركته.\nمن يقبل التحدي؟", reply_markup=keyboards.open_challenge_accept_button(chat_id))
        challenge["message_id"] = msg.message_id
        asyncio.create_task(auto_cancel_open_challenge(chat_id, context))

async def auto_cancel_open_challenge(chat_id, context):
    await asyncio.sleep(60)
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if challenge:
            try:
                await context.bot.edit_message_text(chat_id, challenge["message_id"], text="⏰ انتهت صلاحية التحدي المفتوح.")
            except: pass
            state.open_challenges.pop(chat_id, None)

async def accept_open_challenge(update, context, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge:
            await query.answer("انتهى التحدي أو غير موجود.")
            return
        if user.id == challenge["initiator"]:
            await query.answer("لا يمكنك تحدي نفسك!")
            return
        challenge["acceptor"] = user.id
        await context.bot.send_message(user.id, "اختر حركتك:", reply_markup=keyboards.choice_buttons(f"open_accept_{chat_id}_temp"))
    await query.answer("تم قبول التحدي! اختر حركتك في الخاص.")

async def process_open_acceptor_pick(update, context, move, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge or challenge.get("acceptor") != user.id:
            await query.edit_message_text("لا يمكنك الرد على هذا التحدي.")
            return
        initiator_id = challenge["initiator"]
        initiator_move = challenge["move"]
        if not initiator_move:
            await query.edit_message_text("لم يتم تحديد حركة البادئ بعد.")
            return
        result_init = game_logic.get_result(initiator_move, move)
        db.apply_game_result(initiator_id, result_init, initiator_move, user.id)
        result_acceptor = "loss" if result_init == "win" else ("win" if result_init == "loss" else "draw")
        db.apply_game_result(user.id, result_acceptor, move, initiator_id)
        u1 = db.get_user(initiator_id)
        u2 = db.get_user(user.id)
        theme1 = utils.get_choices_for_user(initiator_id)
        theme2 = utils.get_choices_for_user(user.id)
        icon1 = theme1.get(initiator_move, initiator_move)
        icon2 = theme2.get(move, move)
        winner = f"🏆 فاز {u1['first_name']}!" if result_init == "win" else (f"🏆 فاز {u2['first_name']}!" if result_acceptor == "win" else "🤝 تعادل!")
        text = f"⚔️ **نتيجة التحدي المفتوح**\n{u1['first_name']} اختار {icon1}\n{u2['first_name']} اختار {icon2}\n{winner}"
        await context.bot.send_message(chat_id, text)
        try: await context.bot.delete_message(chat_id, challenge["message_id"])
        except: pass
        state.open_challenges.pop(chat_id, None)
    await query.edit_message_text("تم إرسال النتيجة إلى المجموعة.")

# ---------- البطولة ----------
async def process_tournament_pick(update, context, move, tour_id, match_index):
    query = update.callback_query
    user = query.from_user
    tour = db.get_tournament(tour_id)
    if not tour: return
    bracket = json.loads(tour.get("bracket", "{}"))
    current_round = tour["current_round"]
    round_key = f"round{current_round}"
    matches = bracket.get(round_key, [])
    if match_index >= len(matches): return
    match = matches[match_index]
    match_data = json.loads(tour.get("match_data", "{}"))
    match_data[str(match_index)] = match_data.get(str(match_index), {})
    match_data[str(match_index)][str(user.id)] = move
    db.update_tournament(tour_id, match_data=json.dumps(match_data))
    if str(match["p1"]) in match_data[str(match_index)] and str(match["p2"]) in match_data[str(match_index)]:
        m1 = match_data[str(match_index)][str(match["p1"])]
        m2 = match_data[str(match_index)][str(match["p2"])]
        res = game_logic.get_result(m1, m2)
        winner = match["p1"] if res == "win" else match["p2"] if res == "loss" else None
        match["winner"] = winner
        bracket[round_key][match_index] = match
        db.update_tournament(tour_id, bracket=json.dumps(bracket))
        if current_round == 1:
            winners = [m["winner"] for m in bracket["round1"] if m.get("winner") is not None]
            if len(winners) == 4:
                bracket["round2"] = [{"p1": winners[0], "p2": winners[1]}, {"p1": winners[2], "p2": winners[3]}]
                db.update_tournament(tour_id, bracket=json.dumps(bracket), current_round=2)
                for i, m2 in enumerate(bracket["round2"]):
                    await context.bot.send_message(m2["p1"], f"🏆 نصف النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
                    await context.bot.send_message(m2["p2"], f"🏆 نصف النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
        elif current_round == 2:
            winners = [m["winner"] for m in bracket["round2"] if m.get("winner") is not None]
            if len(winners) == 2:
                bracket["final"] = [{"p1": winners[0], "p2": winners[1]}]
                db.update_tournament(tour_id, bracket=json.dumps(bracket), current_round=3)
                for i, mf in enumerate(bracket["final"]):
                    await context.bot.send_message(mf["p1"], f"🏆 النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
                    await context.bot.send_message(mf["p2"], f"🏆 النهائي! اختر حركتك:", reply_markup=keyboards.tournament_choice_buttons(tour_id, i))
        elif current_round == 3:
            final_winner = match["winner"]
            if final_winner:
                db.update_user(final_winner, tournament_wins=db.get_user(final_winner).get("tournament_wins",0)+1, points=db.get_user(final_winner)["points"]+200)
                await context.bot.send_message(final_winner, "🎉 أنت بطل البطولة! ربحت 200 نقطة.")
            db.update_tournament(tour_id, status="finished")
    await query.edit_message_text("تم تسجيل حركتك.")

# ---------- غرفة المشاهدة ----------
async def process_spectate_pick(update, context, move, room_id):
    query = update.callback_query
    user = query.from_user
    room = db.get_spectator_room(room_id)
    if not room or room["status"] != "active":
        await query.edit_message_text("انتهت الغرفة.")
        return
    if user.id not in (room["player1"], room["player2"]):
        await query.edit_message_text("لست مشاركاً في هذه المباراة.")
        return
    moves = json.loads(room["moves"] or "{}")
    moves[str(user.id)] = move
    db.update_spectator_room(room_id, moves=json.dumps(moves))
    p1, p2 = room["player1"], room["player2"]
    if str(p1) in moves and str(p2) in moves:
        m1 = moves[str(p1)]
        m2 = moves[str(p2)]
        res1 = game_logic.get_result(m1, m2)
        db.apply_game_result(p1, res1, m1, p2)
        res2 = "loss" if res1 == "win" else ("win" if res1 == "loss" else "draw")
        db.apply_game_result(p2, res2, m2, p1)
        u1 = db.get_user(p1)
        u2 = db.get_user(p2)
        theme1 = utils.get_choices_for_user(p1)
        theme2 = utils.get_choices_for_user(p2)
        icon1 = theme1.get(m1, m1)
        icon2 = theme2.get(m2, m2)
        text = f"👀 **نتيجة مباراة المشاهدة**\n{u1['first_name']} اختار {icon1}\n{u2['first_name']} اختار {icon2}\nالنتيجة: {res1} لصالح {u1['first_name']}"
        await context.bot.send_message(room["chat_id"], text)
        db.update_spectator_room(room_id, status="finished")
    await query.edit_message_text("تم تسجيل حركتك.")

# ---------- حلقة التصويت التلقائي للقناة ----------
async def channel_voting_loop(chat_id, context: ContextTypes.DEFAULT_TYPE):
    last_message_id = None
    try:
        while True:
            settings = state.channel_settings.get(chat_id)
            if not settings: break
            interval = settings.get("interval", 60)
            ttl = settings.get("ttl", 30)

            # حذف رسالة النتائج السابقة
            if last_message_id:
                try: await context.bot.delete_message(chat_id, last_message_id)
                except: pass
                last_message_id = None

            current_event = None
            if random.random() < config.EVENT_CHANCE:
                current_event = random.choice(config.POSSIBLE_EVENTS)

            event_text = ""
            if current_event == "double_points": event_text = "🎁 حدث: نقاط مضاعفة!"
            elif current_event == "shuffle": event_text = "🌀 حدث: خلط الأصوات!"
            elif current_event == "boss": event_text = "🐉 حدث: الزعيم يشارك!"

            db.start_channel_loop(chat_id, interval, ttl)
            try:
                msg = await context.bot.send_message(
                    chat_id,
                    f"🔥 **جولة جديدة!** (تنتهي خلال {interval} ثانية)\n{event_text}\nاختر حركتك:",
                    reply_markup=keyboards.channel_vote_buttons(chat_id)
                )
                invite_message_id = msg.message_id
            except Exception as e:
                logger.error(f"خطأ في جولة القناة {chat_id}: {e}")
                break

            try: await asyncio.sleep(interval)
            except asyncio.CancelledError:
                try: await context.bot.delete_message(chat_id, invite_message_id)
                except: pass
                break

            lock = await state.get_vote_lock(chat_id)
            async with lock:
                result = db.finish_channel_round(chat_id)

            if result and result["players"]:
                counts = result["counts"]
                winners = result["winners"]
                winning = ", ".join(result["winning_moves"])
                is_draw = result["draw"]

                bot_move = utils.markov_bot_choice(0)
                clan_scores = {}
                for uid, move in result["players"].items():
                    uid_int = int(uid)
                    user = db.get_user(uid_int) or {"points": 0, "clan": None}
                    is_winner = uid_int in winners

                    streak = db.update_user_streak(chat_id, uid_int, is_winner)
                    if is_winner:
                        reward = config.CHANNEL_LOOP_REWARDS["draw"] if is_draw else config.CHANNEL_LOOP_REWARDS["win"]
                    else:
                        reward = config.CHANNEL_LOOP_REWARDS["loss"]
                    if current_event == "double_points":
                        reward *= 2
                    if streak > 1 and is_winner:
                        reward += config.STREAK_BONUS * streak
                    if move == bot_move:
                        reward += 5
                    db.update_user(uid_int, points=user["points"] + reward)
                    db.add_channel_points(chat_id, uid_int, reward)
                    clan = user.get("clan")
                    if clan:
                        clan_scores[clan] = clan_scores.get(clan, 0) + reward

                text = "📊 **نتائج الجولة:**\n"
                for move, cnt in counts.items():
                    text += f"{move}: {cnt} لاعب\n"
                text += f"\n🤖 حركة البوت: {bot_move}\n"
                if is_draw:
                    text += f"🤝 تعادل! الحركات المتساوية: {winning}\n"
                else:
                    text += f"🏆 الحركة الفائزة: {winning}\n"
                    text += f"عدد الفائزين: {len(winners)}\n"
                if current_event == "double_points":
                    text += "🎁 نقاط مضاعفة!\n"

                if clan_scores:
                    sorted_clans = sorted(clan_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                    text += "\n🏰 **ترتيب العشائر:**\n"
                    for i, (clan, score) in enumerate(sorted_clans, 1):
                        text += f"{i}. {clan} - {score} نقطة\n"

                text += "\nاضغط لرؤية قائمة الأفضل:"
            else:
                text = "لم يشارك أحد في هذه الجولة."

            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=invite_message_id,
                    text=text,
                    reply_markup=keyboards.channel_leaderboard_button(chat_id)
                )
                last_message_id = invite_message_id
            except:
                msg = await context.bot.send_message(chat_id, text, reply_markup=keyboards.channel_leaderboard_button(chat_id))
                last_message_id = msg.message_id

            try: await asyncio.sleep(5)
            except asyncio.CancelledError: break
    finally:
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                del state.channel_settings[chat_id]

# ---------- أوامر القناة ----------
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
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                old_task = state.channel_settings[chat_id].get("task")
                if old_task: old_task.cancel()
                del state.channel_settings[chat_id]
        task = asyncio.create_task(channel_voting_loop(chat_id, context))
        async with state.channel_settings_lock:
            state.channel_settings[chat_id] = {"interval": interval, "ttl": ttl, "task": task}
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
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                task = state.channel_settings[chat_id].get("task")
                if task: task.cancel()
                del state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف جولات التصويت في {chat.title}")
            else:
                await update.message.reply_text("لا توجد جولات نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ---------- Admin Panel ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total_users = len(db.get_all_user_ids())
    conn = sqlite3.connect("rps_bot.db")
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
    async with state.channel_settings_lock:
        chans = list(state.channel_settings.keys())
    text = "القنوات المفعلة:\n" + "\n".join([str(c) for c in chans]) if chans else "لا توجد"
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_reset_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    conn = sqlite3.connect("rps_bot.db")
    conn.execute("DELETE FROM active_games")
    conn.execute("DELETE FROM pending_matches")
    conn.commit()
    conn.close()
    await query.answer("تم مسح المباريات العالقة.")

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
            db.update_user(uid, points=db.get_user(uid)["points"] + config.MASS_BATTLE_REWARD[0],
                           gems=db.get_user(uid).get("gems",0) + config.MASS_BATTLE_REWARD[1])
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
    await process_team_battle(battle_id, context)

async def process_team_battle(battle_id, context):
    conn = sqlite3.connect("rps_bot.db")
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

        if len(msg) > 100:
            await update.message.reply_text("النص طويل جداً.")
            return

        if context.user_data.get("awaiting_friend_username"):
            await handlers.process_friend_username(update, context)
        elif context.user_data.get("awaiting_clan_name"):
            await handlers.process_clan_name(update, context)
        elif context.user_data.get("awaiting_join_clan"):
            await handlers.process_join_clan(update, context)
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
    asyncio.create_task(start_channel_game_cycle(chat_id, context))
    await context.bot.send_message(chat_id, "🎮 تم تفعيل اللعب! يمكنك الضغط على الأزرار أدناه:", reply_markup=keyboards.group_game_menu(chat_id))

async def start_channel_game_cycle(chat_id, context: ContextTypes.DEFAULT_TYPE):
    # هذا هو الروتين القديم للجروبات (اختياري)، يمكن إزالته أو استبداله
    pass

# ---------- تشغيل البوت ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("battlepass", battlepass_command))
    app.add_handler(CommandHandler("sell", market_sell_command))
    app.add_handler(CommandHandler("season", handlers.season_command))
    app.add_handler(CommandHandler("boss", handlers.boss_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("start_channel", start_channel_command))
    app.add_handler(CommandHandler("stop_channel", stop_channel_command))
    app.add_handler(CommandHandler("challenge", handlers.challenge_start))
    app.add_handler(CommandHandler("massbattle", massbattle_command))
    app.add_handler(CommandHandler("drop", drop_command))
    app.add_handler(CommandHandler("teambattle", teambattle_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_stuck_games())
    loop.create_task(auto_drops(app))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
