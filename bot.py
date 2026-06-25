import json, logging, asyncio, random, sqlite3
from datetime import datetime, timedelta
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
from handlers.commands.admin_commands import (
    admin_stats, admin_broadcast_prompt, admin_set_points_prompt,
    admin_channels_list, admin_reset_games
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.init_db()

# ---------- المهام الدورية ----------
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

# ---------- تشغيل البوت ----------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    # --- الأوامر ---
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

    # --- معالجات الأزرار (مقسمة) ---
    app.add_handler(CallbackQueryHandler(channel_h.handle_move, pattern="^move_"))
    app.add_handler(CallbackQueryHandler(navigation_handler, pattern="^(back_main|delete_message|language|profile)$"))
    app.add_handler(CallbackQueryHandler(game_handler, pattern="^(game|solo|random|friend|channel|spock|story|group_|pick_|spockpick_|open_|join_tournament_|accept_challenge_|reject_challenge_|spectate_)"))
    app.add_handler(CallbackQueryHandler(channel_handler, pattern="^(channel_play|weekly_leaderboard|ch_leaderboard_|predict_|tasks|achievements|rating|battlepass|wheel)"))
    app.add_handler(CallbackQueryHandler(shop_handler, pattern="^(shop|shop_cards|buy_|shop_titles|buy_title_|shop_themes|buy_theme_|frames_shop|buy_frame_|abilities_shop|buy_ability_|market|treasure_box)"))
    app.add_handler(CallbackQueryHandler(social_handler, pattern="^(friends|add_friend|friend_requests|friend_list|accept_friend_|reject_friend_|clans|clan_|treasury_|do_upgrade_|clan_war_info)"))
    app.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin_"))

    # --- معالج النصوص ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # --- المهام الخلفية ---
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_stuck_games())
    loop.create_task(auto_drops(app))

    logger.info("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
