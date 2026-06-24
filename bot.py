import json, logging, asyncio, random
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# ---------- أمر /me لعرض بروفايل اللاعب مع الرانك ----------
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

    # الرجوع للقائمة الرئيسية
    if data == "back_main":
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=keyboards.main_menu())
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
            try:
                progress = json.loads(progress_data)
            except:
                pass
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

    # أوضاع اللعب
    elif data == "solo":
        state.active_games[user.id] = {"type": "solo"}
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

    # اختيار الحركات
    elif data.startswith("pick_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
        move = parts[1]
        game_type = parts[2]
        if move not in ["rock", "paper", "scissors"]:
            await query.answer("حركة غير صالحة!")
            return
        # فحص إذا كانت لعبة مشاهدة
        if game_type.startswith("spectate_"):
            challenge_id = game_type.split("_", 1)[1]
            await process_spectate_move(update, context, move, challenge_id)
        else:
            await process_move(update, context, move, game_type)
    elif data.startswith("spockpick_"):
        move = data.split("_", 1)[1]
        await process_spock_move(update, context, move)

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

    # 🆕 تحديات المشاهدة
    elif data.startswith("accept_challenge_"):
        await handlers.accept_challenge(update, context)
    elif data.startswith("reject_challenge_"):
        await handlers.reject_challenge(update, context)

# ---------- معالجة الحركات ----------
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
        if not opp_id:
            return
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
    if not updated:
        return

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

# ---------- 🆕 معالجة تحديات المشاهدة ----------
async def process_spectate_move(update, context, move, challenge_id):
    query = update.callback_query
    user = query.from_user
    async with state.spectate_lock:
        challenge = state.spectate_challenges.get(challenge_id)
        if not challenge or challenge["status"] != "active":
            await query.edit_message_text("التحدي غير موجود أو انتهى.")
            return
        if user.id not in challenge["players"]:
            await query.answer("لست مشاركاً في هذا التحدي.")
            return
        challenge["moves"][user.id] = move
        await query.edit_message_text("تم تسجيل حركتك، بانتظار الخصم...")
        if len(challenge["moves"]) == 2:
            p1, p2 = challenge["players"]
            m1 = challenge["moves"][p1]
            m2 = challenge["moves"][p2]
            result_p1 = game_logic.get_result(m1, m2)
            # تحديث قاعدة البيانات لكلا اللاعبين
            db.apply_game_result(p1, result_p1, m1, p2)
            # النتيجة للثاني عكس الأول
            result_p2 = "loss" if result_p1 == "win" else ("win" if result_p1 == "loss" else "draw")
            db.apply_game_result(p2, result_p2, m2, p1)
            # أسماء وأيقونات
            u1 = db.get_user(p1)
            u2 = db.get_user(p2)
            theme1 = utils.get_choices_for_user(p1)
            theme2 = utils.get_choices_for_user(p2)
            icon1 = theme1.get(m1, m1)
            icon2 = theme2.get(m2, m2)
            # تعليق تلقائي
            comment = generate_commentary(result_p1, m1, m2)
            msg = (f"⚔️ انتهت المباراة!\n"
                   f"{u1['first_name']} اختار {icon1}\n"
                   f"{u2['first_name']} اختار {icon2}\n"
                   f"النتيجة: {result_p1} لصالح {u1['first_name']}\n\n"
                   f"📢 التعليق: {comment}")
            await context.bot.send_message(challenge["chat_id"], msg)
            # تنظيف
            state.spectate_challenges.pop(challenge_id, None)

def generate_commentary(result, move1, move2):
    if result == "win":
        comments = [
            "هجوم صاعق! الخصم لم يتمكن من الصمود.",
            "ضربة قاضية بكل براعة!",
            "استراتيجية محكمة أتت أكلها."
        ]
    elif result == "loss":
        comments = [
            "خسارة مؤلمة، حظ أوفر في المرة القادمة.",
            "وقع في الفخ! الخصم كان له بالمرصاد.",
            "درس قاسٍ، لكن الأبطال يتعلمون من الهزيمة."
        ]
    else:
        comments = [
            "تعادل عادل! كلاهما يفكر بنفس الطريقة.",
            "قمة الإثارة والتكافؤ!",
            "لا غالب ولا مغلوب، مباراة متوازنة."
        ]
    return random.choice(comments)

# ---------- معالج النصوص ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text.strip()
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

# ---------- أوامر المؤسس ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        await update.message.reply_text("غير مسموح")
        return
    await update.message.reply_text("لوحة التحكم:\n/start_war لبدء حرب عشائر")

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
    app.add_handler(CommandHandler("challenge", handlers.challenge_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
