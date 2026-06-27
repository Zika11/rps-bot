import json
import logging
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import config
import models
import db
import state
import keyboards
import game_logic
import utils

import engine.game_engine as game_engine
import state as channel_state

import handlers.channel_handlers as channel_h
import handlers.game_handlers as game_h
import handlers.shop_handlers as shop_h
import handlers.social_handlers as social_h
import handlers.misc_handlers as misc_h

from handlers.callbacks import (
    navigation_handler,
    game_handler,
    channel_handler,
    shop_handler,
    social_handler,
    admin_handler
)

from handlers.commands import (
    start, me_command, daily_command, referral_command,
    game_command, web_command,
    shop_command, buy_command, market_sell_command, battlepass_command,
    admin_panel, start_channel_command, stop_channel_command,
    massbattle_command, teambattle_command, drop_command
)

# استيراد أمر matchmaking (مع التعامل مع حالة عدم وجوده)
try:
    from handlers.commands.game_commands import matchmaking_status
except ImportError:
    matchmaking_status = None
    logging.warning("⚠️ matchmaking_status غير موجود")

from handlers.commands.admin_commands import (
    admin_stats, admin_broadcast_prompt, admin_set_points_prompt,
    admin_channels_list, admin_reset_games
)

from tasks import run_cleanup, run_auto_drops

# ==================== الألعاب الجديدة ====================
from games.guess_number import GuessNumberGame
from games.quiz import QuizGame

# ==================== إعدادات Logging ====================
try:
    from utils.logging_utils import logger
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ utils.logging_utils غير موجود، استخدام logging عادي")

# ==================== خدمات إضافية ====================
try:
    from services.cache_service import cache
except ImportError:
    cache = None
    logger.warning("⚠️ services.cache_service غير موجود")

try:
    from core.redis_client import redis_client
except ImportError:
    redis_client = None
    logger.warning("⚠️ core.redis_client غير موجود")

try:
    from core.google_sheets import gsheets
except ImportError:
    gsheets = None
    logger.warning("⚠️ core.google_sheets غير موجود")

# ==================== تهيئة قاعدة البيانات ====================
models.init_db()
logger.info(f"✅ قاعدة البيانات جاهزة: {config.DB_NAME}")

# ==================== التحقق من الاتصالات ====================
if redis_client and hasattr(redis_client, 'is_connected') and redis_client.is_connected():
    logger.info("✅ Redis متصل")
else:
    logger.info("ℹ️ Redis غير متصل أو معطل")

if gsheets and hasattr(gsheets, 'is_connected') and gsheets.is_connected():
    logger.info("✅ Google Sheets متصل")
    try:
        if cache:
            gsheet_settings = cache.get_settings()
            if gsheet_settings:
                logger.info(f"✅ تم تحميل {len(gsheet_settings)} إعداد من Google Sheets")
    except Exception as e:
        logger.error(f"❌ فشل تحميل الإعدادات من Google Sheets: {e}")
else:
    logger.info("ℹ️ Google Sheets غير متصل أو معطل")

