import json, logging, asyncio, random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import models, db, config, state, keyboards, game_logic, utils, handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.init_db()

# ---------- أوامر أساسية ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id)
    if not u:
        db.create_user(user.id, user.username, user.first_name)
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
    wins = u.get("wins", 0)
    losses = u.get("losses", 0)
    draws = u.get("draws", 0)
    total = wins + losses + draws
    winrate = f"{(wins / total * 100):.1f}%" if total > 0 else "0%"
    profile_text = (
        f"👤 {u['first_name']}\n"
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
        state.active_games[user.id] = {"type": "solo", "chat_id": None}
        await query.edit_message_text("اختر حركتك:", reply_markup=keyboards.choice_buttons("solo"))
    elif data == "random":
        result = await state.add_pending(user.id)
        if result is None:
            await query.answer("أنت بالفعل في قائمة الانتظار أو مشغول بلعبة!")
        elif result is True:
            await query.edit_message_text("بانتظار لاعب آخر...")
        else:
            opp_id = result
            await query.edit_message_text("تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
            await context.bot.send_message(opp_id, "تم العثور على خصم! اختر حركتك:", reply_markup=keyboards.choice_buttons("random"))
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
        state.group_solo_games[user.id] = {"chat_id": chat_id}
        keyboard = keyboards.group_choice_buttons(chat_id, user.id)
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

    # اختيار الحركات
    elif data.startswith("pick_"):
        parts = data.split("_")
        if len(parts) < 3: return
        move = parts[1]
        game_type = parts[2]
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        if game_type.startswith("spectate_"):
            challenge_id = game_type.split("_", 1)[1]
            await process_spectate_move(update, context, move, challenge_id)
        else:
            await process_move(update, context, move, game_type)
    elif data.startswith("group_pick_"):
        parts = data.split("_")
        move = parts[2]
        chat_id = int(parts[3])
        player_id = int(parts[4])
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        await process_group_solo_pick(update, context, move, chat_id, player_id)
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
    elif data.startswith("buy_") and "title" not in data and "theme" not in data:
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

# ---------- دوال الألعاب الفردية (خاص) ----------
async def process_move(update, context, move, game_type):
    query = update.callback_query
    user = query.from_user
    game = state.active_games.get(user.id)
    if not game:
        await query.edit_message_text("انتهت اللعبة.")
        return
    if game_type == "solo":
        bot_move = utils.markov_bot_choice(user.id)
        result = game_logic.get_result(move, bot_move)
        await finish_game(update, context, user.id, move, bot_move, result)
    elif game_type == "random":
        opp_id = game.get("opponent")
        if not opp_id: return
        game["move"] = move
        opp_game = state.active_games.get(opp_id)
        if opp_game and "move" in opp_game:
            opp_move = opp_game["move"]
            res1 = game_logic.get_result(move, opp_move)
            res2 = game_logic.get_result(opp_move, move)
            await finish_game(update, context, user.id, move, opp_move, res1)
            await context.bot.send_message(opp_id, f"نتيجة المباراة: {res2}")
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
    await finish_game(update, context, user.id, move, bot_move, result, spock=True)

async def finish_game(update, context, user_id, user_move, opp_move, result, spock=False):
    game = state.active_games.get(user_id)
    opponent_id = game.get("opponent") if game else None
    updated = db.apply_game_result(user_id, result, user_move, opponent_id)
    if not updated: return
    theme = utils.get_choices_for_user(user_id)
    user_icon = theme.get(user_move, user_move)
    opp_icon = theme.get(opp_move, opp_move)
    text = f"أنت: {user_icon} vs الخصم: {opp_icon}\nالنتيجة: {result}"
    if update.callback_query:
        await update.callback_query.edit_message_text(text)
    await game_logic.check_achievements(user_id, context)
    await game_logic.check_and_complete_task(user_id, "task_1", context, 1)
    game_logic.add_clan_points(user_id, 2)
    utils.update_user_moves(user_id, user_move)
    await state.remove_game(user_id)

# ---------- اللعب الفردي الجماعي ----------
async def process_group_solo_pick(update, context, move, chat_id, player_id):
    query = update.callback_query
    user = query.from_user
    if user.id != player_id:
        await query.answer("هذه اللعبة ليست لك!")
        return
    game = state.group_solo_games.get(player_id)
    if not game or game["chat_id"] != chat_id:
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
        await context.bot.send_message(user.id, "اختر حركتك للتحدي المفتوح:", reply_markup=keyboards.choice_buttons(f"open_{chat_id}"))
        state.open_challenges[chat_id] = {
            "initiator": user.id,
            "move": None,
            "message_id": None
        }
    await query.answer("تم إرسال خيارات الحركة في الخاص.")

async def process_open_pick(update, context, move, chat_id):
    query = update.callback_query
    user = query.from_user
    async with state.open_challenge_lock:
        challenge = state.open_challenges.get(chat_id)
        if not challenge or challenge["initiator"] != user.id:
            await query.edit_message_text("لا يوجد تحدي بهذا المعرف.")
            return
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        challenge["move"] = move
        await query.edit_message_text("تم اختيار حركتك. سيتم الإعلان في المجموعة...")
        try:
            msg = await context.bot.send_message(
                chat_id,
                f"🎯 **تحدي مفتوح!**\n{user.first_name} اختار حركته.\nمن يقبل التحدي؟",
                reply_markup=keyboards.open_challenge_accept_button(chat_id)
            )
            challenge["message_id"] = msg.message_id
            asyncio.create_task(auto_cancel_open_challenge(chat_id, context))
        except Exception as e:
            logger.error(f"فشل إرسال إعلان التحدي: {e}")
            state.open_challenges.pop(chat_id, None)

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
        await context.bot.send_message(user.id, "اختر حركتك:", reply_markup=keyboards.choice_buttons(f"open_accept_{chat_id}"))
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
        winner_text = f"🏆 فاز {u1['first_name']}!" if result_init == "win" else (f"🏆 فاز {u2['first_name']}!" if result_acceptor == "win" else "🤝 تعادل!")
        text = (f"⚔️ **نتيجة التحدي المفتوح**\n"
                f"{u1['first_name']} اختار {icon1}\n"
                f"{u2['first_name']} اختار {icon2}\n"
                f"{winner_text}")
        await context.bot.send_message(chat_id, text)
        try:
            await context.bot.delete_message(chat_id, challenge["message_id"])
        except: pass
        state.open_challenges.pop(chat_id, None)
    await query.edit_message_text("تم إرسال النتيجة إلى المجموعة.")

# ---------- دورة اللعب التلقائي (للجروبات والقنوات) ----------
async def start_channel_game_cycle(chat_id, context: ContextTypes.DEFAULT_TYPE):
    """دورة لا نهائية للقنوات والجروبات مع إعدادات مخصصة"""
    while True:
        async with state.channel_settings_lock:
            settings = state.channel_settings.get(chat_id)
            if not settings:
                break
            interval = settings.get("interval", 120)
            ttl = settings.get("ttl", 60)
        # إنشاء جلسة جديدة إذا كانت للعبة العشوائية (للقنوات قد لا تحتاج)
        async with state.group_session_lock:
            session = {"players": set(), "task": asyncio.current_task()}
            state.group_game_sessions[chat_id] = session
        try:
            msg = await context.bot.send_message(
                chat_id,
                "🎮 **بدأت جولة جديدة!** (تنتهي قريباً)\nاختر نمط لعبك أو انضم للعشوائي:",
                reply_markup=keyboards.group_game_menu(chat_id)
            )
            # تخزين معرف الرسالة للحذف التلقائي لاحقاً
            async with state.channel_settings_lock:
                if chat_id in state.channel_settings:
                    state.channel_settings[chat_id]["message_id"] = msg.message_id
        except Exception as e:
            logger.error(f"فشل إرسال رسالة الجولة إلى {chat_id}: {e}")
            break

        # حذف الرسالة بعد مدة ttl
        async def delete_after(chat_id, msg_id, delay):
            await asyncio.sleep(delay)
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except: pass

        asyncio.create_task(delete_after(chat_id, msg.message_id, ttl))

        # انتظار فترة interval قبل الجولة التالية (مع مراعاة أن الرسالة قد حذفت بالفعل)
        await asyncio.sleep(interval)

        # معالجة اللاعبين العشوائيين (اختياري - كما سبق)
        async with state.group_session_lock:
            players = list(session["players"])
            state.group_game_sessions.pop(chat_id, None)
        # يمكن تفعيل العشوائي كما في النسخ السابقة، لكن للقناة قد لا نريد ذلك
        # سنتركه فارغاً للقنوات (أو نضيفه إذا أردت)

# ---------- أمر بدء دورة القناة (للمؤسس) ----------
async def start_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        await update.message.reply_text("غير مسموح")
        return
    try:
        args = context.args
        if not args:
            await update.message.reply_text("استخدم: /start_channel @channelname [interval=120] [ttl=60]")
            return
        channel_name = args[0]
        interval = 120
        ttl = 60
        for a in args[1:]:
            if a.startswith("interval="):
                interval = int(a.split("=")[1])
            elif a.startswith("ttl="):
                ttl = int(a.split("=")[1])
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                # إيقاف الدورة السابقة إذا وجدت
                old_task = state.channel_settings[chat_id].get("task")
                if old_task:
                    old_task.cancel()
            task = asyncio.create_task(start_channel_game_cycle(chat_id, context))
            state.channel_settings[chat_id] = {
                "interval": interval,
                "ttl": ttl,
                "task": task,
                "message_id": None
            }
        await update.message.reply_text(f"تم بدء الدورة في {chat.title}\nالفاصل: {interval}s | حذف الرسالة بعد: {ttl}s")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ---------- أمر إيقاف دورة القناة ----------
async def stop_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    try:
        if not context.args:
            await update.message.reply_text("استخدم: /stop_channel @channelname")
            return
        chat = await context.bot.get_chat(context.args[0])
        chat_id = chat.id
        async with state.channel_settings_lock:
            if chat_id in state.channel_settings:
                task = state.channel_settings[chat_id].get("task")
                if task:
                    task.cancel()
                del state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف الدورة في {chat.title}")
            else:
                await update.message.reply_text("لا توجد دورة نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ---------- معالج النصوص (يشمل @mention للجروبات) ----------
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
    # بدء دورة عادية للجروب (بدون إعدادات مخصصة)
    async with state.group_session_lock:
        if chat_id in state.group_game_sessions:
            return
    asyncio.create_task(start_channel_game_cycle(chat_id, context))
    await context.bot.send_message(chat_id, "🎮 تم تفعيل اللعب! يمكنك الضغط على الأزرار أدناه:", reply_markup=keyboards.group_game_menu(chat_id))

# ---------- أوامر المؤسس ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        await update.message.reply_text("غير مسموح")
        return
    await update.message.reply_text("لوحة التحكم:\n/start_war لبدء حرب عشائر\n/start_channel @channel interval=120 ttl=60\n/stop_channel @channel")

async def start_war_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    await update.message.reply_text("بدأت حرب العشائر!")

# ---------- تشغيل البوت ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("start_war", start_war_command))
    app.add_handler(CommandHandler("start_channel", start_channel_command))
    app.add_handler(CommandHandler("stop_channel", stop_channel_command))
    app.add_handler(CommandHandler("challenge", handlers.challenge_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
