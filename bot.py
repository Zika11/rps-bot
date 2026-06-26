import json
import logging
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# استيراد config (يعمل سواء كان ملف config.py في الجذر أو مجلد config/ مع __init__.py)
import config

# استيراد الوحدات الأساسية
import models
import db
import state
import keyboards
import game_logic
import utils

# استيراد محرك اللعبة
import engine.game_engine as game_engine
import state as channel_state

# استيراد الـ handlers
import handlers.channel_handlers as channel_h
import handlers.game_handlers as game_h
import handlers.shop_handlers as shop_h
import handlers.social_handlers as social_h
import handlers.misc_handlers as misc_h

# استيراد معالجات الأزرار
from handlers.callbacks import (
    navigation_handler,
    game_handler,
    channel_handler,
    shop_handler,
    social_handler,
    admin_handler
)

# استيراد الأوامر
from handlers.commands import (
    start, me_command, daily_command, referral_command,
    game_command, web_command,
    shop_command, buy_command, market_sell_command, battlepass_command,
    admin_panel, start_channel_command, stop_channel_command,
    massbattle_command, teambattle_command, drop_command
)
from handlers.commands.admin_commands import (
    admin_stats, admin_broadcast_prompt, admin_set_points_prompt,
    admin_channels_list, admin_reset_games
)

# استيراد المهام الخلفية
from tasks import run_cleanup, run_auto_drops

# استيراد نظام اللوجينج المحسن (إن وجد)
try:
    from utils.logging_utils import logger
except ImportError:
    # في حالة عدم وجود logging_utils، استخدم logging العادي
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ utils.logging_utils غير موجود، استخدام logging عادي")

# استيراد خدمات التخزين المؤقت (إن وجدت)
try:
    from services.cache_service import cache
except ImportError:
    cache = None
    logger.warning("⚠️ services.cache_service غير موجود، التخزين المؤقت معطل")

try:
    from core.redis_client import redis_client
except ImportError:
    redis_client = None
    logger.warning("⚠️ core.redis_client غير موجود، Redis معطل")

try:
    from core.google_sheets import gsheets
except ImportError:
    gsheets = None
    logger.warning("⚠️ core.google_sheets غير موجود، Google Sheets معطل")

# ==================== تهيئة قاعدة البيانات ====================
models.init_db()
logger.info("✅ قاعدة البيانات جاهزة")

# ==================== التحقق من الاتصالات ====================
if redis_client and hasattr(redis_client, 'is_connected') and redis_client.is_connected():
    logger.info("✅ Redis متصل")
else:
    logger.info("ℹ️ Redis غير متصل أو معطل")

if gsheets and hasattr(gsheets, 'is_connected') and gsheets.is_connected():
    logger.info("✅ Google Sheets متصل")
    # محاولة تحميل الإعدادات
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
    """معالج الرسائل النصية (للأوامر النصية غير المعرفة، البث، إدخال البيانات)"""
    user = update.effective_user
    msg = update.message.text.strip() if update.message.text else ""
    chat_type = update.effective_chat.type
    bot_username = context.bot.username.lower()
    entities = update.message.entities or update.message.caption_entities

    # التعامل مع المنشن في المجموعات
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

    # في الخاص فقط
    if chat_type == "private":
        # حالة انتظار البث
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

        # حالة انتظار تعديل النقاط (إدارة)
        if context.user_data.get("awaiting_set_points"):
            try:
                parts = update.message.text.split()
                uid = int(parts[0])
                pts = int(parts[1])
                gems = int(parts[2])
                db.update_user(uid, points=pts, gems=gems)
                # مسح الكاش إذا كان موجوداً
                if cache and hasattr(cache, 'clear_user_cache'):
                    cache.clear_user_cache(uid)
                await update.message.reply_text("تم التحديث")
            except Exception as e:
                logger.error(f"خطأ في تعديل النقاط: {e}")
                await update.message.reply_text("صيغة خاطئة. استخدم: user_id points gems")
            context.user_data["awaiting_set_points"] = False
            return

        # حالة انتظار بدء قناة (إدارة)
        if context.user_data.get("awaiting_start_channel"):
            await channel_h.process_start_channel_text(update, context)
            return

        # حالة انتظار إيقاف قناة (إدارة)
        if context.user_data.get("awaiting_stop_channel"):
            await channel_h.process_stop_channel_text(update, context)
            return

        # منع النصوص الطويلة
        if len(msg) > 100:
            await update.message.reply_text("النص طويل جداً.")
            return

        # حالات انتظار إدخال بيانات من المستخدم
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
    """معالج منشن البوت في المجموعة"""
    async with state.group_session_lock:
        if chat_id in state.group_game_sessions:
            return
    await context.bot.send_message(
        chat_id,
        "مرحباً بك في RPS Arena!",
        reply_markup=keyboards.channel_main_menu(chat_id)
    )

# ==================== تشغيل البوت ====================
def main():
    """النقطة الرئيسية لتشغيل البوت"""
    # التحقق من وجود التوكن
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN":
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

    # -------------------- معالجات الأزرار (مقسمة حسب البادئة) --------------------
    # حركات القناة (move_*)
    app.add_handler(CallbackQueryHandler(channel_h.handle_move, pattern="^move_"))
    
    # الملاحة الأساسية
    app.add_handler(CallbackQueryHandler(navigation_handler, pattern="^(back_main|delete_message|language|profile)$"))
    
    # أزرار اللعب
    app.add_handler(CallbackQueryHandler(
        game_handler,
        pattern="^(game|solo|random|friend|channel|spock|story|group_|pick_|spockpick_|open_|join_tournament_|accept_challenge_|reject_challenge_|spectate_|play_|mode_|rematch_)"
    ))
    
    # أزرار القناة والمهام والإنجازات والتصنيف والعجلة
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
    
    # أزرار الإدارة (للمؤسس فقط)
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin_"))

    # -------------------- معالج النصوص --------------------
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # -------------------- المهام الخلفية --------------------
    loop = asyncio.get_event_loop()
    loop.create_task(run_cleanup())        # تنظيف الألعاب العالقة
    loop.create_task(run_auto_drops(app))  # إسقاط الصناديق التلقائية

    # -------------------- بدء البوت --------------------
    logger.info("🚀 البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