# ==================== معالج الرسائل النصية ====================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية (للبث، إدخال البيانات، المنشن، ألعاب التخمين)"""
    user = update.effective_user
    msg = update.message.text.strip() if update.message.text else ""
    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower()
    entities = update.message.entities or update.message.caption_entities

    # ===== التعامل مع المنشن في المجموعات =====
    if entities and chat_type in ["group", "supergroup"]:
        for ent in entities:
            if ent.type == MessageEntity.MENTION:
                mention = msg[ent.offset:ent.offset + ent.length]
                if mention.lower() == f"@{bot_username}":
                    await handle_group_mention(update, context, update.effective_chat.id)
                    return
            elif ent.type == MessageEntity.TEXT_MENTION:
                if ent.user.id == context.bot.id:
                    await handle_group_mention(update, context, update.effective_chat.id)
                    return

    # ===== في الخاص فقط =====
    if chat_type == "private":
        # ===== لعبة خمن الرقم =====
        if context.user_data.get("guess_game_active"):
            await GuessNumberGame.handle_guess(update, context)
            return

        # ===== حالة انتظار البث =====
        if context.user_data.get("awaiting_broadcast"):
            broadcast_msg = update.message.text
            success, fail = 0, 0
            for uid in db.get_all_user_ids():
                try:
                    await context.bot.send_message(uid, broadcast_msg)
                    success += 1
                except Exception as e:
                    fail += 1
                    logger.error(f"فشل إرسال البث للمستخدم {uid}: {e}")
            await update.message.reply_text(f"تم: {success} نجاح, {fail} فشل")
            context.user_data["awaiting_broadcast"] = False
            return

        # ===== حالة انتظار تعديل النقاط (إدارة) =====
        if context.user_data.get("awaiting_set_points"):
            try:
                parts = update.message.text.split()
                uid = int(parts[0])
                pts = int(parts[1])
                gems = int(parts[2])
                db.update_user(uid, points=pts, gems=gems)
                if cache and hasattr(cache, 'clear_user_cache'):
                    cache.clear_user_cache(uid)
                await update.message.reply_text("تم التحديث")
            except Exception as e:
                logger.error(f"خطأ في تعديل النقاط: {e}")
                await update.message.reply_text("صيغة خاطئة. استخدم: user_id points gems")
            context.user_data["awaiting_set_points"] = False
            return

        # ===== حالة انتظار بدء قناة (إدارة) =====
        if context.user_data.get("awaiting_start_channel"):
            await channel_h.process_start_channel_text(update, context)
            return

        # ===== حالة انتظار إيقاف قناة (إدارة) =====
        if context.user_data.get("awaiting_stop_channel"):
            await channel_h.process_stop_channel_text(update, context)
            return

        # ===== منع النصوص الطويلة =====
        if len(msg) > 100:
            await update.message.reply_text("النص طويل جداً.")
            return

        # ===== حالات انتظار إدخال بيانات من المستخدم =====
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
                await update.message.reply_text(
                    f"تحدي صديق قيد التطوير (سيتم إعلام {target['first_name']})."
                )
            context.user_data["awaiting_friend_challenge"] = False

async def handle_group_mention(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """معالج منشن البوت في المجموعة"""
    async with state.group_session_lock:
        if chat_id in state.group_game_sessions:
            return
    await context.bot.send_message(
        chat_id,
        "مرحباً بك في RPS Arena!",
        reply_markup=keyboards.channel_main_menu(chat_id)
    )

# ==================== أوامر الإدارة ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم للمؤسس"""
    user = update.effective_user
    if user.id != config.FOUNDER_ID:
        await update.message.reply_text(f"❌ غير مصرح لك. معرفك: {user.id}")
        return
    await update.message.reply_text("🛡️ **لوحة التحكم**", reply_markup=keyboards.admin_menu())

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != config.FOUNDER_ID:
        await query.answer("غير مصرح لك!")
        return
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
    if query.from_user.id != config.FOUNDER_ID:
        await query.answer("غير مصرح لك!")
        return
    await query.edit_message_text(
        "أرسل الرسالة التي تريد إرسالها للجميع:",
        reply_markup=keyboards.back_button("admin")
    )
    context.user_data["awaiting_broadcast"] = True

async def admin_set_points_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != config.FOUNDER_ID:
        await query.answer("غير مصرح لك!")
        return
    await query.edit_message_text(
        "أرسل:\n`user_id points gems`",
        reply_markup=keyboards.back_button("admin")
    )
    context.user_data["awaiting_set_points"] = True

async def admin_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != config.FOUNDER_ID:
        await query.answer("غير مصرح لك!")
        return
    async with channel_state.channel_settings_lock:
        chans = list(channel_state.channel_settings.keys())
    text = "القنوات المفعلة:\n" + "\n".join([str(c) for c in chans]) if chans else "لا توجد"
    await query.edit_message_text(text, reply_markup=keyboards.admin_menu())

async def admin_reset_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != config.FOUNDER_ID:
        await query.answer("غير مصرح لك!")
        return
    conn = sqlite3.connect(config.DB_NAME)
    conn.execute("DELETE FROM active_games")
    conn.execute("DELETE FROM pending_matches")
    conn.commit()
    conn.close()
    await query.answer("تم مسح المباريات العالقة.")

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
        if a.startswith("interval="):
            interval = int(a.split("=")[1])
        elif a.startswith("ttl="):
            ttl = int(a.split("=")[1])
    try:
        chat = await context.bot.get_chat(channel_name)
        chat_id = chat.id
        async with channel_state.channel_settings_lock:
            if chat_id in channel_state.channel_settings:
                old_task = channel_state.channel_settings[chat_id].get("task")
                if old_task:
                    old_task.cancel()
                del channel_state.channel_settings[chat_id]
        task = asyncio.create_task(channel_h.channel_voting_loop(chat_id, context))
        async with channel_state.channel_settings_lock:
            channel_state.channel_settings[chat_id] = {"interval": interval, "ttl": ttl, "task": task}
        await update.message.reply_text(
            f"تم بدء جولات التصويت التلقائي في {chat.title}\n"
            f"الفاصل: {interval}s | حذف الرسالة: {ttl}s"
        )
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
                if task:
                    task.cancel()
                del channel_state.channel_settings[chat_id]
                await update.message.reply_text(f"تم إيقاف جولات التصويت في {chat.title}")
            else:
                await update.message.reply_text("لا توجد جولات نشطة لهذه القناة.")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {str(e)}")

# ==================== الأوامر الجماعية ====================
async def massbattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    battle_id = db.start_mass_battle(chat_id)
    await context.bot.send_message(
        chat_id,
        "⚡ معركة جماعية! اختر حركتك خلال 30 ثانية:",
        reply_markup=keyboards.mass_battle_start_button(chat_id)
    )
    await asyncio.sleep(config.MASS_BATTLE_DURATION)
    winners = db.get_mass_battle_results(battle_id)
    if winners:
        for uid in winners:
            user_data = db.get_user(uid)
            db.update_user(
                uid,
                points=user_data["points"] + config.MASS_BATTLE_REWARD[0],
                gems=user_data.get("gems", 0) + config.MASS_BATTLE_REWARD[1]
            )
        winner_names = ", ".join([db.get_user(uid)["first_name"] for uid in winners[:5]])
        await context.bot.send_message(
            chat_id,
            f"🎉 انتهت المعركة! الفائزون: {winner_names} "
            f"(+{config.MASS_BATTLE_REWARD[0]} نقطة، +{config.MASS_BATTLE_REWARD[1]} جوهرة)"
        )
    else:
        await context.bot.send_message(chat_id, "لم ينضم أحد للمعركة!")

async def drop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not utils.is_founder(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    reward = random.choice(config.DROP_REWARDS)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 افتح الصندوق!", callback_data=f"claim_drop_{reward[0]}_{reward[1]}")]
    ])
    await context.bot.send_message(chat_id, "💥 صندوق مفاجئ! أول واحد يضغط يربح:", reply_markup=keyboard)

async def teambattle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("استخدم: /teambattle اسم_الفريق_الأحمر اسم_الفريق_الأزرق")
        return
    team1, team2 = context.args[0], context.args[1]
    battle_id = db.create_team_battle(chat_id, team1, team2)
    await update.message.reply_text(
        f"🔴 {team1} vs {team2} 🔵\nاضغط للانضمام لفريق:",
        reply_markup=keyboards.team_battle_team_buttons(battle_id)
    )
    await asyncio.sleep(60)
    conn = sqlite3.connect(config.DB_NAME)
    battle = conn.execute("SELECT * FROM team_battles WHERE battle_id=?", (battle_id,)).fetchone()
    if not battle:
        conn.close()
        return
    chat_id = battle["chat_id"]
    team1_players = db.get_team_players(battle_id, "red")
    team2_players = db.get_team_players(battle_id, "blue")
    for uid in team1_players:
        await context.bot.send_message(
            uid,
            "اختر حركتك لمعركة الفريق:",
            reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}")
        )
    for uid in team2_players:
        await context.bot.send_message(
            uid,
            "اختر حركتك لمعركة الفريق:",
            reply_markup=keyboards.choice_buttons(f"teambattle_{battle_id}")
        )
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
    await context.bot.send_message(
        chat_id,
        f"نتيجة المعركة: {'🔴 فاز الفريق الأحمر' if winner_team=='red' else '🔵 فاز الفريق الأزرق' if winner_team=='blue' else 'تعادل'}"
    )
    conn.close()

# ==================== عجلة الحظ ====================
async def wheel_spin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    u = db.get_user(user.id)
    if u.get("gems", 0) < config.WHEEL_COST:
        await query.answer("تحتاج 5 جواهر لتدوير العجلة!")
        return
    
    # خصم الجواهر وحفظ القيمة الجديدة
    current_gems = u["gems"] - config.WHEEL_COST
    db.update_user(user.id, gems=current_gems)
    
    reward_type, value = db.spin_wheel(user.id)
    
    if reward_type == "points":
        current_points = db.get_user(user.id)["points"]
        db.update_user(user.id, points=current_points + value)
        msg = f"🎉 ربحت {value} نقطة!"
    elif reward_type == "gems":
        db.update_user(user.id, gems=current_gems + value)
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
            current_points = db.get_user(user.id)["points"]
            db.update_user(user.id, points=current_points + sub[1])
            msg = f"🎁 صندوق كنز: +{sub[1]} نقطة"
        elif sub[0] == "gems":
            current_gems_after = db.get_user(user.id)["gems"]
            db.update_user(user.id, gems=current_gems_after + sub[1])
            msg = f"🎁 صندوق كنز: +{sub[1]} جوهرة"
        else:
            msg = "🎁 صندوق كنز!"
    else:
        msg = "🎡 حظ سعيد!"
    
    db.add_battle_pass_xp(user.id, 5)
    await query.edit_message_text(f"🎡 العجلة توقفت عند: {msg}", reply_markup=keyboards.wheel_button())

# ==================== معالج الأخطاء العام ====================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام"""
    logger.error(f"Exception: {context.error}", exc_info=context.error)
    
    if update and hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.answer("حدث خطأ مؤقت. حاول مرة أخرى.")
        except:
            pass
    elif update and hasattr(update, 'message') and update.message:
        try:
            await update.message.reply_text("⚠️ حدث خطأ مؤقت. حاول مرة أخرى.")
        except:
            pass

# ==================== تشغيل البوت ====================
def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "":
        logger.error("❌ BOT_TOKEN غير موجود! أضفه في متغيرات البيئة")
        return

    app = Application.builder().token(config.BOT_TOKEN).build()

    # -------------------- الأوامر --------------------
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
    
    # أمر matchmaking (إذا كان متاحاً)
    if matchmaking_status:
        app.add_handler(CommandHandler("matchmaking", matchmaking_status))

    # -------------------- الألعاب الجديدة --------------------
    app.add_handler(CallbackQueryHandler(GuessNumberGame.start, pattern="^guess_number$"))
    app.add_handler(CallbackQueryHandler(GuessNumberGame.again, pattern="^guess_number_again$"))
    app.add_handler(CallbackQueryHandler(QuizGame.start, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(QuizGame.again, pattern="^quiz_again$"))
    app.add_handler(CallbackQueryHandler(QuizGame.handle_answer, pattern="^quiz_answer_"))

    # -------------------- معالجات الأزرار --------------------
    # حركات القناة
    app.add_handler(CallbackQueryHandler(channel_h.handle_move, pattern="^move_"))
    
    # الملاحة الأساسية + الأزرار الجديدة
    app.add_handler(CallbackQueryHandler(
        navigation_handler,
        pattern="^(back_main|delete_message|language|profile|play_now|more|how_to_play|support|rate_bot|select_type|browse_sections|create_room|search_games|search_room|channel_|manage_channels|change_question_type|create_game_now|enable_auto_play|toggle_auto_play|broadcast_game|show_question_type)$"
    ))
    
    # أزرار اللعب
    app.add_handler(CallbackQueryHandler(
        game_handler,
        pattern="^(game|solo|random|friend|channel|spock|story|group_|pick_|spockpick_|open_|join_tournament_|accept_challenge_|reject_challenge_|spectate_|play_|mode_|rematch_)"
    ))
    
    # أزرار القناة والمهام والإنجازات
    app.add_handler(CallbackQueryHandler(
        channel_handler,
        pattern="^(channel_play|weekly_leaderboard|ch_leaderboard_|predict_|tasks|achievements|rating|battlepass|wheel)"
    ))
    
    # أزرار المتجر
    app.add_handler(CallbackQueryHandler(
        shop_handler,
        pattern="^(shop|shop_cards|buy_|shop_titles|buy_title_|shop_themes|buy_theme_|frames_shop|buy_frame_|abilities_shop|buy_ability_|market|treasure_box)"
    ))
    
    # أزرار الأصدقاء والعشائر
    app.add_handler(CallbackQueryHandler(
        social_handler,
        pattern="^(friends|add_friend|friend_requests|friend_list|accept_friend_|reject_friend_|clans|clan_|treasury_|do_upgrade_|clan_war_info)"
    ))
    
    # أزرار الإدارة
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin_"))

    # -------------------- معالج النصوص والأخطاء --------------------
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    # -------------------- المهام الخلفية --------------------
    loop = asyncio.get_event_loop()
    loop.create_task(run_cleanup())
    loop.create_task(run_auto_drops(app))

    logger.info("🚀 البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
